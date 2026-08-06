"""ConfigEntry migrations for Benni Light Policy."""
from __future__ import annotations

from typing import Any

from .const import (
    CONF_ACTIVITY_STATE,
    CONF_BIO_STATE,
    CONF_CALENDAR_THEME,
    CONF_DAY_STATE,
    CONF_ENTERTAINMENT_STABLE,
    CONF_GROUP_ALL,
    CONF_LUX,
    CONF_MEDIA_CONTEXT,
    CONF_MEDIA_DEVICE,
    CONF_PRESENCE_HOUSEHOLD,
    CONF_PRESENCE_PERSONAL,
    CONF_PRESENCE_TRANSITION,
    CONF_SEASON,
    CONF_SYSTEM_READY,
)

# WZ-Deckenlicht = zwei light-Entities (weißes Panel + Aqara-RGB-Ring).
CEILING_WHITE: str = "light.living_ceiling_light_white"
CEILING_RGB: str = "light.living_ceiling_light_rgb"

LEGACY_ENTITY_REPLACEMENTS: dict[str, str] = {
    # Core-State PR #25/#31: Combined-/Toolbox-Referenzen bleiben als
    # Eingangsbestand kompatibel, werden aber auf die kanonischen Clean-IDs
    # migriert. Core State selbst führt dabei keinen stillen Alias ein.
    "sensor.benni_context_bio_state": "sensor.benni_core_state_bio_state",
    "sensor.benni_combined_context_bio_state": "sensor.benni_core_state_bio_state",
    "sensor.benni_context_activity_state": "sensor.benni_core_state_activity_state",
    "sensor.benni_combined_context_activity_state": "sensor.benni_core_state_activity_state",
    "sensor.benni_context_day_state": "sensor.benni_core_state_day_state",
    "sensor.benni_combined_context_day_state": "sensor.benni_core_state_day_state",
    "sensor.benni_context_day_context": "sensor.benni_core_state_day_context",
    "sensor.benni_combined_context_day_context": "sensor.benni_core_state_day_context",
    "sensor.benni_context_presence_personal": "sensor.benni_core_state_presence_personal",
    "sensor.benni_combined_context_presence_personal": "sensor.benni_core_state_presence_personal",
    "sensor.benni_combined_context_presence_household": "sensor.benni_core_state_presence_household",
    "sensor.benni_combined_context_presence_transition": "sensor.benni_core_state_presence_transition",
    # Media State bleibt der Owner: nur die belegte historische Toolbox-ID
    # wird auf den bestehenden Media-State-Contract umgestellt. Beide alten
    # Media-Context-Entity-Namensformen sind im historischen Repository belegt.
    "sensor.benni_media_context": "sensor.benni_media_state_media_context",
    "sensor.benni_media_context_media_context": "sensor.benni_media_state_media_context",
    "sensor.benni_media_device": "sensor.benni_media_state_media_device",
    "sensor.garden_illuminance_atomic": "sensor.benni_device_garden_lux",
    "sensor.weather_season_meteorological_atomic": (
        "sensor.benni_device_weather_season_meteorological"
    ),
    "binary_sensor.benni_media_context_entertainment_active": (
        "binary_sensor.benni_media_state_entertainment_active"
    ),
    "binary_sensor.benni_entertainment_active": (
        "binary_sensor.benni_media_state_entertainment_active"
    ),
    # Parent Issue #33: migrate only the two IDs proven as Light-Policy
    # consumer candidates.  The YAML helper itself is not an alias owner.
    "binary_sensor.system_apply_ready": "binary_sensor.benni_core_state_apply_ready",
    "binary_sensor.system_benni_context_ready": "binary_sensor.benni_core_state_apply_ready",
}

MIGRATED_ENTITY_KEYS: tuple[str, ...] = (
    CONF_BIO_STATE,
    CONF_ACTIVITY_STATE,
    CONF_CALENDAR_THEME,
    CONF_DAY_STATE,
    CONF_ENTERTAINMENT_STABLE,
    CONF_LUX,
    CONF_MEDIA_CONTEXT,
    CONF_MEDIA_DEVICE,
    CONF_PRESENCE_HOUSEHOLD,
    CONF_PRESENCE_PERSONAL,
    CONF_PRESENCE_TRANSITION,
    CONF_SEASON,
    CONF_SYSTEM_READY,
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
