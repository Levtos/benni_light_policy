"""WebSocket-API für das Light-Policy-Panel.

Liefert dem Frontend einen konsolidierten Status-Snapshot (Plan, Gates, Bereiche,
Spezialregeln) und verwaltet die zentrale Look-Map (policy_key -> Look-Ref).

Bewusste Trennung: die echten Looks (Slug+Name) holt das Panel direkt über
`benni_scene_presets/list_looks`; hier wird NICHT die scene_presets-Storage kopiert.
Coverage rechnet das Frontend aus (Soll-Keys von hier × vorhandene Looks von dort).
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ACTIVITY_STATE,
    CONF_BIO_STATE,
    CONF_CALENDAR_THEME,
    CONF_CLASSIFIER_ENTITY,
    CONF_DAY_STATE,
    CONF_ENTERTAINMENT_STABLE,
    CONF_LUX,
    CONF_MAPPINGS,
    CONF_MEDIA_CONTEXT,
    CONF_MEDIA_DEVICE,
    CONF_OVERNIGHT_AWAY,
    CONF_PRESENCE_HOUSEHOLD,
    CONF_PRESENCE_PERSONAL,
    CONF_PRESENCE_TRANSITION,
    CONF_SEASON,
    CONF_SOURCE_ID,
    CONF_SYSTEM_READY,
    CONF_WEATHER,
    DATA_COORDINATOR,
    DAY_PHASES,
    DOMAIN,
    POLICY_FIXED_MODES,
    POLICY_THEMES,
    SUBENTRY_GAMING,
    SUBENTRY_MUSIC,
    SUBENTRY_NOTIFICATION_RING,
    WS_GET_LOOK_MAP,
    WS_GET_STATUS,
    WS_SET_APPLY_ENABLED,
    WS_SET_BRIGHTNESS_PROFILE,
    WS_SET_CUSTOM_THEMES,
    WS_SET_LOOK_MAP,
    WS_SET_SUBENTRY_MAPPINGS,
)

# Foundation-Quell-Entities, deren Verfügbarkeit den "System bereit"-Status speist.
FOUNDATION_KEYS: tuple[str, ...] = (
    CONF_BIO_STATE, CONF_DAY_STATE, CONF_ACTIVITY_STATE,
    CONF_PRESENCE_PERSONAL, CONF_PRESENCE_HOUSEHOLD, CONF_PRESENCE_TRANSITION,
    CONF_LUX, CONF_WEATHER, CONF_SEASON, CONF_CALENDAR_THEME,
    CONF_ENTERTAINMENT_STABLE, CONF_MEDIA_DEVICE, CONF_MEDIA_CONTEXT,
    CONF_OVERNIGHT_AWAY, CONF_SYSTEM_READY,
)

# Subentry-Typen mit classifier_value -> Look-Ref-Mapping (Spezialregeln-Tab).
MAPPING_SUBENTRY_TYPES = (SUBENTRY_GAMING, SUBENTRY_MUSIC, SUBENTRY_NOTIFICATION_RING)


def _coordinator(hass: HomeAssistant):
    bucket = hass.data.get(DOMAIN) or {}
    for entry_bucket in bucket.values():
        # hass.data[DOMAIN] enthält neben den Entry-Buckets (dict) auch Setup-Flags
        # (bool) — nur echte Entry-Buckets betrachten.
        if not isinstance(entry_bucket, dict):
            continue
        coord = entry_bucket.get(DATA_COORDINATOR)
        if coord is not None:
            return coord
    return None


def matrix_keys(themes: list[str] | tuple[str, ...] | None = None) -> list[str]:
    """Alle Tagesphasen-Matrix-Keys (theme_phase)."""
    return [f"{theme}_{phase}" for theme in (themes or POLICY_THEMES) for phase in DAY_PHASES]


def _entity_ready(hass: HomeAssistant, eid: str | None) -> bool:
    if not eid:
        return False
    st = hass.states.get(eid)
    return st is not None and st.state not in ("unknown", "unavailable")


def _foundation_summary(hass: HomeAssistant, coord) -> dict[str, Any]:
    total = 0
    ok = 0
    missing: list[str] = []
    for key in FOUNDATION_KEYS:
        eid = coord.get_option(key)
        if not eid:
            continue
        total += 1
        if _entity_ready(hass, eid):
            ok += 1
        else:
            missing.append(eid)
    return {"ok": ok, "total": total, "missing": missing}


def _subentry_rules(coord) -> list[dict[str, Any]]:
    """Gaming/Musik/Ring-Subentries mit ihren classifier_value -> Look-Ref-Mappings."""
    out: list[dict[str, Any]] = []
    for sub in coord.entry.subentries.values():
        if sub.subentry_type not in MAPPING_SUBENTRY_TYPES:
            continue
        d = sub.data
        out.append({
            "subentry_id": sub.subentry_id,
            "type": sub.subentry_type,
            "title": sub.title,
            "source_id": d.get(CONF_SOURCE_ID),
            "classifier_entity": d.get(CONF_CLASSIFIER_ENTITY),
            "mappings": dict(d.get(CONF_MAPPINGS) or {}),
        })
    return out


def _area_rules(coord) -> list[dict[str, Any]]:
    """Bereiche/Sonderwege (Wake-Up, Flur, Bad, Ring) — nur zur Anzeige."""
    out: list[dict[str, Any]] = []
    for sub in coord.entry.subentries.values():
        out.append({
            "subentry_id": sub.subentry_id,
            "type": sub.subentry_type,
            "title": sub.title,
            # Welche Felder relevant sind, entscheidet das Frontend je Typ.
            "data": {k: v for k, v in sub.data.items() if k != CONF_MAPPINGS},
            "via_look": sub.subentry_type in MAPPING_SUBENTRY_TYPES,
        })
    return out


def _status(hass: HomeAssistant, coord) -> dict[str, Any]:
    plan = coord.last_plan
    plan_dict = plan.as_dict() if plan else {}
    gate = coord.gate_internals()
    desired_key = plan_dict.get("preset_enum")
    return {
        "version": getattr(coord, "version", None),
        "plan": plan_dict,
        "gate": gate,
        "apply_enabled": coord.apply_enabled,
        "manual_off": coord.manual_off_active,
        "ring_mode": coord.ring_mode,
        "bedtime_active": getattr(coord, "bedtime_signal_active", False),
        "activity": coord.current_activity(),
        "day_state": coord.current_day_state(),
        # gewünschter Policy-Key + aufgelöster echter Look-Ref (für Coverage/Anzeige).
        "desired_policy_key": desired_key,
        "desired_look_ref": coord.resolve_look_ref(desired_key),
        "foundation": _foundation_summary(hass, coord),
        "subentry_rules": _subentry_rules(coord),
        "areas": _area_rules(coord),
        "brightness_profile": {
            **coord.brightness_profile(),
        },
    }


def _catalog(coord) -> dict[str, Any]:
    """Soll-Keys, die einen Look brauchen, + aktuelle Look-Map."""
    themes = [*POLICY_THEMES, *coord.custom_themes]
    return {
        "look_map": coord.look_map,
        "fixed_modes": list(POLICY_FIXED_MODES),
        "themes": themes,
        "custom_themes": list(coord.custom_themes),
        "phases": list(DAY_PHASES),
        "matrix_keys": matrix_keys(themes),
        "subentry_rules": _subentry_rules(coord),
    }


def async_setup_websocket_api(hass: HomeAssistant) -> None:
    @websocket_api.websocket_command({vol.Required("type"): WS_GET_STATUS})
    @websocket_api.async_response
    async def ws_get_status(hass, connection, msg) -> None:
        coord = _coordinator(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_ready", "Light Policy not loaded")
            return
        connection.send_result(msg["id"], _status(hass, coord))

    @websocket_api.websocket_command({vol.Required("type"): WS_GET_LOOK_MAP})
    @websocket_api.async_response
    async def ws_get_look_map(hass, connection, msg) -> None:
        coord = _coordinator(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_ready", "Light Policy not loaded")
            return
        connection.send_result(msg["id"], _catalog(coord))

    @websocket_api.websocket_command({
        vol.Required("type"): WS_SET_LOOK_MAP,
        vol.Required("look_map"): {str: vol.Any(str, None)},
    })
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_set_look_map(hass, connection, msg) -> None:
        coord = _coordinator(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_ready", "Light Policy not loaded")
            return
        cleaned = await coord.async_set_look_map(msg["look_map"])
        connection.send_result(msg["id"], {"look_map": cleaned})

    @websocket_api.websocket_command({
        vol.Required("type"): WS_SET_SUBENTRY_MAPPINGS,
        vol.Required("subentry_id"): str,
        vol.Required("mappings"): {str: vol.Any(str, None)},
    })
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_set_subentry_mappings(hass, connection, msg) -> None:
        coord = _coordinator(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_ready", "Light Policy not loaded")
            return
        try:
            cleaned = await coord.async_set_subentry_mappings(
                msg["subentry_id"], msg["mappings"]
            )
        except ValueError as err:
            connection.send_error(msg["id"], "invalid_subentry", str(err))
            return
        connection.send_result(msg["id"], {"mappings": cleaned})

    @websocket_api.websocket_command({
        vol.Required("type"): WS_SET_APPLY_ENABLED,
        vol.Required("enabled"): bool,
    })
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_set_apply_enabled(hass, connection, msg) -> None:
        coord = _coordinator(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_ready", "Light Policy not loaded")
            return
        await coord.async_set_apply_enabled(msg["enabled"])
        connection.send_result(msg["id"], {"apply_enabled": msg["enabled"]})

    @websocket_api.websocket_command({
        vol.Required("type"): WS_SET_BRIGHTNESS_PROFILE,
        vol.Required("brightness_profile"): {str: vol.Any(int, str, None)},
    })
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_set_brightness_profile(hass, connection, msg) -> None:
        coord = _coordinator(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_ready", "Light Policy not loaded")
            return
        cleaned = await coord.async_set_brightness_profile(msg["brightness_profile"])
        connection.send_result(msg["id"], {"brightness_profile": cleaned})

    @websocket_api.websocket_command({
        vol.Required("type"): WS_SET_CUSTOM_THEMES,
        vol.Required("custom_themes"): [str],
    })
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_set_custom_themes(hass, connection, msg) -> None:
        coord = _coordinator(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_ready", "Light Policy not loaded")
            return
        cleaned = await coord.async_set_custom_themes(msg["custom_themes"])
        connection.send_result(msg["id"], {"custom_themes": list(cleaned)})

    websocket_api.async_register_command(hass, ws_get_status)
    websocket_api.async_register_command(hass, ws_get_look_map)
    websocket_api.async_register_command(hass, ws_set_look_map)
    websocket_api.async_register_command(hass, ws_set_subentry_mappings)
    websocket_api.async_register_command(hass, ws_set_apply_enabled)
    websocket_api.async_register_command(hass, ws_set_brightness_profile)
    websocket_api.async_register_command(hass, ws_set_custom_themes)
