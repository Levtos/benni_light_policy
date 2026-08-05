import lp_const as C
import lp_migration as M


def test_config_entry_version_triggers_fleet54_migration() -> None:
    assert C.CONFIG_ENTRY_VERSION == 5


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


def test_canonical_core_state_day_context_is_not_rewritten() -> None:
    data = {C.CONF_CALENDAR_THEME: "sensor.benni_core_state_day_context"}
    options: dict[str, str] = {}

    new_data, new_options, changed = M.migrate_legacy_entity_ids(data, options)

    assert changed is False
    assert new_data == data
    assert new_options == {}


def test_all_canonical_core_and_media_prefills_are_stable() -> None:
    data = {
        key: entity
        for key, entity in C.ENTITY_PREFILL.items()
        if key in M.MIGRATED_ENTITY_KEYS
    }
    options: dict[str, str] = {}

    new_data, new_options, changed = M.migrate_legacy_entity_ids(data, options)

    assert changed is False
    assert new_data == data
    assert new_options == options


def test_legacy_activity_presence_and_media_context_migrate_to_current_contract() -> None:
    data = {
        C.CONF_ACTIVITY_STATE: "sensor.benni_combined_context_activity_state",
        C.CONF_PRESENCE_PERSONAL: "sensor.benni_combined_context_presence_personal",
        C.CONF_PRESENCE_HOUSEHOLD: "sensor.benni_combined_context_presence_household",
        C.CONF_PRESENCE_TRANSITION: "sensor.benni_combined_context_presence_transition",
        C.CONF_MEDIA_CONTEXT: "sensor.benni_media_context",
        C.CONF_MEDIA_DEVICE: "sensor.benni_media_device",
    }

    new_data, _, changed = M.migrate_legacy_entity_ids(data, {})

    assert changed is True
    assert new_data[C.CONF_ACTIVITY_STATE] == C.ENTITY_PREFILL[C.CONF_ACTIVITY_STATE]
    assert new_data[C.CONF_PRESENCE_PERSONAL] == C.ENTITY_PREFILL[C.CONF_PRESENCE_PERSONAL]
    assert new_data[C.CONF_PRESENCE_HOUSEHOLD] == C.ENTITY_PREFILL[C.CONF_PRESENCE_HOUSEHOLD]
    assert new_data[C.CONF_PRESENCE_TRANSITION] == C.ENTITY_PREFILL[C.CONF_PRESENCE_TRANSITION]
    assert new_data[C.CONF_MEDIA_CONTEXT] == C.ENTITY_PREFILL[C.CONF_MEDIA_CONTEXT]
    assert new_data[C.CONF_MEDIA_DEVICE] == C.ENTITY_PREFILL[C.CONF_MEDIA_DEVICE]


# -------------------------------------------- RGB-Ring im Hard-Off-Scope (GROUP_ALL)
def test_ceiling_rgb_added_to_group_all_in_options() -> None:
    data: dict = {}
    options = {C.CONF_GROUP_ALL: [M.CEILING_WHITE, "light.living_sofa_table_lamp"]}

    changed = M.ensure_ceiling_rgb_in_group_all(data, options)

    assert changed is True
    assert M.CEILING_RGB in options[C.CONF_GROUP_ALL]
    # weißes Panel bleibt, Reihenfolge erhalten, RGB hinten angehängt.
    assert options[C.CONF_GROUP_ALL][-1] == M.CEILING_RGB
    assert data == {}


def test_ceiling_rgb_added_to_group_all_in_data_when_no_options() -> None:
    data = {C.CONF_GROUP_ALL: [M.CEILING_WHITE]}
    options: dict = {}

    changed = M.ensure_ceiling_rgb_in_group_all(data, options)

    assert changed is True
    assert M.CEILING_RGB in data[C.CONF_GROUP_ALL]


def test_ceiling_rgb_idempotent_when_already_present() -> None:
    options = {C.CONF_GROUP_ALL: [M.CEILING_WHITE, M.CEILING_RGB]}

    changed = M.ensure_ceiling_rgb_in_group_all({}, options)

    assert changed is False
    assert options[C.CONF_GROUP_ALL].count(M.CEILING_RGB) == 1


def test_ceiling_rgb_noop_when_white_not_in_group() -> None:
    # Andere Installation ohne das WZ-Deckenlicht → nichts anfassen.
    options = {C.CONF_GROUP_ALL: ["light.some_other_lamp"]}

    changed = M.ensure_ceiling_rgb_in_group_all({}, options)

    assert changed is False
    assert M.CEILING_RGB not in options[C.CONF_GROUP_ALL]
