"""Benni Light Policy — erstes Aggregat-Modul (eigene HACS-Integration).

Single-Instance: ein Config-Entry verwaltet das Wohnzimmer (weitere Bereiche
iterativ). Decision/Apply-Pattern wie cover_policy, aber standalone-Domain.
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    DATA_COORDINATOR,
    DATA_SKIP_RELOAD_COUNT,
    DOMAIN,
    SERVICE_APPLY_NOW,
    SERVICE_CLEAR_MANUAL_OFF,
    SERVICE_SET_MANUAL_OFF,
)
from .coordinator import LightPolicyCoordinator
from .view import async_remove_view, async_setup_view
from .websocket_api import async_setup_websocket_api

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH]
_WS_FLAG = "_ws_registered"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coord = LightPolicyCoordinator(hass, entry)
    await coord.async_load()
    coord.async_start()
    await coord.async_evaluate()

    data = hass.data.setdefault(DOMAIN, {})
    data[entry.entry_id] = {DATA_COORDINATOR: coord}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_register_services(hass)

    # Panel + WebSocket-API (Dashboard-Frontend). WS einmalig pro HA-Prozess.
    await async_setup_view(hass)
    if not data.get(_WS_FLAG):
        async_setup_websocket_api(hass)
        data[_WS_FLAG] = True

    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    data = hass.data.setdefault(DOMAIN, {})
    skip_count = int(data.get(DATA_SKIP_RELOAD_COUNT) or 0)
    if skip_count > 0:
        data[DATA_SKIP_RELOAD_COUNT] = skip_count - 1
        return
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        bucket = hass.data[DOMAIN].pop(entry.entry_id, None)
        if bucket:
            bucket[DATA_COORDINATOR].async_stop()
        # Kein Coordinator mehr → Panel + Services entfernen.
        if not any(DATA_COORDINATOR in b for b in hass.data[DOMAIN].values() if isinstance(b, dict)):
            async_remove_view(hass)
            for svc in (SERVICE_APPLY_NOW, SERVICE_SET_MANUAL_OFF, SERVICE_CLEAR_MANUAL_OFF):
                hass.services.async_remove(DOMAIN, svc)
    return unloaded


def _coordinators(hass: HomeAssistant) -> list[LightPolicyCoordinator]:
    # hass.data[DOMAIN] enthält neben Entry-Buckets (dict) auch Setup-Flags (bool).
    return [
        b[DATA_COORDINATOR]
        for b in hass.data.get(DOMAIN, {}).values()
        if isinstance(b, dict) and DATA_COORDINATOR in b
    ]


def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_APPLY_NOW):
        return

    async def _apply_now(_call: ServiceCall) -> None:
        for coord in _coordinators(hass):
            await coord.async_apply_now()

    async def _set_manual_off(_call: ServiceCall) -> None:
        for coord in _coordinators(hass):
            await coord.async_set_manual_off()

    async def _clear_manual_off(_call: ServiceCall) -> None:
        for coord in _coordinators(hass):
            await coord.async_clear_manual_off()

    hass.services.async_register(DOMAIN, SERVICE_APPLY_NOW, _apply_now)
    hass.services.async_register(DOMAIN, SERVICE_SET_MANUAL_OFF, _set_manual_off)
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_MANUAL_OFF, _clear_manual_off)
