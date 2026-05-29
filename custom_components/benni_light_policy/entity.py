"""Gemeinsame Entity-Basis: abonniert den Coordinator und teilt das Device."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback

from .const import DOMAIN
from .coordinator import LightPolicyCoordinator


def device_info(entry: ConfigEntry) -> dict[str, Any]:
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": "Light Policy",
        "manufacturer": "Benni",
        "model": "Light Policy (Aggregat)",
    }


class LightPolicyEntity:
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, coord: LightPolicyCoordinator, entry: ConfigEntry) -> None:
        self.coord = coord
        self._entry = entry
        self._attr_device_info = device_info(entry)

    async def async_added_to_hass(self) -> None:
        self.coord.add_listener(self._sched_update)

    async def async_will_remove_from_hass(self) -> None:
        self.coord.remove_listener(self._sched_update)

    @callback
    def _sched_update(self) -> None:
        self.async_write_ha_state()  # type: ignore[attr-defined]
