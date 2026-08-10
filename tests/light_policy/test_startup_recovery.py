from __future__ import annotations

from datetime import UTC, datetime, timedelta

from lp_pure_pkg.startup_recovery import StartupRecoveryState, classify_lux

START = datetime(2026, 8, 10, 6, 29, 40, tzinfo=UTC)


def test_unknown_unavailable_and_fallback_lux_are_not_fresh() -> None:
    after_start = START + timedelta(seconds=2)

    assert classify_lux("unknown", after_start, START).reason == "state_unknown"
    assert classify_lux("unavailable", after_start, START).reason == "state_unavailable"
    assert classify_lux("1", after_start, START).reason == "known_fallback_1_lx"
    assert classify_lux("1.0", after_start, START).reason == "known_fallback_1_lx"


def test_stale_lux_before_core_start_is_rejected() -> None:
    sample = classify_lux("550", START - timedelta(seconds=1), START)

    assert sample.fresh is False
    assert sample.reason == "stale_before_start"


def test_reconnected_post_start_lux_is_accepted() -> None:
    sample = classify_lux("11596", START + timedelta(minutes=14), START)

    assert sample.fresh is True
    assert sample.value == 11596


def test_startup_recovery_crosses_once_after_gate_and_fresh_lux() -> None:
    recovery = StartupRecoveryState()

    assert recovery.maybe_complete(startup_ready=False, lux_fresh=True) is False
    assert recovery.maybe_complete(startup_ready=True, lux_fresh=False) is False
    assert recovery.pending is True

    assert recovery.maybe_complete(startup_ready=True, lux_fresh=True) is True
    assert recovery.maybe_complete(startup_ready=True, lux_fresh=True) is False
    assert recovery.apply_count == 1
    assert recovery.pending is False


def test_repeated_apply_now_evaluations_do_not_repeat_startup_recovery() -> None:
    recovery = StartupRecoveryState()
    assert recovery.maybe_complete(startup_ready=True, lux_fresh=True) is True

    # ``apply_now`` deliberately re-enters the same evaluator; the startup
    # recovery edge remains one-shot even when the explicit service is repeated.
    assert [
        recovery.maybe_complete(startup_ready=True, lux_fresh=True)
        for _ in range(3)
    ] == [False, False, False]
    assert recovery.apply_count == 1
