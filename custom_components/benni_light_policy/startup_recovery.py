"""Pure helpers for the one-shot startup Lux recovery gate."""
from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

FALLBACK_LUX = 1.0
INVALID_LUX_STATES = frozenset({"unknown", "unavailable"})
LUX_SOURCE_ROLE = "lux_source"


@dataclass(frozen=True)
class LuxSample:
    """Classified Lux input used by the coordinator and its diagnostics."""

    value: float | None
    timestamp: datetime | None
    reason: str

    @property
    def fresh(self) -> bool:
        return self.value is not None and self.reason == "fresh"


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _parse_lux(raw: Any) -> float | None:
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, str) and raw.strip().lower() in INVALID_LUX_STATES:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value


def _as_bool(raw: Any) -> bool | None:
    """Read explicit contract booleans without treating unknown as healthy."""
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)) and raw in (0, 1):
        return bool(raw)
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value in {"true", "on", "yes", "1"}:
            return True
        if value in {"false", "off", "no", "0"}:
            return False
    return None


def _source_available(
    attributes: Mapping[str, Any],
    *,
    source_key: str,
) -> bool | None:
    """Resolve the configured Lux source from the canonical source map."""
    raw = attributes.get("source_available")
    if isinstance(raw, Mapping):
        for key in (source_key, LUX_SOURCE_ROLE):
            if key in raw:
                return _as_bool(raw[key])
        return None
    return _as_bool(raw)


def _healthy_one_lux_contract(
    attributes: Mapping[str, Any] | None,
    *,
    source_key: str,
) -> bool:
    """Require explicit healthy provenance before accepting a post-start 1 lx."""
    if not isinstance(attributes, Mapping):
        return False
    for key in ("fallback_active", "is_fallback"):
        if key in attributes and _as_bool(attributes[key]) is not False:
            return False
    return (
        _as_bool(attributes.get("available")) is True
        and _as_bool(attributes.get("fresh")) is True
        and str(attributes.get("atomic_quality", "")).strip().lower() == "ok"
        and _as_bool(attributes.get("fail_safe_active")) is False
        and _as_bool(attributes.get("degraded")) is False
        and _source_available(attributes, source_key=source_key) is True
    )


def classify_lux(
    raw_state: Any,
    timestamp: datetime | None,
    startup_started_at: datetime | None,
    *,
    attributes: Mapping[str, Any] | None = None,
    source_key: str = LUX_SOURCE_ROLE,
) -> LuxSample:
    """Accept only a real post-start measurement for startup recovery.

    The source's ``last_reported`` timestamp should be supplied by the caller;
    ``last_updated``/``last_changed`` are compatibility fallbacks. A value of
    exactly 1 lx is accepted only with an explicit healthy Lux contract; missing
    or degraded provenance remains fail-safe blocked.
    """
    state = str(raw_state).strip().lower() if raw_state is not None else ""
    if state in INVALID_LUX_STATES:
        return LuxSample(None, timestamp, f"state_{state}")

    value = _parse_lux(raw_state)
    if value is None:
        return LuxSample(None, timestamp, "invalid_numeric_state")

    sample_time = _as_utc(timestamp)
    start_time = _as_utc(startup_started_at)
    if sample_time is None:
        return LuxSample(None, timestamp, "missing_timestamp")
    if start_time is None:
        return LuxSample(None, timestamp, "missing_start_reference")
    if sample_time <= start_time:
        return LuxSample(None, timestamp, "stale_before_start")
    if value == FALLBACK_LUX and not _healthy_one_lux_contract(
        attributes,
        source_key=source_key,
    ):
        return LuxSample(None, timestamp, "known_fallback_1_lx")
    return LuxSample(value, timestamp, "fresh")


@dataclass
class StartupRecoveryState:
    """Non-persisted, one-shot recovery state for one integration setup."""

    complete: bool = False
    apply_count: int = 0

    @property
    def pending(self) -> bool:
        return not self.complete

    def maybe_complete(self, *, startup_ready: bool, lux_fresh: bool) -> bool:
        """Complete once, and return whether this call crossed the boundary."""
        if self.complete or not startup_ready or not lux_fresh:
            return False
        self.complete = True
        self.apply_count += 1
        return True
