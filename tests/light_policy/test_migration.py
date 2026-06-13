import lp_const as C
import lp_migration as M


def test_config_entry_version_triggers_fleet54_migration() -> None:
    assert C.CONFIG_ENTRY_VERSION == 2


def test_migrate_legacy_entity_ids_updates_data_and_options() -> None:
    data = {
        C.CONF_CALENDAR_THEME: "sensor.benni_context_day_context",
        C.CONF_ENTERTAINMENT_STABLE: "binary_sensor.benni_media_context_entertainment_active",
    }
    options = {
        C.CONF_LUX: "sensor.garden_illuminance_atomic",
        C.CONF_SEASON: "sensor.weather_season_meteorological_atomic",
    }

    new_data, new_options, changed = M.migrate_legacy_entity_ids(data, options)

    assert changed is True
    assert new_data[C.CONF_CALENDAR_THEME] == "sensor.benni_core_state_day_context"
    assert (
        new_data[C.CONF_ENTERTAINMENT_STABLE]
        == "binary_sensor.benni_media_state_entertainment_active"
    )
    assert new_options[C.CONF_LUX] == "sensor.benni_device_garden_lux"
    assert new_options[C.CONF_SEASON] == "sensor.benni_device_weather_season_meteorological"
    assert data[C.CONF_CALENDAR_THEME] == "sensor.benni_context_day_context"
    assert options[C.CONF_LUX] == "sensor.garden_illuminance_atomic"


def test_migrate_legacy_entity_ids_noops_when_clean() -> None:
    data = {C.CONF_CALENDAR_THEME: "sensor.benni_core_state_day_context"}
    options = {
        C.CONF_LUX: "sensor.benni_device_garden_lux",
        C.CONF_SEASON: "sensor.benni_device_weather_season_meteorological",
    }

    new_data, new_options, changed = M.migrate_legacy_entity_ids(data, options)

    assert changed is False
    assert new_data == data
    assert new_options == options
