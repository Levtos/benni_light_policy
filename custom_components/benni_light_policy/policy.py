"""Pure Entscheidungs-Engine für die Light-Policy — HA-frei, voll testbar.

Trennt strikt:
  * `decide()`  — ermittelt den *gewünschten* Plan (mode/preset/brightness/targets)
                  rein aus dem Context. Hier landet die Lastenheft-Logik §4.1/§7.
  * Gating      — apply_enabled / startup / manual_off setzen nur `apply_allowed`
                  + `blockers`, ohne den Plan zu verändern. So bleibt der Plan
                  (und sein scene_hash) für den Phase-4-Shadow-Vergleich aussagekräftig,
                  auch wenn gerade nicht angewendet werden darf.

Der Lux-Gate-Zustand ist zustandsbehaftet (Hysterese) und wird vom Coordinator
gehalten/persistiert; `lux_gate()` ist trotzdem pure (prev_gate als Eingabe).
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .const import (
    ACTIVITY_HOUSEHOLD,
    ACTIVITY_PRESET_DRIVING,
    ACTIVITY_PRIVATE_TIME,
    ACTIVITY_WORK_HOME,
    BIO_SLEEP,
    BIO_WAKING,
    COLOR_TEMP_WAKING,
    COLOR_TEMP_WORK_HOME,
    DAY_PHASES,
    DEFAULT_BRIGHTNESS,
    DEFAULT_LUX_THRESHOLDS,
    GROUP_ALL,
    GROUP_CEILING,
    GROUP_MAIN,
    MASTER_PHASE_DAYTIME,
    MODE_CINEMA,
    MODE_HOUSEHOLD,
    MODE_IDLE,
    MODE_MUSIC_PARTY,
    MODE_PC_HEARTHSTONE,
    MODE_PC_OVERWATCH,
    MODE_PRESENCE_SIM,
    MODE_PRIVATE_TIME,
    MODE_WAKING,
    MODE_WORK_HOME,
    PRESENCE_SIM_PHASES,
    PRESENCE_SIM_TRIGGERS,
    PRESENCE_TRANSITION_COMING_HOME,
    PRESET_PC_HEARTHSTONE,
    PRESET_PC_OVERWATCH,
    SEASON_WINTER,
    TITLE_HEARTHSTONE,
    TITLE_OVERWATCH,
    WEATHER_DARK_DROP_RATIO,
    WEATHER_DARK_ICONS,
)

# Apply-Kind: wie die Apply-Schicht den Plan umsetzt.
APPLY_OFF = "off"      # Hard-Off (alle WZ-Lampen aus)
APPLY_CCT = "cct"      # direktes light.turn_on mit color_temp (work_home, waking)
APPLY_SCENE = "scene"  # Scene-Presets-Dynamic-Scene (Crossfade)

# Kalender-Thema (deutsch, aus benni_context) → Preset-Theme (Katalog-Schlüssel).
THEME_MAP = {
    "weihnachten": "christmas",
    "ostern": "easter",
    "halloween": "halloween",
}
# Party-Musik-Enums sind noch nicht definiert (Lastenheft OQ-2) — bis dahin
# triggert music_party nicht.
PARTY_TITLES: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Context:
    """Snapshot aller Quell-Inputs für eine Entscheidung. None = unknown."""

    bio_state: str | None = None
    day_state: str | None = None          # Detailphase (early_morning ..)
    activity_state: str | None = None
    presence_personal: str | None = None
    presence_household: str | None = None
    guest: bool | None = None             # Eltern anwesend
    season: str | None = None
    calendar_theme: str | None = None
    title_classifier: str | None = None
    entertainment_stable: bool | None = None
    overnight_away: bool | None = None     # Benni übernachtet auswärts
    presence_transition: str | None = None  # coming_home / leaving_home / none
    lux: float | None = None
    weather: str | None = None
    master_phase: str | None = None


@dataclass
class Plan:
    mode: str
    preset_enum: str | None
    brightness: int | None
    color_temp: int | None
    apply_kind: str
    targets: list[str] = field(default_factory=list)
    exclusive_off: list[str] = field(default_factory=list)
    reason: str = ""
    lux_gate_on: bool = False
    blockers: list[str] = field(default_factory=list)
    apply_allowed: bool = True

    @property
    def scene_hash(self) -> str:
        """16-stelliger Hash über die *wirksamen* (sichtbaren) Plan-Parameter.

        Bewusst OHNE apply_allowed/blockers — der Hash beschreibt die Szenen-Identität,
        nicht das Gating. Konsumenten triggern auf hash-Change; das Gating wird separat
        über den apply_blocked-Sensor signalisiert.
        """
        payload = {
            "mode": self.mode,
            "preset_enum": self.preset_enum,
            "brightness": self.brightness,
            "color_temp": self.color_temp,
            "apply_kind": self.apply_kind,
            "targets": sorted(self.targets),
            "exclusive_off": sorted(self.exclusive_off),
        }
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "preset_enum": self.preset_enum,
            "brightness": self.brightness,
            "color_temp": self.color_temp,
            "apply_kind": self.apply_kind,
            "targets": list(self.targets),
            "exclusive_off": list(self.exclusive_off),
            "reason": self.reason,
            "lux_gate_on": self.lux_gate_on,
            "scene_hash": self.scene_hash,
            "blockers": list(self.blockers),
            "apply_allowed": self.apply_allowed,
        }


# --------------------------------------------------------------------------- #
# Lux-Gate (R1, Schmitt-Trigger mit saisonalen Schwellen)
# --------------------------------------------------------------------------- #
def lux_gate(
    lux: float | None,
    season: str | None,
    prev_gate: bool | None,
    *,
    day_state_known: bool,
    tmc_set: bool = True,
    weather_dark: bool = False,
    thresholds: dict[str, tuple[int, int]] | None = None,
) -> bool:
    """True = Gate offen (dunkel genug, Licht erlaubt).

    - Day State unbekannt  → Gate zu (Lastenheft Edge Case).
    - weather_dark (R10)   → Gate offen (wetterbedingte Dunkelheit am Tag).
    - Lux unavailable      → letzten Zustand halten (prev), sonst zu.
    - TMC noch nicht gesetzt → einfacher Vergleich ohne Hysterese (R1/R2):
      Gate offen iff lux < dunkel-Schwelle.
    - TMC gesetzt → Schmitt-Trigger: lux < dunkel → an; lux >= hell → aus; dazwischen halten.
    """
    if not day_state_known:
        return False
    if weather_dark:
        return True
    thr = thresholds or DEFAULT_LUX_THRESHOLDS
    dark, bright = thr.get(season or SEASON_WINTER, thr[SEASON_WINTER])
    if lux is None:
        return bool(prev_gate)
    if not tmc_set:
        return lux < dark
    if lux < dark:
        return True
    if lux >= bright:
        return False
    return bool(prev_gate)


def bedtime_signal_due(
    day_state: str | None,
    bio_state: str | None,
    awake_minutes: float | None,
    *,
    threshold_minutes: int = 840,
) -> bool:
    """R16: Schlafzimmer-Bettgeh-Signal — early/late_night + awake + ≥14h wach."""
    return (
        day_state in ("early_night", "late_night")
        and bio_state == "awake"
        and awake_minutes is not None
        and awake_minutes >= threshold_minutes
    )


def hallway_should_light(trigger_active: bool, lux_gate_on: bool) -> bool:
    """R14: Flurlicht an iff Trigger (Tür/Bewegung) UND draußen dunkel."""
    return bool(trigger_active and lux_gate_on)


def weather_darkness(
    lux_now: float | None,
    lux_baseline: float | None,
    weather: str | None,
    master_phase: str | None,
    *,
    drop_ratio: float = WEATHER_DARK_DROP_RATIO,
) -> bool:
    """R10: True wenn am Tag (morning/midday) der Lux um > drop_ratio gefallen ist
    UND das Wetter-Icon dunkel ist. lux_baseline = Lux vor ~10 min."""
    if master_phase not in MASTER_PHASE_DAYTIME:
        return False
    if (weather or "") not in WEATHER_DARK_ICONS:
        return False
    if lux_now is None or lux_baseline is None or lux_baseline <= 0:
        return False
    return (lux_baseline - lux_now) / lux_baseline > drop_ratio


# --------------------------------------------------------------------------- #
# Preset-/Brightness-Helfer
# --------------------------------------------------------------------------- #
def _effective_theme(ctx: Context) -> str:
    """Event-Thema gewinnt über Jahreszeit, sonst Jahreszeit (Fallback winter)."""
    mapped = THEME_MAP.get((ctx.calendar_theme or "").lower())
    if mapped:
        return mapped
    return ctx.season or SEASON_WINTER


def _phase_preset(ctx: Context, phase: str) -> str:
    return f"{_effective_theme(ctx)}_{phase}"


def _brightness(profile: dict[str, int], key: str) -> int | None:
    return profile.get(key)


# --------------------------------------------------------------------------- #
# Wohnzimmer-Policies (Lastenheft §4.1) — typisierte, prioritäts-geordnete Registry.
#
# Jede Policy ist ein Evaluator (Context, lux_gate, profile) -> Plan | None.
# `None` = Policy trifft nicht zu. Der Arbiter nimmt die erste zutreffende in
# Prioritätsreihenfolge (== „erste zutreffende Bedingung gewinnt" aus §4.1).
# Diese Registry ist das Fundament für den späteren Hub + Subentries (Phase 2):
# jede dieser Arten wird dort zu einem konfigurierbaren Subentry-Typ.
# --------------------------------------------------------------------------- #
def _awake_phase(ctx: Context) -> str | None:
    return ctx.day_state if ctx.day_state in DAY_PHASES else None


def _eval_waking(ctx: Context, gate: bool, profile: dict[str, int]) -> Plan | None:
    if ctx.bio_state != BIO_WAKING:
        return None
    return Plan(
        mode=MODE_WAKING, preset_enum=None,
        brightness=_brightness(profile, MODE_WAKING), color_temp=COLOR_TEMP_WAKING,
        apply_kind=APPLY_CCT, targets=[GROUP_ALL], lux_gate_on=gate,
        reason="waking: bio=waking (Weckerlicht, Lux-Gate ignoriert)",
    )


def _eval_sleep_off(ctx: Context, gate: bool, profile: dict[str, int]) -> Plan | None:
    if ctx.bio_state != BIO_SLEEP:
        return None
    return Plan(
        mode=MODE_IDLE, preset_enum=None, brightness=0, color_temp=None,
        apply_kind=APPLY_OFF, targets=[], exclusive_off=[GROUP_ALL],
        lux_gate_on=gate, reason="hard_off: bio=sleep",
    )


def _eval_lux_off(ctx: Context, gate: bool, profile: dict[str, int]) -> Plan | None:
    if gate:
        return None
    return Plan(
        mode=MODE_IDLE, preset_enum=None, brightness=0, color_temp=None,
        apply_kind=APPLY_OFF, targets=[], exclusive_off=[GROUP_ALL],
        lux_gate_on=gate, reason="hard_off: lux_gate off (zu hell)",
    )


def _eval_private_time(ctx: Context, gate: bool, profile: dict[str, int]) -> Plan | None:
    if ctx.activity_state != ACTIVITY_PRIVATE_TIME:
        return None
    return Plan(
        mode=MODE_PRIVATE_TIME, preset_enum=MODE_PRIVATE_TIME,
        brightness=_brightness(profile, MODE_PRIVATE_TIME), color_temp=None,
        apply_kind=APPLY_SCENE, targets=[GROUP_MAIN], exclusive_off=[GROUP_CEILING],
        lux_gate_on=gate, reason="private_time: activity=private_time",
    )


def _eval_work_home(ctx: Context, gate: bool, profile: dict[str, int]) -> Plan | None:
    if ctx.activity_state != ACTIVITY_WORK_HOME:
        return None
    return Plan(
        mode=MODE_WORK_HOME, preset_enum=None,
        brightness=_brightness(profile, MODE_WORK_HOME), color_temp=COLOR_TEMP_WORK_HOME,
        apply_kind=APPLY_CCT, targets=[GROUP_CEILING, GROUP_MAIN],
        lux_gate_on=gate, reason="work_home: activity=work_home (CCT 5000K)",
    )


def _eval_household(ctx: Context, gate: bool, profile: dict[str, int]) -> Plan | None:
    if ctx.activity_state != ACTIVITY_HOUSEHOLD:
        return None
    phase = _awake_phase(ctx) or "early_evening"
    return Plan(
        mode=MODE_HOUSEHOLD, preset_enum=_phase_preset(ctx, phase),
        brightness=_brightness(profile, phase), color_temp=None,
        apply_kind=APPLY_SCENE, targets=[GROUP_MAIN], lux_gate_on=gate,
        reason=f"household: activity=household, phase={phase}",
    )


def _eval_presence_sim(ctx: Context, gate: bool, profile: dict[str, int]) -> Plan | None:
    # R12: coming_home beendet die Simulation sofort (noch bevor presence_personal flippt).
    awake_phase = _awake_phase(ctx)
    if not (
        ctx.presence_personal in PRESENCE_SIM_TRIGGERS
        and awake_phase in PRESENCE_SIM_PHASES
        and not ctx.overnight_away
        and ctx.presence_transition != PRESENCE_TRANSITION_COMING_HOME
    ):
        return None
    return Plan(
        mode=MODE_PRESENCE_SIM, preset_enum=_phase_preset(ctx, awake_phase),
        brightness=_brightness(profile, awake_phase), color_temp=None,
        apply_kind=APPLY_SCENE, targets=[GROUP_MAIN], lux_gate_on=gate,
        reason=f"presence_sim: presence={ctx.presence_personal}, phase={awake_phase}",
    )


def _eval_music_party(ctx: Context, gate: bool, profile: dict[str, int]) -> Plan | None:
    # OQ-2: Party-Titel-Enums noch nicht definiert → derzeit inaktiv.
    if not (
        ctx.title_classifier in PARTY_TITLES
        and (ctx.calendar_theme or "").lower() == "geburtstag"
        and ctx.activity_state in ACTIVITY_PRESET_DRIVING
    ):
        return None
    return Plan(
        mode=MODE_MUSIC_PARTY, preset_enum=MODE_MUSIC_PARTY,
        brightness=None, color_temp=None, apply_kind=APPLY_SCENE,
        targets=[GROUP_MAIN], lux_gate_on=gate, reason="music_party",
    )


def _eval_gaming(ctx: Context, gate: bool, profile: dict[str, int]) -> Plan | None:
    if ctx.activity_state not in ACTIVITY_PRESET_DRIVING:
        return None
    if ctx.title_classifier == TITLE_OVERWATCH:
        return Plan(
            mode=MODE_PC_OVERWATCH, preset_enum=PRESET_PC_OVERWATCH,
            brightness=None, color_temp=None, apply_kind=APPLY_SCENE,
            targets=[GROUP_MAIN], lux_gate_on=gate, reason="pc_overwatch",
        )
    if ctx.title_classifier == TITLE_HEARTHSTONE:
        return Plan(
            mode=MODE_PC_HEARTHSTONE, preset_enum=PRESET_PC_HEARTHSTONE,
            brightness=None, color_temp=None, apply_kind=APPLY_SCENE,
            targets=[GROUP_MAIN], lux_gate_on=gate, reason="pc_hearthstone",
        )
    return None


def _eval_cinema(ctx: Context, gate: bool, profile: dict[str, int]) -> Plan | None:
    if not (ctx.entertainment_stable and not ctx.guest):
        return None
    return Plan(
        mode=MODE_CINEMA, preset_enum=MODE_CINEMA, brightness=None, color_temp=None,
        apply_kind=APPLY_SCENE, targets=[GROUP_MAIN], exclusive_off=[GROUP_CEILING],
        lux_gate_on=gate, reason="cinema: entertainment_stable on, kein Gast",
    )


def _eval_dayphase(ctx: Context, gate: bool, profile: dict[str, int]) -> Plan:
    """Terminal — liefert immer einen Plan (saisonales Preset der Tagesphase)."""
    phase = _awake_phase(ctx) or "early_evening"
    return Plan(
        mode=phase, preset_enum=_phase_preset(ctx, phase),
        brightness=_brightness(profile, phase), color_temp=None,
        apply_kind=APPLY_SCENE, targets=[GROUP_MAIN], lux_gate_on=gate,
        reason=f"dayphase fallback: {phase}",
    )


@dataclass(frozen=True)
class PolicyDef:
    """Typisierte Wohnzimmer-Policy. priority: kleiner = höher (§4.1)."""

    kind: str
    priority: int
    evaluate: Callable[[Context, bool, dict[str, int]], Plan | None]


# Reihenfolge == Prioritätsreihenfolge (§4.1). `dayphase` ist terminal.
LIVING_ROOM_POLICIES: tuple[PolicyDef, ...] = (
    PolicyDef("waking", 1, _eval_waking),
    PolicyDef("idle_sleep", 2, _eval_sleep_off),
    PolicyDef("idle_lux", 3, _eval_lux_off),
    PolicyDef("private_time", 4, _eval_private_time),
    PolicyDef("work_home", 5, _eval_work_home),
    PolicyDef("household", 6, _eval_household),
    PolicyDef("presence_sim", 7, _eval_presence_sim),
    PolicyDef("music_party", 8, _eval_music_party),
    PolicyDef("gaming", 9, _eval_gaming),
    PolicyDef("cinema", 11, _eval_cinema),
    PolicyDef("dayphase", 12, _eval_dayphase),
)

POLICY_KINDS: tuple[str, ...] = tuple(p.kind for p in LIVING_ROOM_POLICIES)


def _decide_plan(ctx: Context, lux_gate_on: bool, profile: dict[str, int]) -> Plan:
    """Arbiter: erste zutreffende Policy in Prioritätsreihenfolge gewinnt."""
    for pol in LIVING_ROOM_POLICIES:
        result = pol.evaluate(ctx, lux_gate_on, profile)
        if result is not None:
            return result
    return _eval_dayphase(ctx, lux_gate_on, profile)  # Sicherheitsnetz


def decide(
    ctx: Context,
    *,
    lux_gate_on: bool,
    startup_ready: bool,
    apply_enabled: bool,
    manual_off_active: bool,
    brightness_profile: dict[str, int] | None = None,
) -> Plan:
    """Vollständige Entscheidung inkl. Gating-Overlay."""
    profile = {**DEFAULT_BRIGHTNESS, **(brightness_profile or {})}
    plan = _decide_plan(ctx, lux_gate_on, profile)

    # Gating-Overlay — verändert nur apply_allowed/blockers, nie den Plan selbst.
    if not apply_enabled:
        plan.blockers.append("apply_disabled")
        plan.apply_allowed = False
    if not startup_ready:
        plan.blockers.append("startup_block")
        plan.apply_allowed = False
    if manual_off_active:
        # R9 — Hold gewinnt: kein Hard-Off, kein Einschalten.
        plan.blockers.append("manual_off")
        plan.apply_allowed = False

    return plan
