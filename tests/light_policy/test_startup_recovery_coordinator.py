"""Coordinator handoff and integration coverage for startup Lux recovery."""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import time
import types
from datetime import UTC, datetime, timedelta
from pathlib import Path


def _install_homeassistant_doubles() -> None:
    """Provide only the HA modules required to import the coordinator."""
    homeassistant = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    config_entries = sys.modules.setdefault(
        "homeassistant.config_entries", types.ModuleType("homeassistant.config_entries")
    )
    const = sys.modules.setdefault("homeassistant.const", types.ModuleType("homeassistant.const"))
    core = sys.modules.setdefault("homeassistant.core", types.ModuleType("homeassistant.core"))
    helpers = sys.modules.setdefault("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
    device_registry = sys.modules.setdefault(
        "homeassistant.helpers.device_registry",
        types.ModuleType("homeassistant.helpers.device_registry"),
    )
    entity_registry = sys.modules.setdefault(
        "homeassistant.helpers.entity_registry",
        types.ModuleType("homeassistant.helpers.entity_registry"),
    )
    event = sys.modules.setdefault(
        "homeassistant.helpers.event", types.ModuleType("homeassistant.helpers.event")
    )
    start = sys.modules.setdefault(
        "homeassistant.helpers.start", types.ModuleType("homeassistant.helpers.start")
    )
    storage = sys.modules.setdefault(
        "homeassistant.helpers.storage", types.ModuleType("homeassistant.helpers.storage")
    )
    util = sys.modules.setdefault("homeassistant.util", types.ModuleType("homeassistant.util"))
    dt_util = sys.modules.setdefault("homeassistant.util.dt", types.ModuleType("homeassistant.util.dt"))

    config_entries.ConfigEntry = object
    const.EVENT_HOMEASSISTANT_STARTED = "homeassistant_started"
    core.CALLBACK_TYPE = object
    core.Event = object
    core.HomeAssistant = object
    core.callback = lambda func: func

    def _unsubscribe(*_args, **_kwargs):
        return lambda: None

    def _track_state_change(hass, _entities, callback):
        if hasattr(hass, "callbacks"):
            hass.callbacks.append(callback)
        return _unsubscribe()

    def _track_interval(hass, _interval, callback):
        if hasattr(hass, "timers"):
            hass.timers.append(callback)
        return _unsubscribe()

    event.async_track_state_change_event = _track_state_change
    event.async_track_time_interval = _track_interval
    event.async_call_later = _track_interval
    start.async_at_started = lambda _hass, _callback: _unsubscribe()

    class _Store:
        def __init__(self, *_args, **_kwargs) -> None:
            self.data = None

        async def async_load(self):
            return self.data

        async def async_save(self, data):
            self.data = data

    storage.Store = _Store
    device_registry.async_get = lambda _hass: types.SimpleNamespace(devices={})
    entity_registry.async_get = lambda _hass: types.SimpleNamespace(entities={})
    dt_util.utcnow = lambda: datetime.now(UTC)
    dt_util.now = lambda: datetime.now(UTC)
    dt_util.as_utc = lambda value: (
        value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    )
    dt_util.parse_datetime = lambda value: datetime.fromisoformat(value)

    homeassistant.config_entries = config_entries
    homeassistant.const = const
    homeassistant.core = core
    homeassistant.helpers = helpers
    homeassistant.util = util
    helpers.device_registry = device_registry
    helpers.entity_registry = entity_registry
    helpers.event = event
    helpers.start = start
    helpers.storage = storage
    util.dt = dt_util


_install_homeassistant_doubles()

ROOT = Path(__file__).resolve().parents[2]
COORDINATOR_PATH = ROOT / "custom_components" / "benni_light_policy" / "coordinator.py"
spec = importlib.util.spec_from_file_location("lp_pure_pkg.coordinator", COORDINATOR_PATH)
coordinator = importlib.util.module_from_spec(spec)
sys.modules["lp_pure_pkg.coordinator"] = coordinator
spec.loader.exec_module(coordinator)

import lp_const as C  # noqa: E402
from lp_pure_pkg.startup_recovery import LuxSample, StartupRecoveryState  # noqa: E402

START = datetime(2026, 8, 14, 20, 0, tzinfo=UTC)


class _State:
    def __init__(
        self,
        state: str,
        *,
        attributes: dict | None = None,
        last_reported: datetime | None = None,
        last_updated: datetime | None = None,
        last_changed: datetime | None = None,
    ) -> None:
        self.state = state
        self.attributes = attributes or {}
        self.last_reported = last_reported
        self.last_updated = last_updated
        self.last_changed = last_changed


class _States:
    def __init__(self, values: dict[str, _State]) -> None:
        self.values = values

    def get(self, entity_id: str):
        return self.values.get(entity_id)


class _Hass:
    def __init__(self, states: dict[str, _State]) -> None:
        self.states = _States(states)
        self.data = {}
        self.callbacks = []
        self.timers = []


class _Entry:
    entry_id = "startup-recovery-test"
    options: dict = {}
    subentries: dict = {}

    def __init__(self) -> None:
        self.data = {
            C.CONF_APPLY_ENABLED: True,
            C.CONF_BIO_STATE: "sensor.bio",
            C.CONF_DAY_STATE: "sensor.day",
            C.CONF_LUX: "sensor.lux",
            C.CONF_SEASON: "sensor.season",
        }


def _healthy_contract() -> dict:
    return {
        "available": True,
        "fresh": True,
        "atomic_quality": "ok",
        "fail_safe_active": False,
        "degraded": False,
        "source_available": {"lux_source": True},
    }


def _new_coordinator(
    *,
    lux_value: str = "1",
    lux_attributes: dict | None = None,
    lux_last_reported: datetime | None = None,
) -> coordinator.LightPolicyCoordinator:
    entry = _Entry()
    states = {
        C.DEFAULT_SYSTEM_READY_ENTITY: _State(
            "on",
            attributes={"startup_started_at": START.isoformat()},
            last_reported=START,
        ),
        "sensor.bio": _State("awake"),
        "sensor.day": _State("late_evening"),
        "sensor.season": _State("winter"),
        "sensor.lux": _State(
            lux_value,
            attributes=lux_attributes,
            last_reported=lux_last_reported or START + timedelta(seconds=2),
            last_updated=START + timedelta(seconds=2),
            last_changed=START + timedelta(seconds=2),
        ),
    }
    coord = object.__new__(coordinator.LightPolicyCoordinator)
    coord.hass = _Hass(states)
    coord.entry = entry
    coord._started_at = time.monotonic() - 20
    coord._ha_started = True
    coord._ha_started_at = START
    coord._startup_recovery = StartupRecoveryState()
    coord._last_lux_sample = LuxSample(None, None, "not_started")
    coord._prev_lux_gate = None
    coord._prev_bio = None
    coord._manual_off = False
    coord._tmc_set = False
    coord._prev_day_state = None
    coord._prev_presence_transition = None
    coord._lux_history = []
    coord._last_plan = None
    coord._prev_mode = None
    coord._last_wake_teardown = []
    coord._last_applied_hash = None
    coord._last_applied_look_ref = None
    coord._last_applied_brightness = None
    coord._last_commanded_entities = []
    coord._last_apply_ts = 0.0
    coord._apply_task = None
    coord._evaluation_task = None
    coord._evaluation_pending = False
    coord._evaluation_lock = asyncio.Lock()
    coord._stopping = False
    coord._areas = []
    coord._ring_mode = None
    coord._last_weather_dark = False
    coord._listeners = []
    return coord


def test_coordinator_passes_lux_contract_attributes_for_healthy_one_lux() -> None:
    coord = _new_coordinator(lux_attributes=_healthy_contract())

    sample = coord._lux_sample()
    context = coord.build_context(lux_sample=sample)

    assert sample.fresh is True
    assert sample.value == 1
    assert context.lux == 1


def test_coordinator_uses_last_reported_and_blocks_legacy_one_lux() -> None:
    coord = _new_coordinator(
        lux_last_reported=START - timedelta(seconds=1),
        lux_attributes={},
    )

    sample = coord._lux_sample()

    assert sample.fresh is False
    assert sample.reason == "stale_before_start"


def test_integration_recovers_once_on_healthy_post_start_one_lux() -> None:
    async def _run() -> None:
        coord = _new_coordinator(lux_attributes=_healthy_contract())
        scheduled: list = []

        coord._schedule_apply = lambda plan, **_kwargs: scheduled.append(plan)

        async def _save() -> None:
            return None

        coord._async_save = _save

        plan = await coord.async_evaluate()
        assert plan.apply_allowed is True
        assert "startup_lux_block" not in plan.blockers
        assert coord._startup_recovery.pending is False
        assert coord._startup_recovery.apply_count == 1
        assert len(scheduled) == 1

        await coord.async_evaluate()
        assert coord._startup_recovery.apply_count == 1
        assert len(scheduled) == 1

        await coord.async_apply_now()
        assert coord._startup_recovery.apply_count == 1
        assert len(scheduled) == 2

    asyncio.run(_run())
