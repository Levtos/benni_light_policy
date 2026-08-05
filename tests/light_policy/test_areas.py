"""Lifecycle tests for the HA-facing area controllers using small HA doubles."""
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import types


def _install_homeassistant_doubles() -> None:
    if "homeassistant.core" in sys.modules:
        return
    homeassistant = types.ModuleType("homeassistant")
    helpers = types.ModuleType("homeassistant.helpers")
    core = types.ModuleType("homeassistant.core")
    event = types.ModuleType("homeassistant.helpers.event")

    core.CALLBACK_TYPE = object
    core.Event = object
    core.callback = lambda func: func

    def _track(_hass, _entities, callback):
        _hass.callbacks.append(callback)

        def _unsubscribe():
            _hass.unsubscribed += 1

        return _unsubscribe

    def _later(_hass, _delay, callback):
        _hass.timers.append(callback)

        def _unsubscribe():
            _hass.timer_unsubscribed += 1

        return _unsubscribe

    event.async_track_state_change_event = _track
    event.async_call_later = _later
    homeassistant.helpers = helpers
    helpers.event = event
    sys.modules.update({
        "homeassistant": homeassistant,
        "homeassistant.helpers": helpers,
        "homeassistant.core": core,
        "homeassistant.helpers.event": event,
    })


_install_homeassistant_doubles()

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AREAS_PATH = os.path.join(ROOT, "custom_components", "benni_light_policy", "areas.py")
spec = importlib.util.spec_from_file_location("lp_pure_pkg.areas", AREAS_PATH)
areas = importlib.util.module_from_spec(spec)
sys.modules["lp_pure_pkg.areas"] = areas
spec.loader.exec_module(areas)

import lp_const as C  # noqa: E402


class _State:
    def __init__(self, state: str) -> None:
        self.state = state


class _States:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = {key: _State(value) for key, value in values.items()}

    def get(self, entity_id: str):
        return self.values.get(entity_id)


class _Services:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict, bool]] = []

    async def async_call(self, domain, service, data, *, blocking):
        self.calls.append((domain, service, data, blocking))


class _Hass:
    def __init__(self, states: dict[str, str]) -> None:
        self.states = _States(states)
        self.services = _Services()
        self.callbacks = []
        self.timers = []
        self.unsubscribed = 0
        self.timer_unsubscribed = 0

    def async_create_task(self, coro):
        return asyncio.create_task(coro)


class _Coord:
    apply_enabled = True

    def __init__(self, hass: _Hass) -> None:
        self.hass = hass
        self.ring_modes: list[str] = []

    def get_option(self, key, default=None):
        return default

    def set_ring_mode(self, mode):
        self.ring_modes.append(mode)

    def lux_gate_on(self):
        return True

    def current_day_state(self):
        return "evening"

    def brightness_for(self, _key):
        return 200


def test_bathroom_start_sees_existing_on_light_and_stop_cleans_timer():
    hass = _Hass({"switch.bathroom": "on"})
    coord = _Coord(hass)
    controller = areas.BathroomController(coord, {
        C.CONF_BATHROOM_LIGHT: "switch.bathroom",
        C.CONF_BATHROOM_TIMEOUT: 120,
    })

    controller.start()

    assert len(hass.timers) == 1
    controller.stop()
    assert hass.unsubscribed == 1
    assert hass.timer_unsubscribed == 1


def test_bathroom_invalid_legacy_timeout_is_safe():
    hass = _Hass({"light.bathroom": "on"})
    controller = areas.BathroomController(_Coord(hass), {
        C.CONF_BATHROOM_LIGHT: "light.bathroom",
        C.CONF_BATHROOM_TIMEOUT: "invalid",
    })

    controller.start()

    assert len(hass.timers) == 1


def test_ring_start_applies_current_activity_once():
    async def _run() -> None:
        hass = _Hass({"sensor.activity": "gaming"})
        coord = _Coord(hass)
        controller = areas.RingController(coord, {
            C.CONF_ACTIVITY_STATE: "sensor.activity",
            C.CONF_RING_TARGETS: ["light.ring"],
            C.CONF_MAPPINGS: {"gaming": "gaming_effect"},
        })

        controller.start()
        await asyncio.sleep(0)

        assert coord.ring_modes == ["gaming"]
        assert hass.services.calls[0][0:2] == (C.AQARA_DOMAIN, C.AQARA_SERVICE_SET_EFFECT)
        controller.stop()

    asyncio.run(_run())


def test_ring_ignores_unknown_activity_and_invalid_mapping():
    async def _run() -> None:
        hass = _Hass({"sensor.activity": "unknown"})
        coord = _Coord(hass)
        controller = areas.RingController(coord, {
            C.CONF_ACTIVITY_STATE: "sensor.activity",
            C.CONF_RING_TARGETS: ["light.ring"],
            C.CONF_MAPPINGS: ["not-a-map"],
        })

        controller.start()
        await asyncio.sleep(0)

        assert coord.ring_modes == []
        assert hass.services.calls == []
        controller.stop()

    asyncio.run(_run())
