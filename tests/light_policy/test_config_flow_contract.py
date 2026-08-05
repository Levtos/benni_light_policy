"""Config-flow contract checks; require Home Assistant's test/runtime package."""
from __future__ import annotations

import pytest
import voluptuous as vol

pytest.importorskip("homeassistant.config_entries")

from custom_components.benni_light_policy.config_flow import (  # noqa: E402
    SELECTORS,
    LightPolicyConfigFlow,
    LightPolicyOptionsFlow,
)
from custom_components.benni_light_policy.const import (  # noqa: E402
    CONF_SOURCE_PRIORITY,
    CONFIG_ENTRY_VERSION,
    SUBENTRY_BATHROOM,
    SUBENTRY_GAMING,
    SUBENTRY_HALLWAY,
    SUBENTRY_MUSIC,
    SUBENTRY_NOTIFICATION_RING,
    SUBENTRY_WAKE_UP,
)


def test_config_and_options_flow_use_current_version():
    assert LightPolicyConfigFlow.VERSION == CONFIG_ENTRY_VERSION
    assert LightPolicyOptionsFlow is not None


def test_source_priority_accepts_zero_and_rejects_negative_values():
    selector = SELECTORS[CONF_SOURCE_PRIORITY]
    assert selector(0) == 0
    with pytest.raises(vol.Invalid):
        selector(-1)


def test_all_supported_subentry_types_are_registered():
    supported = LightPolicyConfigFlow.async_get_supported_subentry_types(None)
    assert set(supported) == {
        SUBENTRY_GAMING,
        SUBENTRY_MUSIC,
        SUBENTRY_NOTIFICATION_RING,
        SUBENTRY_HALLWAY,
        SUBENTRY_BATHROOM,
        SUBENTRY_WAKE_UP,
    }
