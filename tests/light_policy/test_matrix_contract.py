"""Pure tests for the canonical nine-phase matrix contract."""

import lp_const as C


def test_primary_matrix_uses_core_state_order_without_legacy_only_phases() -> None:
    assert C.CANONICAL_MATRIX_PHASES == C.CORE_DAY_PHASES == (
        "early_night",
        "late_night",
        "early_morning",
        "forenoon",
        "midday",
        "afternoon",
        "late_afternoon",
        "evening",
        "late_evening",
    )
    assert C.LEGACY_MATRIX_PHASES == ("late_morning", "early_evening")


def test_matrix_keys_default_to_exactly_nine_phases_per_theme() -> None:
    keys = C.matrix_keys(["spring", "summer"])

    assert len(keys) == 18
    assert keys[:9] == [f"spring_{phase}" for phase in C.CORE_DAY_PHASES]
    assert keys[9:] == [f"summer_{phase}" for phase in C.CORE_DAY_PHASES]
    assert not any(key.endswith(("_late_morning", "_early_evening")) for key in keys)


def test_legacy_and_supported_matrix_keys_remain_available_explicitly() -> None:
    legacy = C.matrix_keys(["spring"], C.LEGACY_MATRIX_PHASES)
    supported = C.matrix_keys(["spring"], C.SUPPORTED_DAY_PHASES)

    assert legacy == ["spring_late_morning", "spring_early_evening"]
    assert len(supported) == 11
    assert supported[:9] == [f"spring_{phase}" for phase in C.CORE_DAY_PHASES]
