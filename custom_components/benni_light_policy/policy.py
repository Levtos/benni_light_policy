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
# Entscheidungskette (Lastenheft §4.1) — erste zutreffende Bedingung gewinnt
# --------------------------------------------------------------------------- #
def _decide_plan(ctx: Context, lux_gate_on: bool, profile: dict[str, int]) -> Plan:
    awake_phase = ctx.day_state if ctx.day_state in DAY_PHASES else None

    # 1) waking — Weckerlicht (übersteuert sleep).
    if ctx.bio_state == BIO_WAKING:
        return Plan(
            mode=MODE_WAKING, preset_enum=None,
            brightness=_brightness(profile, MODE_WAKING), color_temp=COLOR_TEMP_WAKING,
            apply_kind=APPLY_CCT, targets=[GROUP_ALL], lux_gate_on=lux_gate_on,
            reason="waking: bio=waking (Weckerlicht, Lux-Gate ignoriert)",
        )

    # 2) idle/hard-off — Bio = sleep.
    if ctx.bio_state == BIO_SLEEP:
        return Plan(
            mode=MODE_IDLE, preset_enum=None, brightness=0, color_temp=None,
            apply_kind=APPLY_OFF, targets=[], exclusive_off=[GROUP_ALL],
            lux_gate_on=lux_gate_on, reason="hard_off: bio=sleep",
        )

    # 3) idle/hard-off — zu hell.
    if not lux_gate_on:
        return Plan(
            mode=MODE_IDLE, preset_enum=None, brightness=0, color_temp=None,
            apply_kind=APPLY_OFF, targets=[], exclusive_off=[GROUP_ALL],
            lux_gate_on=lux_gate_on, reason="hard_off: lux_gate off (zu hell)",
        )

    # 4) private_time.
    if ctx.activity_state == ACTIVITY_PRIVATE_TIME:
        return Plan(
            mode=MODE_PRIVATE_TIME, preset_enum=MODE_PRIVATE_TIME,
            brightness=_brightness(profile, MODE_PRIVATE_TIME), color_temp=None,
            apply_kind=APPLY_SCENE, targets=[GROUP_MAIN], exclusive_off=[GROUP_CEILING],
            lux_gate_on=lux_gate_on, reason="private_time: activity=private_time",
        )

    # 5) work_home — CCT-Arbeitslicht.
    if ctx.activity_state == ACTIVITY_WORK_HOME:
        return Plan(
            mode=MODE_WORK_HOME, preset_enum=None,
            brightness=_brightness(profile, MODE_WORK_HOME), color_temp=COLOR_TEMP_WORK_HOME,
            apply_kind=APPLY_CCT, targets=[GROUP_CEILING, GROUP_MAIN],
            lux_gate_on=lux_gate_on, reason="work_home: activity=work_home (CCT 5000K)",
        )

    # 6) household — wie aktuelle Tagesphase, Entertainment wird ignoriert.
    if ctx.activity_state == ACTIVITY_HOUSEHOLD:
        phase = awake_phase or "early_evening"
        return Plan(
            mode=MODE_HOUSEHOLD, preset_enum=_phase_preset(ctx, phase),
            brightness=_brightness(profile, phase), color_temp=None,
            apply_kind=APPLY_SCENE, targets=[GROUP_MAIN], lux_gate_on=lux_gate_on,
            reason=f"household: activity=household, phase={phase}",
        )

    # 7) presence_sim — abwesend/bei_eltern in dunkler Phase, kein Übernacht-Signal.
    #     R12: coming_home beendet die Simulation sofort (noch bevor presence_personal flippt).
    if (
        ctx.presence_personal in PRESENCE_SIM_TRIGGERS
        and awake_phase in PRESENCE_SIM_PHASES
        and not ctx.overnight_away
        and ctx.presence_transition != PRESENCE_TRANSITION_COMING_HOME
    ):
        return Plan(
            mode=MODE_PRESENCE_SIM, preset_enum=_phase_preset(ctx, awake_phase),
            brightness=_brightness(profile, awake_phase), color_temp=None,
            apply_kind=APPLY_SCENE, targets=[GROUP_MAIN], lux_gate_on=lux_gate_on,
            reason=f"presence_sim: presence={ctx.presence_personal}, phase={awake_phase}",
        )

    # 8) music_party — Party-Titel + Geburtstag + free_time/idle (OQ-2: derzeit inaktiv).
    if (
        ctx.title_classifier in PARTY_TITLES
        and (ctx.calendar_theme or "").lower() == "geburtstag"
        and ctx.activity_state in ACTIVITY_PRESET_DRIVING
    ):
        return Plan(
            mode=MODE_MUSIC_PARTY, preset_enum=MODE_MUSIC_PARTY,
            brightness=None, color_temp=None, apply_kind=APPLY_SCENE,
            targets=[GROUP_MAIN], lux_gate_on=lux_gate_on, reason="music_party",
        )

    # 9/10) PC-Spiele — Title Classifier + free_time/idle.
    if ctx.activity_state in ACTIVITY_PRESET_DRIVING:
        if ctx.title_classifier == TITLE_OVERWATCH:
            return Plan(
                mode=MODE_PC_OVERWATCH, preset_enum=PRESET_PC_OVERWATCH,
                brightness=None, color_temp=None, apply_kind=APPLY_SCENE,
                targets=[GROUP_MAIN], lux_gate_on=lux_gate_on, reason="pc_overwatch",
            )
        if ctx.title_classifier == TITLE_HEARTHSTONE:
            return Plan(
                mode=MODE_PC_HEARTHSTONE, preset_enum=PRESET_PC_HEARTHSTONE,
                brightness=None, color_temp=None, apply_kind=APPLY_SCENE,
                targets=[GROUP_MAIN], lux_gate_on=lux_gate_on, reason="pc_hearthstone",
            )

    # 11) cinema — Entertainment stabil an + kein Gast (R8).
    if ctx.entertainment_stable and not ctx.guest:
        return Plan(
            mode=MODE_CINEMA, preset_enum=MODE_CINEMA, brightness=None, color_temp=None,
            apply_kind=APPLY_SCENE, targets=[GROUP_MAIN], exclusive_off=[GROUP_CEILING],
            lux_gate_on=lux_gate_on, reason="cinema: entertainment_stable on, kein Gast",
        )

    # 12) Tagesphase-Fallback — saisonales Preset der aktuellen Detailphase.
    phase = awake_phase or "early_evening"
    return Plan(
        mode=phase, preset_enum=_phase_preset(ctx, phase),
        brightness=_brightness(profile, phase), color_temp=None,
        apply_kind=APPLY_SCENE, targets=[GROUP_MAIN], lux_gate_on=lux_gate_on,
        reason=f"dayphase fallback: {phase}",
    )


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
