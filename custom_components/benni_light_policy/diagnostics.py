"""Diagnostics-Download für eine Config-Entry (Geräte-Menü → Diagnose).

Liefert Config + letzten Plan + Lux-Gate-Internals als ein JSON — macht das
Shadow-Debugging und das gemeinsame Durchgehen einfach.
"""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DATA_COORDINATOR, DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    bucket = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coord = bucket.get(DATA_COORDINATOR)

    data: dict[str, Any] = {
        "config": {
            "data": dict(entry.data),
            "options": dict(entry.options),
        }
    }
    if coord is not None:
        plan = coord.last_plan
        data["state"] = {
            "plan": plan.as_dict() if plan else None,
            "lux_gate": coord.gate_internals(),
            "ring_mode": coord.ring_mode,
            "bedtime_signal_active": coord.bedtime_signal_active,
            "startup_ready": coord.startup_ready,
            "apply_enabled": coord.apply_enabled,
            "manual_off_active": coord.manual_off_active,
        }
    return data
