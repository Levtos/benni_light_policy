"""Light-Policy-Coordinator (Single-Instance).

Hört auf alle Quell-Entities, rechnet bei jedem Trigger eine neue Decision
(`policy.decide`) und wendet sie an — aber nur wenn `apply_enabled` an ist.
Default ist `apply_enabled=False` (Shadow-safe für Phase-4-Cut-Over).

Apply läuft über die Look-Ebene von benni_scene_presets: pro Decision EIN
`apply_look {look, brightness}`. Der Look trägt Targets, Off-Bindings und Crossfade
selbst (`look_transition`); apply_look stoppt überschneidende Lampen, Off-Bindings
clearen den Rest. Brightness kommt aus der Tagesphase. Ausnahmen: wake_up (freie
raw_targets) = direkter light.turn_on; Hard-Off = light.turn_off auf GROUP_ALL.
Script-Modus `restart` wird durch Abbrechen eines laufenden Apply-Tasks nachgebildet.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

try:
    from homeassistant.helpers.start import async_at_started
except Exception:  # pragma: no cover
    async_at_started = None  # type: ignore[assignment]

from . import areas, policy
from .const import (
    BIO_AWAKE,
    BIO_SLEEP,
    CONF_ACTIVITY_STATE,
    CONF_APPLY_ENABLED,
    CONF_BIO_STATE,
    CONF_BRIGHTNESS,
    CONF_CALENDAR_THEME,
    CONF_CLASSIFIER_ENTITY,
    CONF_CROSSFADE_SECONDS,
    CONF_DAY_STATE,
    CONF_ENTERTAINMENT_STABLE,
    CONF_GROUP_ALL,
    CONF_GROUP_CEILING,
    CONF_GROUP_MAIN,
    CONF_GUEST,
    CONF_LOOK_MAP,
    CONF_LUX,
    CONF_LUX_THRESHOLDS,
    CONF_OVERNIGHT_AWAY,
    CONF_PRESENCE_HOUSEHOLD,
    CONF_PRESENCE_PERSONAL,
    CONF_PRESENCE_TRANSITION,
    CONF_REQUIRE_BIRTHDAY,
    CONF_SCENE_INTERVAL_SECONDS,
    CONF_SEASON,
    CONF_STARTUP_BLOCK_SECONDS,
    CONF_SYSTEM_READY,
    CONF_TITLE_CLASSIFIER,
    CONF_MAPPINGS,
    CONF_MEDIA_CONTEXT,
    CONF_MEDIA_DEVICE,
    CONF_SOURCE_ID,
    CONF_SOURCE_PRIORITY,
    CONF_TRIGGER_VALUE,
    CONF_WAKE_UP_TARGETS,
    CONF_WEATHER,
    GAMING_DEFAULT_PRIORITY,
    DEFAULT_APPLY_ENABLED,
    DEFAULT_BRIGHTNESS,
    DEFAULT_CROSSFADE_SECONDS,
    DEFAULT_LUX_THRESHOLDS,
    DEFAULT_SCENE_INTERVAL_SECONDS,
    DEFAULT_STARTUP_BLOCK_SECONDS,
    SEASON_WINTER,
    GROUP_ALL,
    GROUP_CEILING,
    GROUP_MAIN,
    PHASE_EARLY_MORNING,
    PRESENCE_TRANSITION_COMING_HOME,
    SCENE_PRESETS_DOMAIN,
    SUBENTRY_GAMING,
    SUBENTRY_MUSIC,
    SUBENTRY_WAKE_UP,
    TMC_FALLBACK_HOUR,
    TMC_TRIGGER_LUX,
    WEATHER_DARK_WINDOW_SECONDS,
    SP_SERVICE_APPLY_LOOK,
    SP_ATTR_LOOK,
    SP_ATTR_BRIGHTNESS,
)
from .policy import APPLY_CCT, APPLY_OFF, APPLY_SCENE
from .storage import make_store

_LOGGER = logging.getLogger(__name__)

RECENT_APPLY_GUARD_SECONDS = 8  # eigener Schreibvorgang ≠ externe Interaktion


def _bool_state(s: str | None) -> bool | None:
    if s is None or s in ("unknown", "unavailable"):
        return None
    return s.lower() in ("on", "true", "1", "home", "active", "playing")


def _float_or_none(s: str | None) -> float | None:
    if s in (None, "", "unknown", "unavailable"):
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


class LightPolicyCoordinator:
    """Eine Instanz pro Config-Entry (Single-Instance-Modell)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._store = make_store(hass, entry.entry_id)
        self._unsub: list[CALLBACK_TYPE] = []
        self._listeners: list[CALLBACK_TYPE] = []

        self._started_at = time.monotonic()
        self._ha_started = False

        self._prev_lux_gate: bool | None = None
        self._prev_bio: str | None = None
        self._manual_off = False

        self._tmc_set = False
        self._prev_day_state: str | None = None
        self._prev_presence_transition: str | None = None
        self._lux_history: list[tuple[float, float]] = []  # (monotonic_ts, lux)

        self._last_plan: policy.Plan | None = None
        self._last_apply_ts = 0.0
        self._apply_task: asyncio.Task | None = None

        self._areas: list = []
        self._ring_mode: str | None = None
        self._last_weather_dark = False

    # ----- options helpers -----
    @property
    def _opts(self) -> dict[str, Any]:
        return {**self.entry.data, **self.entry.options}

    def _opt(self, key: str, default: Any = None) -> Any:
        return self._opts.get(key, default)

    @property
    def apply_enabled(self) -> bool:
        return bool(self._opt(CONF_APPLY_ENABLED, DEFAULT_APPLY_ENABLED))

    @property
    def startup_block_seconds(self) -> int:
        return int(self._opt(CONF_STARTUP_BLOCK_SECONDS, DEFAULT_STARTUP_BLOCK_SECONDS))

    @property
    def crossfade_seconds(self) -> int:
        return int(self._opt(CONF_CROSSFADE_SECONDS, DEFAULT_CROSSFADE_SECONDS))

    @property
    def scene_interval_seconds(self) -> int:
        return int(self._opt(CONF_SCENE_INTERVAL_SECONDS, DEFAULT_SCENE_INTERVAL_SECONDS))

    @property
    def manual_off_active(self) -> bool:
        return self._manual_off

    @property
    def look_map(self) -> dict[str, str]:
        """Zentrale Map policy_key -> Look-Ref (Slug/Name). Aus den Options."""
        raw = self._opt(CONF_LOOK_MAP) or {}
        return dict(raw) if isinstance(raw, dict) else {}

    def resolve_look_ref(self, policy_key: str | None) -> str | None:
        """policy_key -> Look-Ref. Map gewinnt; sonst Key selbst (Fallback ohne
        Namenskonvention). Leere Map-Werte werden ignoriert."""
        if not policy_key:
            return None
        mapped = self.look_map.get(policy_key)
        return mapped.strip() if isinstance(mapped, str) and mapped.strip() else policy_key

    def _startup_ready(self) -> bool:
        if not self._ha_started:
            return False
        return (time.monotonic() - self._started_at) >= self.startup_block_seconds

    # ----- lifecycle -----
    @callback
    def async_start(self) -> None:
        if async_at_started is not None:
            self._unsub.append(async_at_started(self.hass, self._on_started))
        elif self.hass.is_running:
            self._on_started(None)
        else:
            self._unsub.append(
                self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, self._on_started)
            )

        watch: set[str] = set()
        for key in (
            CONF_BIO_STATE, CONF_DAY_STATE, CONF_ACTIVITY_STATE, CONF_LUX,
            CONF_PRESENCE_PERSONAL, CONF_PRESENCE_HOUSEHOLD, CONF_GUEST,
            CONF_PRESENCE_TRANSITION,
            CONF_SEASON, CONF_CALENDAR_THEME,
            CONF_ENTERTAINMENT_STABLE, CONF_MEDIA_DEVICE, CONF_MEDIA_CONTEXT,
            CONF_OVERNIGHT_AWAY, CONF_SYSTEM_READY,
            CONF_WEATHER,
            CONF_GROUP_MAIN, CONF_GROUP_CEILING, CONF_GROUP_ALL,
        ):
            v = self._opt(key)
            if isinstance(v, str) and v:
                watch.add(v)
        # Subentry-Quellen (Gaming/Musik-Classifier) mitbeobachten.
        for sub in self.entry.subentries.values():
            v = sub.data.get(CONF_CLASSIFIER_ENTITY)
            if isinstance(v, str) and v:
                watch.add(v)

        if watch:
            self._unsub.append(
                async_track_state_change_event(self.hass, list(watch), self._on_state_change)
            )
        self._unsub.append(
            async_track_time_interval(self.hass, self._on_interval, timedelta(seconds=30))
        )

        # Bereichs-Controller je Subentry (Flur/Bad/Notification-RGB) starten.
        self._areas = areas.build_controllers_from_subentries(self, self.entry.subentries.values())
        for ctrl in self._areas:
            ctrl.start()

    @callback
    def async_stop(self) -> None:
        for unsub in self._unsub:
            unsub()
        self._unsub.clear()
        for ctrl in self._areas:
            ctrl.stop()
        self._areas = []
        if self._apply_task and not self._apply_task.done():
            self._apply_task.cancel()

    @callback
    def _on_started(self, _event) -> None:
        self._ha_started = True
        self._started_at = time.monotonic()
        self.hass.async_create_task(self.async_evaluate())

    @callback
    def _on_interval(self, _now) -> None:
        self.hass.async_create_task(self.async_evaluate())

    @callback
    def _on_state_change(self, _event: Event) -> None:
        self.hass.async_create_task(self.async_evaluate())

    # ----- persistence -----
    async def async_load(self) -> None:
        raw = await self._store.async_load() or {}
        self._prev_lux_gate = raw.get("lux_gate")
        self._manual_off = bool(raw.get("manual_off", False))
        self._prev_bio = raw.get("prev_bio")
        self._tmc_set = bool(raw.get("tmc_set", False))
        self._prev_day_state = raw.get("prev_day_state")

    async def _async_save(self) -> None:
        await self._store.async_save({
            "lux_gate": self._prev_lux_gate,
            "manual_off": self._manual_off,
            "prev_bio": self._prev_bio,
            "tmc_set": self._tmc_set,
            "prev_day_state": self._prev_day_state,
            "last_plan": self._last_plan.as_dict() if self._last_plan else None,
        })

    # ----- context -----
    def _read(self, key: str) -> str | None:
        eid = self._opt(key)
        if not eid:
            return None
        st = self.hass.states.get(eid)
        if st is None or st.state in ("unknown", "unavailable"):
            return None
        return st.state

    def _read_attr(self, key: str, attr: str) -> str | None:
        eid = self._opt(key)
        if not eid:
            return None
        st = self.hass.states.get(eid)
        if st is None:
            return None
        val = st.attributes.get(attr)
        return str(val) if val is not None else None

    def build_context(self) -> policy.Context:
        return policy.Context(
            bio_state=self._read(CONF_BIO_STATE),
            day_state=self._read(CONF_DAY_STATE),
            master_phase=self._read_attr(CONF_DAY_STATE, "master_phase"),
            activity_state=self._read(CONF_ACTIVITY_STATE),
            presence_personal=self._read(CONF_PRESENCE_PERSONAL),
            presence_household=self._read(CONF_PRESENCE_HOUSEHOLD),
            guest=_bool_state(self._read(CONF_GUEST)),
            season=self._read(CONF_SEASON),
            calendar_theme=self._read(CONF_CALENDAR_THEME),
            title_classifier=self._read(CONF_TITLE_CLASSIFIER),
            entertainment_stable=_bool_state(self._read(CONF_ENTERTAINMENT_STABLE)),
            media_device=self._read(CONF_MEDIA_DEVICE),
            media_context=self._read(CONF_MEDIA_CONTEXT),
            overnight_away=_bool_state(self._read(CONF_OVERNIGHT_AWAY)),
            presence_transition=self._read(CONF_PRESENCE_TRANSITION),
            lux=_float_or_none(self._read(CONF_LUX)),
            weather=self._read(CONF_WEATHER),
        )

    # ----- evaluation -----
    def _update_tmc(self, ctx: policy.Context) -> None:
        """R2: TMC-Latch setzen/zurücksetzen. „War es heute schon hell?"."""
        # Reset bei Eintritt in early_morning.
        if ctx.day_state == PHASE_EARLY_MORNING and self._prev_day_state != PHASE_EARLY_MORNING:
            self._tmc_set = False
        self._prev_day_state = ctx.day_state
        if self._tmc_set:
            return
        if ctx.lux is not None and ctx.lux > TMC_TRIGGER_LUX:
            self._tmc_set = True
            return
        # Fallback 09:00 wenn User wach.
        if dt_util.now().hour >= TMC_FALLBACK_HOUR and ctx.bio_state == BIO_AWAKE:
            self._tmc_set = True

    def _weather_dark(self, ctx: policy.Context) -> bool:
        """R10: gleitender 10-min-Lux-Baseline-Vergleich + Wetter-Icon."""
        now = time.monotonic()
        if ctx.lux is not None:
            self._lux_history.append((now, ctx.lux))
        cutoff = now - WEATHER_DARK_WINDOW_SECONDS
        self._lux_history = [(t, v) for (t, v) in self._lux_history if t >= cutoff]
        baseline = self._lux_history[0][1] if self._lux_history else None
        return policy.weather_darkness(ctx.lux, baseline, ctx.weather, ctx.master_phase)

    async def async_evaluate(self) -> policy.Plan:
        ctx = self.build_context()
        self._update_tmc(ctx)
        weather_dark = self._weather_dark(ctx)
        self._last_weather_dark = weather_dark

        gate = policy.lux_gate(
            ctx.lux, ctx.season, self._prev_lux_gate,
            day_state_known=ctx.day_state is not None,
            tmc_set=self._tmc_set,
            weather_dark=weather_dark,
            thresholds=self._opt(CONF_LUX_THRESHOLDS),
        )
        self._prev_lux_gate = gate

        # R9-Reset: Manual-Off löst sich automatisch bei Bio-Übergang sleep → awake.
        if self._prev_bio == BIO_SLEEP and ctx.bio_state == BIO_AWAKE and self._manual_off:
            self._manual_off = False
        self._prev_bio = ctx.bio_state

        # R12 Heimkommen: coming_home-Flanke erzwingt einen Re-Apply (last_plan reset),
        # damit das Licht sofort sitzt, auch wenn presence_personal erst gleich umflippt.
        if (
            self._prev_presence_transition != PRESENCE_TRANSITION_COMING_HOME
            and ctx.presence_transition == PRESENCE_TRANSITION_COMING_HOME
        ):
            self._last_plan = None
        self._prev_presence_transition = ctx.presence_transition

        plan = policy.decide(
            ctx,
            lux_gate_on=gate,
            startup_ready=self._startup_ready(),
            apply_enabled=self.apply_enabled,
            manual_off_active=self._manual_off,
            brightness_profile=self._opt(CONF_BRIGHTNESS),
            extra_policies=self._build_extra_policies(),
        )

        hash_changed = self._last_plan is None or self._last_plan.scene_hash != plan.scene_hash
        self._last_plan = plan

        if plan.apply_allowed and hash_changed:
            self._schedule_apply(plan)

        await self._async_save()
        for cb in self._listeners:
            cb()
        return plan

    def _read_entity(self, eid: str | None) -> str | None:
        if not eid:
            return None
        st = self.hass.states.get(eid)
        if st is None or st.state in ("unknown", "unavailable"):
            return None
        return st.state

    def _build_extra_policies(self) -> list[policy.PolicyDef]:
        """Subentry-getriebene Policies: Gaming/Musik (Classifier+Mapping)
        + Wake-Up (vereinigte Ziel-Lampen aller wake_up-Subentries)."""
        out: list[policy.PolicyDef] = []
        wake_up_targets: list[str] = []
        for sub in self.entry.subentries.values():
            d = sub.data
            if sub.subentry_type == SUBENTRY_WAKE_UP:
                for eid in (d.get(CONF_WAKE_UP_TARGETS) or []):
                    if isinstance(eid, str) and eid and eid not in wake_up_targets:
                        wake_up_targets.append(eid)
                continue
            # Minihub: mappings = dict {classifier_value (str) → preset_uuid (str)}
            mappings = d.get(CONF_MAPPINGS) or {}
            if not isinstance(mappings, dict) or not mappings:
                continue
            value = self._read_entity(d.get(CONF_CLASSIFIER_ENTITY))
            if sub.subentry_type == SUBENTRY_GAMING:
                source_id = (d.get(CONF_SOURCE_ID) or "").strip().lower()
                if not source_id:
                    continue
                priority = int(d.get(CONF_SOURCE_PRIORITY)
                               or GAMING_DEFAULT_PRIORITY.get(source_id, policy.PRIO_GAMING))
                out.append(policy.make_gaming_policy(
                    source_id, value, mappings, priority=priority,
                ))
            elif sub.subentry_type == SUBENTRY_MUSIC:
                out.append(policy.make_music_policy(
                    value, mappings,
                    require_birthday=bool(d.get(CONF_REQUIRE_BIRTHDAY, True)),
                ))
        if wake_up_targets:
            out.append(policy.make_wake_up_policy(wake_up_targets))
        return out

    # (R16 Bettgeh-Signal entfernt — User: stattdessen Wake-Up via wake_planner.)

    # ----- apply (gated, R3/R3b Crossfade) -----
    def _resolve_targets(self, logical: list[str]) -> list[str]:
        mapping = {
            GROUP_MAIN: self._opt(CONF_GROUP_MAIN),
            GROUP_CEILING: self._opt(CONF_GROUP_CEILING),
            GROUP_ALL: self._opt(CONF_GROUP_ALL),
        }
        out: list[str] = []
        for g in logical:
            val = mapping.get(g)
            if not val:
                continue
            if isinstance(val, str):
                out.append(val)
            else:  # Liste von Einzellampen
                out.extend(val)
        # Duplikate raus, Reihenfolge erhalten (z.B. GROUP_ALL ∪ GROUP_MAIN).
        seen: set[str] = set()
        return [e for e in out if not (e in seen or seen.add(e))]

    def _schedule_apply(self, plan: policy.Plan) -> None:
        # mode: restart — laufenden Crossfade abbrechen, neuen starten.
        if self._apply_task and not self._apply_task.done():
            self._apply_task.cancel()
        self._apply_task = self.hass.async_create_task(self._apply(plan))

    async def _apply(self, plan: policy.Plan) -> None:
        try:
            self._last_apply_ts = time.monotonic()

            if plan.apply_kind == APPLY_OFF:
                await self._turn_off(
                    self._resolve_targets([GROUP_ALL])
                    or self._resolve_targets(plan.exclusive_off)
                )
                return

            # wake_up-Sonderfall: freie raw_targets, kein Look → direkter CCT-turn_on.
            if plan.apply_kind == APPLY_CCT and not plan.preset_enum:
                if not plan.raw_targets:
                    _LOGGER.warning("light_policy: %s ohne konfigurierte Targets", plan.mode)
                    return
                await self.hass.services.async_call(
                    "light", "turn_on",
                    {
                        "entity_id": list(plan.raw_targets),
                        "brightness": plan.brightness,
                        "color_temp_kelvin": plan.color_temp,
                        "transition": min(self.crossfade_seconds, 30),
                    },
                    blocking=False,
                )
                return

            # Alle übrigen Modi (CCT-Kelvin-Look + Szene): EIN apply_look. Der Look trägt
            # Targets, Off-Bindings und Crossfade selbst; apply_look stoppt überschneidende
            # Lampen, Off-Bindings clearen den Rest. Brightness kommt aus der Tagesphase.
            # Der Policy-Key (preset_enum) wird über die zentrale Look-Map auf einen echten
            # Look-Ref (Slug/Name) aufgelöst — fällt auf den Key selbst zurück.
            look_ref = self.resolve_look_ref(plan.preset_enum)
            if not look_ref:
                _LOGGER.warning(
                    "light_policy: apply übersprungen — keine Look-Ref (mode=%s)", plan.mode
                )
                return
            data: dict[str, Any] = {SP_ATTR_LOOK: look_ref}
            if plan.brightness:
                data[SP_ATTR_BRIGHTNESS] = plan.brightness
            await self.hass.services.async_call(
                SCENE_PRESETS_DOMAIN, SP_SERVICE_APPLY_LOOK, data, blocking=False,
            )
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001 - ein fehlgeschlagener Apply darf den Loop nicht killen
            _LOGGER.warning("light_policy: apply failed: %s", err)

    async def _turn_off(self, targets: list[str]) -> None:
        if not targets:
            return
        await self.hass.services.async_call(
            "light", "turn_off", {"entity_id": targets}, blocking=False,
        )

    # ----- service surface -----
    async def async_apply_now(self) -> policy.Plan:
        self._last_plan = None  # erzwingt hash_changed → Re-Apply
        return await self.async_evaluate()

    async def async_set_manual_off(self) -> None:
        self._manual_off = True
        await self.async_evaluate()

    async def async_clear_manual_off(self) -> None:
        self._manual_off = False
        await self.async_evaluate()

    async def async_set_apply_enabled(self, value: bool) -> None:
        """Apply zur Laufzeit an/aus (vom Apply-Switch). Schreibt in die Options →
        Update-Listener lädt den Entry neu, der neue Coordinator liest den Wert."""
        new_options = {**self.entry.options, CONF_APPLY_ENABLED: bool(value)}
        self.hass.config_entries.async_update_entry(self.entry, options=new_options)

    async def async_set_look_map(self, mapping: dict[str, str]) -> dict[str, str]:
        """Zentrale Look-Map schreiben (policy_key -> Look-Ref). Leere Werte werden
        entfernt (= Mapping gelöscht). Schreibt in die Options → Reload-Listener."""
        cleaned = {
            str(k): str(v).strip()
            for k, v in (mapping or {}).items()
            if isinstance(v, str) and v.strip()
        }
        new_options = {**self.entry.options, CONF_LOOK_MAP: cleaned}
        self.hass.config_entries.async_update_entry(self.entry, options=new_options)
        return cleaned

    async def async_set_subentry_mappings(
        self, subentry_id: str, mappings: dict[str, str]
    ) -> dict[str, str]:
        """Gaming/Musik/Ring-Subentry: classifier_value -> Look-Ref schreiben.
        Aktualisiert die Subentry-Daten (kein UUID/Preset mehr)."""
        sub = self.entry.subentries.get(subentry_id)
        if sub is None:
            raise ValueError(f"unknown subentry {subentry_id}")
        cleaned = {
            str(k).strip(): str(v).strip()
            for k, v in (mappings or {}).items()
            if str(k).strip() and isinstance(v, str) and v.strip()
        }
        new_data = {**sub.data, CONF_MAPPINGS: cleaned}
        self.hass.config_entries.async_update_subentry(self.entry, sub, data=new_data)
        return cleaned

    # ----- helpers für Bereichs-Controller -----
    def get_option(self, key: str, default=None):
        return self._opt(key, default)

    def current_day_state(self) -> str | None:
        return self._read(CONF_DAY_STATE)

    def current_activity(self) -> str | None:
        return self._read(CONF_ACTIVITY_STATE)

    def brightness_for(self, key: str | None) -> int | None:
        profile = {**DEFAULT_BRIGHTNESS, **(self._opt(CONF_BRIGHTNESS) or {})}
        return profile.get(key) if key else None

    def lux_gate_on(self) -> bool:
        return bool(self._prev_lux_gate)

    def set_ring_mode(self, mode: str | None) -> None:
        self._ring_mode = mode
        for cb in self._listeners:
            cb()

    @property
    def ring_mode(self) -> str | None:
        return self._ring_mode

    # ----- Lux-Gate-Internals (für Debug-Sensor + Diagnostics) -----
    @property
    def startup_ready(self) -> bool:
        return self._startup_ready()

    def gate_internals(self) -> dict[str, Any]:
        season = self._read(CONF_SEASON)
        thr = self._opt(CONF_LUX_THRESHOLDS) or DEFAULT_LUX_THRESHOLDS
        dark, bright = thr.get(season or SEASON_WINTER, thr[SEASON_WINTER])
        return {
            "lux_gate_on": bool(self._prev_lux_gate),
            "tmc_set": self._tmc_set,
            "weather_dark": self._last_weather_dark,
            "startup_ready": self._startup_ready(),
            "season": season,
            "thresholds": {"dark": dark, "bright": bright},
            "lux_samples": len(self._lux_history),
            "apply_enabled": self.apply_enabled,
            "manual_off_active": self._manual_off,
        }

    # ----- accessors -----
    @property
    def last_plan(self) -> policy.Plan | None:
        return self._last_plan

    def add_listener(self, cb: CALLBACK_TYPE) -> None:
        self._listeners.append(cb)

    def remove_listener(self, cb: CALLBACK_TYPE) -> None:
        if cb in self._listeners:
            self._listeners.remove(cb)
