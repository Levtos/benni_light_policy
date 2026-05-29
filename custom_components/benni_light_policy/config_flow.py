"""Config- und Options-Flow für die Light-Policy (Single-Instance)."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ACTIVITY_STATE,
    CONF_APPLY_ENABLED,
    CONF_AWAKE_MINUTES,
    CONF_BATHROOM_LIGHT,
    CONF_BATHROOM_VIBRATION,
    CONF_BEDROOM_GROUP,
    CONF_BIO_STATE,
    CONF_HALLWAY_LIGHT,
    CONF_HALLWAY_TRIGGERS,
    CONF_RING_TARGET,
    CONF_CALENDAR_THEME,
    CONF_CROSSFADE_SECONDS,
    CONF_DAY_STATE,
    CONF_ENTERTAINMENT_STABLE,
    CONF_GROUP_ALL,
    CONF_GROUP_CEILING,
    CONF_GROUP_MAIN,
    CONF_GUEST,
    CONF_LUX,
    CONF_OVERNIGHT_AWAY,
    CONF_PRESENCE_HOUSEHOLD,
    CONF_PRESENCE_PERSONAL,
    CONF_PRESENCE_TRANSITION,
    CONF_PRESET_CATALOG,
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

_ENTITY = selector.EntitySelector(selector.EntitySelectorConfig())
_LIGHT = selector.EntitySelector(selector.EntitySelectorConfig(domain="light"))
_ENTITIES = selector.EntitySelector(selector.EntitySelectorConfig(multiple=True))

# Quell-Inputs (Entities). day_state ist faktisch das wichtigste Gate.
SOURCE_KEYS = (
    CONF_BIO_STATE, CONF_DAY_STATE, CONF_ACTIVITY_STATE, CONF_LUX,
    CONF_PRESENCE_PERSONAL, CONF_PRESENCE_HOUSEHOLD, CONF_GUEST,
    CONF_SEASON, CONF_CALENDAR_THEME, CONF_TITLE_CLASSIFIER,
    CONF_ENTERTAINMENT_STABLE, CONF_OVERNIGHT_AWAY, CONF_SYSTEM_READY,
    CONF_WEATHER, CONF_PRESENCE_TRANSITION, CONF_PRESET_CATALOG,
)
LIGHT_GROUP_KEYS = (
    CONF_GROUP_MAIN, CONF_GROUP_CEILING, CONF_GROUP_ALL,
    CONF_HALLWAY_LIGHT, CONF_BATHROOM_LIGHT, CONF_BEDROOM_GROUP,
)
# Bereichs-Quell-Entities (keine Lights).
AREA_SOURCE_KEYS = (CONF_BATHROOM_VIBRATION, CONF_AWAKE_MINUTES, CONF_RING_TARGET)


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    fields: dict[Any, Any] = {}
    for key in SOURCE_KEYS:
        marker = vol.Optional(key, default=defaults[key]) if key in defaults else vol.Optional(key)
        fields[marker] = _ENTITY
    for key in LIGHT_GROUP_KEYS:
        marker = vol.Optional(key, default=defaults[key]) if key in defaults else vol.Optional(key)
        fields[marker] = _LIGHT
    for key in AREA_SOURCE_KEYS:
        marker = vol.Optional(key, default=defaults[key]) if key in defaults else vol.Optional(key)
        fields[marker] = _ENTITY
    hw_marker = (
        vol.Optional(CONF_HALLWAY_TRIGGERS, default=defaults[CONF_HALLWAY_TRIGGERS])
        if CONF_HALLWAY_TRIGGERS in defaults else vol.Optional(CONF_HALLWAY_TRIGGERS)
    )
    fields[hw_marker] = _ENTITIES
    fields[vol.Optional(CONF_APPLY_ENABLED, default=defaults.get(CONF_APPLY_ENABLED, DEFAULT_APPLY_ENABLED))] = selector.BooleanSelector()
    fields[vol.Optional(CONF_STARTUP_BLOCK_SECONDS, default=defaults.get(CONF_STARTUP_BLOCK_SECONDS, DEFAULT_STARTUP_BLOCK_SECONDS))] = vol.Coerce(int)
    fields[vol.Optional(CONF_CROSSFADE_SECONDS, default=defaults.get(CONF_CROSSFADE_SECONDS, DEFAULT_CROSSFADE_SECONDS))] = vol.Coerce(int)
    fields[vol.Optional(CONF_SCENE_INTERVAL_SECONDS, default=defaults.get(CONF_SCENE_INTERVAL_SECONDS, DEFAULT_SCENE_INTERVAL_SECONDS))] = vol.Coerce(int)
    return vol.Schema(fields)


class LightPolicyConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            return self.async_create_entry(title="Light Policy", data=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return LightPolicyOptionsFlow(entry)


class LightPolicyOptionsFlow(OptionsFlow):
    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        defaults = {**self._entry.data, **self._entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(defaults))
