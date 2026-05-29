"""Binary-Sensor-Plattform: Lux-Gate (lights_allowed) + Apply-Blocked."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DATA_COORDINATOR,
    DOMAIN,
    OBJID_LUX_GATE,
    UID_APPLY_BLOCKED,
    UID_LUX_GATE,
    unique_id,
)
from .entity import LightPolicyEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([
        LuxGateBinarySensor(coord, entry),
        ApplyBlockedBinarySensor(coord, entry),
    ])


class LuxGateBinarySensor(LightPolicyEntity, BinarySensorEntity):
    """on = Licht erlaubt (dunkel genug). Wird auch vom Rollo-Modul konsumiert."""

    _attr_icon = "mdi:brightness-4"

    def __init__(self, coord, entry):
        super().__init__(coord, entry)
        self._attr_unique_id = unique_id(UID_LUX_GATE)
        self._attr_name = "Lights Allowed (Lux Gate)"
        self._attr_suggested_object_id = OBJID_LUX_GATE

    @property
    def is_on(self) -> bool:
        p = self.coord.last_plan
        return bool(p and p.lux_gate_on)


class ApplyBlockedBinarySensor(LightPolicyEntity, BinarySensorEntity):
    """on = Plan darf gerade NICHT angewendet werden (Gating aktiv)."""

    _attr_icon = "mdi:lock-alert"

    def __init__(self, coord, entry):
        super().__init__(coord, entry)
        self._attr_unique_id = unique_id(UID_APPLY_BLOCKED)
        self._attr_name = "Living Room Apply Blocked"
        self._attr_suggested_object_id = "living_room_apply_blocked"

    @property
    def is_on(self) -> bool:
        p = self.coord.last_plan
        return bool(p and not p.apply_allowed)

    @property
    def extra_state_attributes(self):
        p = self.coord.last_plan
        return {"blockers": list(p.blockers) if p else []}
