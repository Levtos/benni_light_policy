"""Switch-Plattform: Manual-Off-Hold (R9).

Ein vom User toggle-barer Boolean (z.B. per Switch Manager auf eine Taste gelegt).
ON  = Hold aktiv → kein Ein/Aus-Apply (Plan wird weiter berechnet, aber apply_blocked).
OFF = frei.
Auto-Reset bei Bio-Übergang sleep→awake (R9). Über Neustart persistiert.
"""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DATA_COORDINATOR,
    DOMAIN,
    UID_APPLY_ENABLED,
    UID_MANUAL_OFF,
    unique_id,
)
from .entity import LightPolicyEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([ManualOffSwitch(coord, entry), ApplyEnabledSwitch(coord, entry)])


class ManualOffSwitch(LightPolicyEntity, SwitchEntity):
    _attr_icon = "mdi:lightbulb-off"

    def __init__(self, coord, entry):
        super().__init__(coord, entry)
        self._attr_unique_id = unique_id(UID_MANUAL_OFF)
        self._attr_name = "Manual Off (Living Room)"
        self._attr_suggested_object_id = "lights_manual_off_living_room"

    @property
    def is_on(self) -> bool:
        return bool(self.coord.manual_off_active)

    async def async_turn_on(self, **kwargs) -> None:
        await self.coord.async_set_manual_off()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coord.async_clear_manual_off()


class ApplyEnabledSwitch(LightPolicyEntity, SwitchEntity):
    """Apply scharf/aus zur Laufzeit (statt Options-Flow). OFF = Shadow-Mode.

    Schreibt in die Config-Entry-Options und lädt den Entry neu.
    """

    _attr_icon = "mdi:flash"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coord, entry):
        super().__init__(coord, entry)
        self._attr_unique_id = unique_id(UID_APPLY_ENABLED)
        self._attr_name = "Apply Enabled"
        self._attr_suggested_object_id = "lights_apply_enabled"

    @property
    def is_on(self) -> bool:
        return bool(self.coord.apply_enabled)

    async def async_turn_on(self, **kwargs) -> None:
        await self.coord.async_set_apply_enabled(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coord.async_set_apply_enabled(False)
