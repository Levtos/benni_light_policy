"""Config- und Options-Flow für die Light-Policy (Single-Instance).

Mehrstufig & kategorisiert (statt einer „Wall of Entities"):
  1 Kontext · 2 Umwelt/Medien · 3 Signale · 4 Lampengruppen · 5 Bereiche
  · 6 Ring & Presets · 7 Optionen

Feld-Wording ist 1:1 an der Benni-Toolbox orientiert (Bio State, Activity State,
Day State, Presence Personal …). Entity-Selektoren sind bewusst NICHT gefiltert
(volle Flexibilität — Quellen dürfen auch von außerhalb der Toolbox kommen).

Der Options-Flow bietet ein Menü, um jede Kategorie einzeln nachzubearbeiten.
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ACTIVITY_STATE,
    CONF_APPLY_ENABLED,
    CONF_AWAKE_MINUTES,
    CONF_BATHROOM_LIGHT,
    CONF_BATHROOM_VIBRATION,
    CONF_BEDROOM_GROUP,
    CONF_BIO_STATE,
    CONF_CALENDAR_THEME,
    CONF_CROSSFADE_SECONDS,
    CONF_DAY_STATE,
    CONF_ENTERTAINMENT_STABLE,
    CONF_GROUP_ALL,
    CONF_GROUP_CEILING,
    CONF_GROUP_MAIN,
    CONF_GUEST,
    CONF_HALLWAY_LIGHT,
    CONF_HALLWAY_TRIGGERS,
    CONF_LUX,
    CONF_OVERNIGHT_AWAY,
    CONF_PRESENCE_HOUSEHOLD,
    CONF_PRESENCE_PERSONAL,
    CONF_PRESENCE_TRANSITION,
    CONF_PRESET_CATALOG,
    CONF_RING_TARGETS,
    CONF_SCENE_INTERVAL_SECONDS,
    CONF_SEASON,
    CONF_STARTUP_BLOCK_SECONDS,
    CONF_SYSTEM_READY,
    CONF_TITLE_CLASSIFIER,
    CONF_WEATHER,
    DEFAULT_APPLY_ENABLED,
    DEFAULT_CROSSFADE_SECONDS,
    DEFAULT_SCENE_INTERVAL_SECONDS,
    DEFAULT_STARTUP_BLOCK_SECONDS,
    DOMAIN,
)

# --- Selektoren (ungefiltert) ---
_ENTITY = selector.EntitySelector(selector.EntitySelectorConfig())
_ENTITIES = selector.EntitySelector(selector.EntitySelectorConfig(multiple=True))
_LIGHT = selector.EntitySelector(selector.EntitySelectorConfig(domain="light"))
_LIGHTS = selector.EntitySelector(selector.EntitySelectorConfig(domain="light", multiple=True))
_BOOL = selector.BooleanSelector()
_INT = vol.Coerce(int)

SELECTORS: dict[str, Any] = {
    CONF_BIO_STATE: _ENTITY, CONF_ACTIVITY_STATE: _ENTITY, CONF_DAY_STATE: _ENTITY,
    CONF_PRESENCE_PERSONAL: _ENTITY, CONF_PRESENCE_HOUSEHOLD: _ENTITY,
    CONF_LUX: _ENTITY, CONF_WEATHER: _ENTITY, CONF_SEASON: _ENTITY,
    CONF_CALENDAR_THEME: _ENTITY, CONF_ENTERTAINMENT_STABLE: _ENTITY,
    CONF_GUEST: _ENTITY, CONF_TITLE_CLASSIFIER: _ENTITY,
    CONF_PRESENCE_TRANSITION: _ENTITY, CONF_OVERNIGHT_AWAY: _ENTITY,
    CONF_SYSTEM_READY: _ENTITY, CONF_AWAKE_MINUTES: _ENTITY,
    CONF_GROUP_MAIN: _LIGHT, CONF_GROUP_CEILING: _LIGHT, CONF_GROUP_ALL: _LIGHT,
    CONF_HALLWAY_LIGHT: _LIGHT, CONF_BATHROOM_LIGHT: _LIGHT, CONF_BEDROOM_GROUP: _LIGHT,
    CONF_HALLWAY_TRIGGERS: _ENTITIES, CONF_BATHROOM_VIBRATION: _ENTITY,
    CONF_RING_TARGETS: _LIGHTS, CONF_PRESET_CATALOG: _ENTITY,
    CONF_APPLY_ENABLED: _BOOL,
    CONF_STARTUP_BLOCK_SECONDS: _INT, CONF_CROSSFADE_SECONDS: _INT,
    CONF_SCENE_INTERVAL_SECONDS: _INT,
}

INT_DEFAULTS: dict[str, int] = {
    CONF_STARTUP_BLOCK_SECONDS: DEFAULT_STARTUP_BLOCK_SECONDS,
    CONF_CROSSFADE_SECONDS: DEFAULT_CROSSFADE_SECONDS,
    CONF_SCENE_INTERVAL_SECONDS: DEFAULT_SCENE_INTERVAL_SECONDS,
}

# --- Kategorien / Schritte ---
STEP_CONTEXT = (CONF_BIO_STATE, CONF_ACTIVITY_STATE, CONF_DAY_STATE,
                CONF_PRESENCE_PERSONAL, CONF_PRESENCE_HOUSEHOLD)
STEP_ENVIRONMENT = (CONF_LUX, CONF_WEATHER, CONF_SEASON,
                    CONF_CALENDAR_THEME, CONF_ENTERTAINMENT_STABLE)
STEP_SIGNALS = (CONF_GUEST, CONF_TITLE_CLASSIFIER, CONF_PRESENCE_TRANSITION,
                CONF_OVERNIGHT_AWAY, CONF_SYSTEM_READY, CONF_AWAKE_MINUTES)
STEP_LAMPS = (CONF_GROUP_MAIN, CONF_GROUP_CEILING, CONF_GROUP_ALL)
STEP_AREAS = (CONF_HALLWAY_LIGHT, CONF_HALLWAY_TRIGGERS, CONF_BATHROOM_LIGHT,
              CONF_BATHROOM_VIBRATION, CONF_BEDROOM_GROUP)
STEP_RING_PRESETS = (CONF_RING_TARGETS, CONF_PRESET_CATALOG)
STEP_OPTIONS = (CONF_APPLY_ENABLED, CONF_STARTUP_BLOCK_SECONDS,
                CONF_CROSSFADE_SECONDS, CONF_SCENE_INTERVAL_SECONDS)

MENU_STEPS = ("context", "environment", "signals", "lamps", "areas",
              "ring_presets", "options")
STEP_KEYS: dict[str, tuple[str, ...]] = {
    "context": STEP_CONTEXT, "environment": STEP_ENVIRONMENT, "signals": STEP_SIGNALS,
    "lamps": STEP_LAMPS, "areas": STEP_AREAS, "ring_presets": STEP_RING_PRESETS,
    "options": STEP_OPTIONS,
}


def _schema(keys: tuple[str, ...], defaults: dict[str, Any]) -> vol.Schema:
    fields: dict[Any, Any] = {}
    for key in keys:
        sel = SELECTORS[key]
        if key in INT_DEFAULTS:
            marker = vol.Optional(key, default=defaults.get(key, INT_DEFAULTS[key]))
        elif key == CONF_APPLY_ENABLED:
            marker = vol.Optional(key, default=bool(defaults.get(key, DEFAULT_APPLY_ENABLED)))
        elif key in defaults and defaults[key] not in (None, ""):
            marker = vol.Optional(key, default=defaults[key])
        else:
            marker = vol.Optional(key)
        fields[marker] = sel
    return vol.Schema(fields)


class LightPolicyConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return await self.async_step_context()

    async def _step(self, step_id: str, next_step: str | None,
                    user_input: dict[str, Any] | None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            if next_step is None:
                return self.async_create_entry(title="Light Policy", data=self._data)
            return await getattr(self, f"async_step_{next_step}")()
        return self.async_show_form(
            step_id=step_id, data_schema=_schema(STEP_KEYS[step_id], self._data)
        )

    async def async_step_context(self, user_input=None):
        return await self._step("context", "environment", user_input)

    async def async_step_environment(self, user_input=None):
        return await self._step("environment", "signals", user_input)

    async def async_step_signals(self, user_input=None):
        return await self._step("signals", "lamps", user_input)

    async def async_step_lamps(self, user_input=None):
        return await self._step("lamps", "areas", user_input)

    async def async_step_areas(self, user_input=None):
        return await self._step("areas", "ring_presets", user_input)

    async def async_step_ring_presets(self, user_input=None):
        return await self._step("ring_presets", "options", user_input)

    async def async_step_options(self, user_input=None):
        return await self._step("options", None, user_input)

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return LightPolicyOptionsFlow(entry)


class LightPolicyOptionsFlow(OptionsFlow):
    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    def _defaults(self) -> dict[str, Any]:
        return {**self._entry.data, **self._entry.options}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        return self.async_show_menu(step_id="init", menu_options=list(MENU_STEPS))

    def _edit(self, step_id: str, user_input: dict[str, Any] | None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data={**self._entry.options, **user_input})
        return self.async_show_form(
            step_id=step_id, data_schema=_schema(STEP_KEYS[step_id], self._defaults())
        )

    async def async_step_context(self, user_input=None):
        return self._edit("context", user_input)

    async def async_step_environment(self, user_input=None):
        return self._edit("environment", user_input)

    async def async_step_signals(self, user_input=None):
        return self._edit("signals", user_input)

    async def async_step_lamps(self, user_input=None):
        return self._edit("lamps", user_input)

    async def async_step_areas(self, user_input=None):
        return self._edit("areas", user_input)

    async def async_step_ring_presets(self, user_input=None):
        return self._edit("ring_presets", user_input)

    async def async_step_options(self, user_input=None):
        return self._edit("options", user_input)
