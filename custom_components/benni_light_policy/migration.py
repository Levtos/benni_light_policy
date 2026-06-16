"""ConfigEntry migrations for Benni Light Policy."""
from __future__ import annotations

from typing import Any

from .const import (
    CONF_CALENDAR_THEME,
    CONF_ENTERTAINMENT_STABLE,
    CONF_GROUP_ALL,
    CONF_LUX,
    CONF_SEASON,
)

# WZ-Deckenlicht = zwei light-Entities (weißes Panel + Aqara-RGB-Ring).
CEILING_WHITE: str = "light.living_ceiling_light_white"
CEILING_RGB: str = "light.living_ceiling_light_rgb"

LEGACY_ENTITY_REPLACEMENTS: dict[str, str] = {
    "sensor.benni_context_day_context": "sensor.benni_combined_context_day_context",
    "sensor.benni_core_state_day_context": "sensor.benni_combined_context_day_context",
    "sensor.garden_illuminance_atomic": "sensor.benni_device_garden_lux",
    "sensor.weather_season_meteorological_atomic": (
        "sensor.benni_device_weather_season_meteorological"
    ),
    "binary_sensor.benni_media_context_entertainment_active": (
        "binary_sensor.benni_media_state_entertainment_active"
    ),
}

MIGRATED_ENTITY_KEYS: tuple[str, ...] = (
    CONF_CALENDAR_THEME,
    CONF_ENTERTAINMENT_STABLE,
    CONF_LUX,
    CONF_SEASON,
)


def migrate_legacy_entity_ids(
    data: dict[str, Any],
    options: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Return config data/options with known retired source entities replaced."""
    migrated = False
    new_data = dict(data)
    new_options = dict(options)

    for target in (new_data, new_options):
        for key in MIGRATED_ENTITY_KEYS:
            value = target.get(key)
            replacement = LEGACY_ENTITY_REPLACEMENTS.get(value)
            if replacement is not None:
                target[key] = replacement
                migrated = True

    return new_data, new_options, migrated


def ensure_ceiling_rgb_in_group_all(
    data: dict[str, Any],
    options: dict[str, Any],
) -> bool:
    """Hard-Off-Scope um den RGB-Ring des WZ-Deckenlichts ergänzen.

    Der Aqara-Restart-Bug schaltet `light.living_ceiling_light_rgb` beim HA-Start
    ein. Der Ring ist eine eigene light-Entity und fehlte in GROUP_ALL → der
    idle-Hard-Off (auch der erzwungene Re-Apply nach Neustart) räumte ihn nicht ab,
    er blieb dauerhaft an. Ergänzt ihn idempotent, sofern das weiße Panel bereits
    in GROUP_ALL steht (= diese Installation). Mutiert das effektive Dict in place.
    """
    owner = options if isinstance(options.get(CONF_GROUP_ALL), list) else data
    groups = owner.get(CONF_GROUP_ALL)
    if (
        isinstance(groups, list)
        and CEILING_WHITE in groups
        and CEILING_RGB not in groups
    ):
        owner[CONF_GROUP_ALL] = [*groups, CEILING_RGB]
        return True
    return False
