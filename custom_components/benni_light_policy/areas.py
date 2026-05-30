"""Bereichs-Controller (R14 Flur, R15 Bad, R17 Ring).

Eigenständige, event-/timer-getriebene Sub-Systeme. Jeder Controller hört auf
seine eigenen Quell-Entities und steuert direkt Geräte (Flur/Bad: `light.*`,
Ring: Aqara) — alles gated an `coord.apply_enabled` (Shadow-safe).

Getrennt vom Wohnzimmer-Plan und von Scene Presets (KH-9: Ring → Aqara).
Verifizierbar erst in HA (Timer + Service-Calls).
"""
from __future__ import annotations

import asyncio
import logging

from homeassistant.core import CALLBACK_TYPE, Event, callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event

from .const import (
    AQARA_DOMAIN,
    AQARA_SERVICE_SET_EFFECT,
    BATHROOM_TIMEOUT_SECONDS,
    CONF_ACTIVITY_STATE,
    CONF_BATHROOM_LIGHT,
    CONF_BATHROOM_VIBRATION,
    CONF_BATHROOM_TIMEOUT,
    CONF_HALLWAY_LIGHT,
    CONF_HALLWAY_TRIGGERS,
    CONF_MAPPINGS,
    CONF_RING_PRESET_MAP,
    CONF_RING_TARGETS,
    HALLWAY_COLOR_TEMP,
    HALLWAY_OFF_REPEAT_DELAY,
    HALLWAY_OFF_REPEATS,
    HALLWAY_TIMER_SECONDS,
    SUBENTRY_BATHROOM,
    SUBENTRY_HALLWAY,
    SUBENTRY_NOTIFICATION_RING,
)

_LOGGER = logging.getLogger(__name__)

_ON_STATES = ("on", "open", "true", "1", "detected", "motion")


def _is_on(state: str | None) -> bool:
    return (state or "").lower() in _ON_STATES


class _AreaBase:
    """Ein Controller pro Subentry. `data` = die Subentry-Config (nur eigene Felder)."""

    def __init__(self, coord, data: dict) -> None:
        self.coord = coord
        self.hass = coord.hass
        self._data = dict(data)
        self._unsub: list[CALLBACK_TYPE] = []

    @property
    def apply_enabled(self) -> bool:
        return self.coord.apply_enabled

    def opt(self, key, default=None):
        return self._data.get(key, default)

    def start(self) -> None:  # pragma: no cover - HA wiring
        raise NotImplementedError

    def stop(self) -> None:
        for unsub in self._unsub:
            unsub()
        self._unsub.clear()


class HallwayController(_AreaBase):
    """R14: Tür/Bewegung + draußen dunkel → Flurlicht an + 2-Min-Auto-Off."""

    def __init__(self, coord, data: dict) -> None:
        super().__init__(coord, data)
        self._timer_unsub: CALLBACK_TYPE | None = None
        self._off_task: asyncio.Task | None = None

    def start(self) -> None:
        light = self.opt(CONF_HALLWAY_LIGHT)
        triggers = self.opt(CONF_HALLWAY_TRIGGERS) or []
        if not light or not triggers:
            return
        self._unsub.append(
            async_track_state_change_event(self.hass, list(triggers), self._on_trigger)
        )

    @callback
    def _on_trigger(self, event: Event) -> None:
        new = event.data.get("new_state")
        if new is None or not _is_on(new.state):
            return
        if not self.apply_enabled or not self.coord.lux_gate_on():
            return
        self.hass.async_create_task(self._activate())

    async def _activate(self) -> None:
        light = self.opt(CONF_HALLWAY_LIGHT)
        if self._off_task and not self._off_task.done():
            self._off_task.cancel()
        brightness = self.coord.brightness_for(self.coord.current_day_state())
        await self.hass.services.async_call(
            "light", "turn_on",
            {"entity_id": light, "brightness": brightness or 200,
             "color_temp_kelvin": HALLWAY_COLOR_TEMP},
            blocking=False,
        )
        self._reset_timer()

    def _reset_timer(self) -> None:
        if self._timer_unsub is not None:
            self._timer_unsub()

        @callback
        def _fire(_now) -> None:
            self._timer_unsub = None
            self._off_task = self.hass.async_create_task(self._auto_off())

        self._timer_unsub = async_call_later(self.hass, HALLWAY_TIMER_SECONDS, _fire)

    async def _auto_off(self) -> None:
        light = self.opt(CONF_HALLWAY_LIGHT)
        try:
            for i in range(HALLWAY_OFF_REPEATS):
                await self.hass.services.async_call(
                    "light", "turn_off", {"entity_id": light}, blocking=False
                )
                if i < HALLWAY_OFF_REPEATS - 1:
                    await asyncio.sleep(HALLWAY_OFF_REPEAT_DELAY)
        except asyncio.CancelledError:
            raise

    def stop(self) -> None:
        super().stop()
        if self._timer_unsub is not None:
            self._timer_unsub()
            self._timer_unsub = None
        if self._off_task and not self._off_task.done():
            self._off_task.cancel()


class BathroomController(_AreaBase):
    """R15: Badlicht an > 60 min ohne Klodeckel-Vibration → ausschalten."""

    def __init__(self, coord, data: dict) -> None:
        super().__init__(coord, data)
        self._timer_unsub: CALLBACK_TYPE | None = None

    def start(self) -> None:
        light = self.opt(CONF_BATHROOM_LIGHT)
        if not light:
            return
        watch = [light]
        vib = self.opt(CONF_BATHROOM_VIBRATION)
        if vib:
            watch.append(vib)
        self._unsub.append(
            async_track_state_change_event(self.hass, watch, self._on_change)
        )

    @callback
    def _on_change(self, event: Event) -> None:
        eid = event.data.get("entity_id")
        new = event.data.get("new_state")
        light = self.opt(CONF_BATHROOM_LIGHT)
        vib = self.opt(CONF_BATHROOM_VIBRATION)

        if eid == light:
            if new and _is_on(new.state):
                self._start_timer()       # Licht an → Vergessens-Timer starten
            else:
                self._cancel_timer()      # Licht aus → Timer abbrechen
        elif eid == vib and new and _is_on(new.state):
            # Aktivität am Klodeckel → Timer resetten (nur wenn Licht an).
            st = self.hass.states.get(light)
            if st and _is_on(st.state):
                self._start_timer()

    def _start_timer(self) -> None:
        self._cancel_timer()

        @callback
        def _fire(_now) -> None:
            self._timer_unsub = None
            if self.apply_enabled:
                # Domain-agnostisch: Bad-Licht kann light.* ODER switch.*
                # (z.B. Shelly) sein. homeassistant.turn_off dispatcht korrekt.
                self.hass.async_create_task(
                    self.hass.services.async_call(
                        "homeassistant", "turn_off",
                        {"entity_id": self.opt(CONF_BATHROOM_LIGHT)}, blocking=False,
                    )
                )

        timeout = int(self.opt(CONF_BATHROOM_TIMEOUT) or BATHROOM_TIMEOUT_SECONDS)
        self._timer_unsub = async_call_later(self.hass, timeout, _fire)

    def _cancel_timer(self) -> None:
        if self._timer_unsub is not None:
            self._timer_unsub()
            self._timer_unsub = None

    def stop(self) -> None:
        super().stop()
        self._cancel_timer()


class RingController(_AreaBase):
    """R17: T1M RGB Ring zeigt den Activity State via Aqara Advanced Lighting.

    Preset-Namen pro Activity State sind OQ-1 (nach Inbetriebnahme) — solange keine
    Map konfiguriert ist, wird nur der ring_mode-Sensor gepflegt (kein Service-Call).
    """

    def start(self) -> None:
        # Activity-Quelle: Subentry-Override, sonst die des Hubs.
        activity = self.opt(CONF_ACTIVITY_STATE) or self.coord.get_option(CONF_ACTIVITY_STATE)
        if not activity:
            return
        self._activity = activity
        self._unsub.append(
            async_track_state_change_event(self.hass, [activity], self._on_activity)
        )

    @callback
    def _on_activity(self, event: Event) -> None:
        new = event.data.get("new_state")
        if new is None:
            return
        self.coord.set_ring_mode(new.state)
        targets = self.opt(CONF_RING_TARGETS) or []
        if isinstance(targets, str):
            targets = [targets]
        # Minihub-Mapping (activity_state-Wert → Aqara-Effekt-Name).
        # Backward-Compat: alter CONF_RING_PRESET_MAP wird noch akzeptiert.
        preset_map = self.opt(CONF_MAPPINGS) or self.opt(CONF_RING_PRESET_MAP) or {}
        effect = preset_map.get(new.state)
        if not (self.apply_enabled and targets and effect):
            return
        # Simultan auf ALLE Ringe (z.B. Wohnzimmer + Küche) denselben Effekt.
        self.hass.async_create_task(
            self.hass.services.async_call(
                AQARA_DOMAIN, AQARA_SERVICE_SET_EFFECT,
                {"entity_id": list(targets), "effect": effect}, blocking=False,
            )
        )


_CONTROLLER_BY_TYPE = {
    SUBENTRY_HALLWAY: HallwayController,
    SUBENTRY_BATHROOM: BathroomController,
    SUBENTRY_NOTIFICATION_RING: RingController,
}


def build_controllers_from_subentries(coord, subentries) -> list[_AreaBase]:
    """Pro passendem Subentry ein Controller mit dessen eigener Config."""
    out: list[_AreaBase] = []
    for sub in subentries:
        cls = _CONTROLLER_BY_TYPE.get(sub.subentry_type)
        if cls is not None:
            out.append(cls(coord, dict(sub.data)))
    return out
