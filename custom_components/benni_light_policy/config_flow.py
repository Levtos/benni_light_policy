"""Config-, Options- und Subentry-Flows für die Light-Policy.

Architektur: **Hub + typisierte Subentries**.
- Hub-Setup fragt die geteilten Foundation-Entities EINMAL ab (auto-vorausgefüllt
  aus der Toolbox), dazu Lampengruppen, Katalog und globale Optionen. Schlank,
  größtenteils nur bestätigen.
- Pro Anwendungsfall (Gaming, Musik, Notification-RGB, Flur, Bad, Schlafzimmer)
  ein **Subentry** mit NUR seinen eigenen 2–4 Feldern → keine „Wall of Entities".

Entity-Selektoren bewusst ungefiltert (volle Flexibilität).
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigSubentryFlow,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ACTIVITY_STATE,
    CONF_APPLY_ENABLED,
    CONF_BATHROOM_LIGHT,
    CONF_BATHROOM_TIMEOUT,
    CONF_BATHROOM_VIBRATION,
    CONF_BIO_STATE,
    CONF_CALENDAR_THEME,
    CONF_CLASSIFIER_ENTITY,
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
    CONF_PRESET_ENUM,
    CONF_REQUIRE_BIRTHDAY,
    CONF_RING_TARGETS,
    CONF_SCENE_INTERVAL_SECONDS,
    CONF_SEASON,
    CONF_STARTUP_BLOCK_SECONDS,
    CONF_SYSTEM_READY,
    CONF_MAPPINGS,
    CONF_MEDIA_CONTEXT,
    CONF_MEDIA_DEVICE,
    CONF_SOURCE_ID,
    CONF_SOURCE_PRIORITY,
    CONF_TRIGGER_VALUE,
    CONF_WAKE_UP_TARGETS,
    MAPPING_PRESET_PREFIX,
    MAPPING_SLOT_COUNT,
    MAPPING_VALUE_PREFIX,
    CONF_WEATHER,
    DEFAULT_APPLY_ENABLED,
    DEFAULT_CROSSFADE_SECONDS,
    DEFAULT_SCENE_INTERVAL_SECONDS,
    DEFAULT_STARTUP_BLOCK_SECONDS,
    DOMAIN,
    ENTITY_PREFILL,
    GROUP_PREFILL,
    SUBENTRY_PREFILL,
    SUBENTRY_BATHROOM,
    SUBENTRY_WAKE_UP,
    SUBENTRY_GAMING,
    SUBENTRY_HALLWAY,
    SUBENTRY_MUSIC,
    SUBENTRY_NOTIFICATION_RING,
)

# --- Selektoren (ungefiltert) ---
_ENTITY = selector.EntitySelector(selector.EntitySelectorConfig())
_ENTITIES = selector.EntitySelector(selector.EntitySelectorConfig(multiple=True))
_LIGHT = selector.EntitySelector(selector.EntitySelectorConfig(domain="light"))
_LIGHTS = selector.EntitySelector(selector.EntitySelectorConfig(domain="light", multiple=True))
# Bad-Licht ist nicht immer ein light.* — z.B. Shelly Switch.
_LIGHT_OR_SWITCH = selector.EntitySelector(
    selector.EntitySelectorConfig(domain=["light", "switch"])
)
_BOOL = selector.BooleanSelector()
_TEXT = selector.TextSelector(selector.TextSelectorConfig())
_INT = vol.Coerce(int)

SELECTORS: dict[str, Any] = {
    # Hub-Foundation
    CONF_BIO_STATE: _ENTITY, CONF_ACTIVITY_STATE: _ENTITY, CONF_DAY_STATE: _ENTITY,
    CONF_PRESENCE_PERSONAL: _ENTITY, CONF_PRESENCE_HOUSEHOLD: _ENTITY,
    CONF_LUX: _ENTITY, CONF_WEATHER: _ENTITY, CONF_SEASON: _ENTITY,
    CONF_CALENDAR_THEME: _ENTITY, CONF_ENTERTAINMENT_STABLE: _ENTITY,
    CONF_MEDIA_DEVICE: _ENTITY, CONF_MEDIA_CONTEXT: _ENTITY,
    CONF_GUEST: _ENTITY, CONF_PRESENCE_TRANSITION: _ENTITY,
    CONF_OVERNIGHT_AWAY: _ENTITY, CONF_SYSTEM_READY: _ENTITY,
    CONF_GROUP_MAIN: _LIGHTS, CONF_GROUP_CEILING: _LIGHTS, CONF_GROUP_ALL: _LIGHTS,
    CONF_PRESET_CATALOG: _ENTITY,
    CONF_APPLY_ENABLED: _BOOL, CONF_STARTUP_BLOCK_SECONDS: _INT,
    CONF_CROSSFADE_SECONDS: _INT, CONF_SCENE_INTERVAL_SECONDS: _INT,
    # Subentry-Felder (Minihub-Schema)
    CONF_CLASSIFIER_ENTITY: _ENTITY,
    CONF_SOURCE_ID: _TEXT, CONF_SOURCE_PRIORITY: _INT,
    CONF_TRIGGER_VALUE: _TEXT, CONF_PRESET_ENUM: _TEXT,
    CONF_REQUIRE_BIRTHDAY: _BOOL, CONF_RING_TARGETS: _LIGHTS,
    CONF_HALLWAY_LIGHT: _LIGHT, CONF_HALLWAY_TRIGGERS: _ENTITIES,
    CONF_BATHROOM_LIGHT: _LIGHT_OR_SWITCH, CONF_BATHROOM_VIBRATION: _ENTITY, CONF_BATHROOM_TIMEOUT: _INT,
    CONF_WAKE_UP_TARGETS: _LIGHTS,
}

INT_DEFAULTS: dict[str, int] = {
    CONF_STARTUP_BLOCK_SECONDS: DEFAULT_STARTUP_BLOCK_SECONDS,
    CONF_CROSSFADE_SECONDS: DEFAULT_CROSSFADE_SECONDS,
    CONF_SCENE_INTERVAL_SECONDS: DEFAULT_SCENE_INTERVAL_SECONDS,
    CONF_BATHROOM_TIMEOUT: 3600,
}
BOOL_KEYS = {CONF_APPLY_ENABLED, CONF_REQUIRE_BIRTHDAY}

# --- Hub-Schritte ---
STEP_CONTEXT = (CONF_BIO_STATE, CONF_ACTIVITY_STATE, CONF_DAY_STATE,
                CONF_PRESENCE_PERSONAL, CONF_PRESENCE_HOUSEHOLD)
STEP_ENVIRONMENT = (CONF_LUX, CONF_WEATHER, CONF_SEASON,
                    CONF_CALENDAR_THEME, CONF_ENTERTAINMENT_STABLE,
                    CONF_MEDIA_DEVICE, CONF_MEDIA_CONTEXT)
STEP_SIGNALS = (CONF_GUEST, CONF_PRESENCE_TRANSITION, CONF_OVERNIGHT_AWAY, CONF_SYSTEM_READY)
STEP_LAMPS = (CONF_GROUP_MAIN, CONF_GROUP_CEILING, CONF_GROUP_ALL, CONF_PRESET_CATALOG)
STEP_OPTIONS = (CONF_APPLY_ENABLED, CONF_STARTUP_BLOCK_SECONDS,
                CONF_CROSSFADE_SECONDS, CONF_SCENE_INTERVAL_SECONDS)

HUB_MENU = ("context", "environment", "signals", "lamps", "options")
HUB_STEP_KEYS: dict[str, tuple[str, ...]] = {
    "context": STEP_CONTEXT, "environment": STEP_ENVIRONMENT, "signals": STEP_SIGNALS,
    "lamps": STEP_LAMPS, "options": STEP_OPTIONS,
}

# --- Subentry-Felder pro Typ ---
SUBENTRY_FIELDS: dict[str, tuple[str, ...]] = {
    # Minihubs (haben zusätzlich Mapping-Slots — siehe SUBENTRY_HAS_MAPPINGS)
    SUBENTRY_GAMING: (CONF_SOURCE_ID, CONF_SOURCE_PRIORITY, CONF_CLASSIFIER_ENTITY),
    SUBENTRY_MUSIC: (CONF_CLASSIFIER_ENTITY, CONF_REQUIRE_BIRTHDAY),
    SUBENTRY_NOTIFICATION_RING: (CONF_RING_TARGETS, CONF_ACTIVITY_STATE),
    # Single-Rule
    SUBENTRY_HALLWAY: (CONF_HALLWAY_LIGHT, CONF_HALLWAY_TRIGGERS),
    SUBENTRY_BATHROOM: (CONF_BATHROOM_LIGHT, CONF_BATHROOM_VIBRATION, CONF_BATHROOM_TIMEOUT),
    SUBENTRY_WAKE_UP: (CONF_WAKE_UP_TARGETS,),
}
# Subentry-Typen mit interner Mapping-Tabelle (classifier/activity → preset/effect).
SUBENTRY_HAS_MAPPINGS: frozenset[str] = frozenset({
    SUBENTRY_GAMING, SUBENTRY_MUSIC, SUBENTRY_NOTIFICATION_RING,
})
SUBENTRY_DEFAULT_TITLE: dict[str, str] = {
    SUBENTRY_GAMING: "Gaming", SUBENTRY_MUSIC: "Musik-Party",
    SUBENTRY_NOTIFICATION_RING: "Notification RGB", SUBENTRY_HALLWAY: "Flur",
    SUBENTRY_BATHROOM: "Bad", SUBENTRY_WAKE_UP: "Wake-Up",
}
SUBENTRY_PRESET_DEFAULT: dict[str, str] = {}


def _marker(key: str, defaults: dict[str, Any]):
    if key in INT_DEFAULTS:
        return vol.Optional(key, default=defaults.get(key, INT_DEFAULTS[key]))
    if key in BOOL_KEYS:
        fallback = DEFAULT_APPLY_ENABLED if key == CONF_APPLY_ENABLED else True
        return vol.Optional(key, default=bool(defaults.get(key, fallback)))
    if key in defaults and defaults[key] not in (None, ""):
        return vol.Optional(key, default=defaults[key])
    return vol.Optional(key)


def _schema(keys: tuple[str, ...], defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema({_marker(k, defaults): SELECTORS[k] for k in keys})


def _exists(hass, eid: str) -> bool:
    return bool(eid) and hass.states.get(eid) is not None


def _prefilled(keys: tuple[str, ...], data: dict[str, Any], hass) -> dict[str, Any]:
    """Hub-Defaults inkl. Auto-Prefill (Einzelwerte + Lampengruppen-Listen) —
    jeweils NUR wenn die Entity(en) in HA existieren."""
    defaults = dict(data)
    for key in keys:
        if key in defaults:
            continue
        single = ENTITY_PREFILL.get(key)
        if single and _exists(hass, single):
            defaults[key] = single
            continue
        group = GROUP_PREFILL.get(key)
        if group:
            present = [e for e in group if _exists(hass, e)]
            if present:
                defaults[key] = present
    return defaults


# --------------------------------------------------------------------------- #
# Hub Config-Flow
# --------------------------------------------------------------------------- #
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
        keys = HUB_STEP_KEYS[step_id]
        if user_input is not None:
            self._data.update(user_input)
            if next_step is None:
                return self.async_create_entry(title="Light Policy", data=self._data)
            return await getattr(self, f"async_step_{next_step}")()
        return self.async_show_form(
            step_id=step_id, data_schema=_schema(keys, _prefilled(keys, self._data, self.hass))
        )

    async def async_step_context(self, user_input=None):
        return await self._step("context", "environment", user_input)

    async def async_step_environment(self, user_input=None):
        return await self._step("environment", "signals", user_input)

    async def async_step_signals(self, user_input=None):
        return await self._step("signals", "lamps", user_input)

    async def async_step_lamps(self, user_input=None):
        return await self._step("lamps", "options", user_input)

    async def async_step_options(self, user_input=None):
        return await self._step("options", None, user_input)

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return LightPolicyOptionsFlow(entry)

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {
            SUBENTRY_GAMING: GamingSubentryFlow,
            SUBENTRY_MUSIC: MusicSubentryFlow,
            SUBENTRY_NOTIFICATION_RING: NotificationRingSubentryFlow,
            SUBENTRY_HALLWAY: HallwaySubentryFlow,
            SUBENTRY_BATHROOM: BathroomSubentryFlow,
            SUBENTRY_WAKE_UP: WakeUpSubentryFlow,
        }


# --------------------------------------------------------------------------- #
# Options-Flow (Hub-Kategorien als Menü)
# --------------------------------------------------------------------------- #
class LightPolicyOptionsFlow(OptionsFlow):
    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    def _defaults(self) -> dict[str, Any]:
        return {**self._entry.data, **self._entry.options}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        return self.async_show_menu(step_id="init", menu_options=list(HUB_MENU))

    def _edit(self, step_id: str, user_input: dict[str, Any] | None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data={**self._entry.options, **user_input})
        keys = HUB_STEP_KEYS[step_id]
        return self.async_show_form(step_id=step_id, data_schema=_schema(keys, self._defaults()))

    async def async_step_context(self, user_input=None):
        return self._edit("context", user_input)

    async def async_step_environment(self, user_input=None):
        return self._edit("environment", user_input)

    async def async_step_signals(self, user_input=None):
        return self._edit("signals", user_input)

    async def async_step_lamps(self, user_input=None):
        return self._edit("lamps", user_input)

    async def async_step_options(self, user_input=None):
        return self._edit("options", user_input)


# --------------------------------------------------------------------------- #
# Subentry-Flows — pro Typ eine kleine Klasse (Typ als eigenes Klassen-Attribut,
# kein Verlass auf HA-interne Typ-Attribute). v1: nur Anlegen; zum Ändern
# Subentry löschen + neu anlegen (Reconfigure folgt später).
# --------------------------------------------------------------------------- #
def _slot_keys(i: int) -> tuple[str, str]:
    return f"{MAPPING_VALUE_PREFIX}{i}", f"{MAPPING_PRESET_PREFIX}{i}"


def _pack_mappings(user_input: dict[str, Any]) -> dict[str, str]:
    """Zieht die N (value/preset)-Slot-Paare aus dem Form-Input und packt sie
    in ein {classifier_value: preset_uuid}-Dict. Leere Slots werden ignoriert.
    Entfernt die Slot-Keys aus user_input (in-place)."""
    packed: dict[str, str] = {}
    for i in range(MAPPING_SLOT_COUNT):
        vkey, pkey = _slot_keys(i)
        v = user_input.pop(vkey, None)
        p = user_input.pop(pkey, None)
        if v in (None, "") or p in (None, ""):
            continue
        packed[str(v).strip()] = str(p).strip()
    return packed


def _unpack_mappings(defaults: dict[str, Any]) -> None:
    """Spielt ein vorhandenes mappings-Dict aus defaults in die Slot-Felder
    zurück (für Reconfigure/Edit)."""
    mappings = defaults.get(CONF_MAPPINGS) or {}
    if not isinstance(mappings, dict):
        return
    items = list(mappings.items())[:MAPPING_SLOT_COUNT]
    for i, (v, p) in enumerate(items):
        vkey, pkey = _slot_keys(i)
        defaults.setdefault(vkey, v)
        defaults.setdefault(pkey, p)


class _BasePolicySubentryFlow(ConfigSubentryFlow):
    policy_type: str = ""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        stype = self.policy_type
        if user_input is not None:
            title = user_input.pop("name", None) or SUBENTRY_DEFAULT_TITLE.get(stype, stype)
            if stype in SUBENTRY_HAS_MAPPINGS:
                user_input[CONF_MAPPINGS] = _pack_mappings(user_input)
            return self.async_create_entry(title=title, data=user_input)

        defaults: dict[str, Any] = {}
        if stype in SUBENTRY_PRESET_DEFAULT:
            defaults[CONF_PRESET_ENUM] = SUBENTRY_PRESET_DEFAULT[stype]
        # Auto-Prefill eindeutiger Subentry-Felder (z.B. Awake-Dauer), wenn vorhanden.
        for key in SUBENTRY_FIELDS[stype]:
            cand = SUBENTRY_PREFILL.get(key)
            if cand and key not in defaults and _exists(self.hass, cand):
                defaults[key] = cand
        if stype in SUBENTRY_HAS_MAPPINGS:
            _unpack_mappings(defaults)
        fields: dict[Any, Any] = {
            vol.Optional("name", default=SUBENTRY_DEFAULT_TITLE.get(stype, stype)): _TEXT
        }
        for key in SUBENTRY_FIELDS[stype]:
            fields[_marker(key, defaults)] = SELECTORS[key]
        if stype in SUBENTRY_HAS_MAPPINGS:
            for i in range(MAPPING_SLOT_COUNT):
                vkey, pkey = _slot_keys(i)
                fields[_marker(vkey, defaults)] = _TEXT
                fields[_marker(pkey, defaults)] = _TEXT
        return self.async_show_form(step_id="user", data_schema=vol.Schema(fields))


class GamingSubentryFlow(_BasePolicySubentryFlow):
    policy_type = SUBENTRY_GAMING


class MusicSubentryFlow(_BasePolicySubentryFlow):
    policy_type = SUBENTRY_MUSIC


class NotificationRingSubentryFlow(_BasePolicySubentryFlow):
    policy_type = SUBENTRY_NOTIFICATION_RING


class HallwaySubentryFlow(_BasePolicySubentryFlow):
    policy_type = SUBENTRY_HALLWAY


class BathroomSubentryFlow(_BasePolicySubentryFlow):
    policy_type = SUBENTRY_BATHROOM


class WakeUpSubentryFlow(_BasePolicySubentryFlow):
    policy_type = SUBENTRY_WAKE_UP
