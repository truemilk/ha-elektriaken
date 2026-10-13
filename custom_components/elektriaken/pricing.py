"""Pure price parsing, conversion, aggregation, and window calculations."""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime, timedelta, tzinfo
from typing import Any

from .models import BestWindow, PricePeriod


class InvalidPriceData(ValueError):
    """Raised when Elering returns malformed price data."""


def price_cents_kwh(raw_eur_mwh: float, vat_rate: float, include_vat: bool = True) -> float:
    """Convert EUR/MWh to c/kWh, optionally adding VAT."""
    multiplier = 1 + vat_rate / 100 if include_vat else 1
    return raw_eur_mwh / 10 * multiplier


def parse_response(
    payload: Mapping[str, Any],
    *,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
) -> list[PricePeriod]:
    """Validate an Elering response and turn points into periods.

    The API provides period start timestamps. Ends are derived from the next
    timestamp, using the median observed interval for the final point.
    """
    if payload.get("success") is not True or not isinstance(payload.get("data"), Mapping):
        raise InvalidPriceData("Elering response was unsuccessful or missing data")
    rows = payload["data"].get("ee")
    if not isinstance(rows, list):
        raise InvalidPriceData("Elering response is missing the ee series")

    values: dict[datetime, float] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise InvalidPriceData("A price row is not an object")
        timestamp, price = row.get("timestamp"), row.get("price")
        if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
            raise InvalidPriceData("A price row has an invalid timestamp")
        if (
            isinstance(price, bool)
            or not isinstance(price, (int, float))
            or not math.isfinite(price)
        ):
            raise InvalidPriceData("A price row has an invalid price")
        start = datetime.fromtimestamp(timestamp, UTC)
        values[start] = float(price)

    ordered = sorted(values.items())
    if not ordered:
        return []
    deltas = [
        int((right[0] - left[0]).total_seconds())
        for left, right in zip(ordered, ordered[1:], strict=False)
        if 0 < (right[0] - left[0]).total_seconds() <= 3600
    ]
    fallback_seconds = int(statistics.median(deltas)) if deltas else 900
    periods: list[PricePeriod] = []
    for index, (start, price) in enumerate(ordered):
        end = (
            ordered[index + 1][0]
            if index + 1 < len(ordered)
            else start + timedelta(seconds=fallback_seconds)
        )
        # A gap is not silently represented as one long market period.
        if (end - start).total_seconds() > fallback_seconds:
            end = start + timedelta(seconds=fallback_seconds)
        if range_start is not None and start < range_start:
            continue
        if range_end is not None and start >= range_end:
            continue
        periods.append(PricePeriod(start, end, price))
    return periods


def aggregate_hourly(periods: Sequence[PricePeriod], timezone: tzinfo) -> list[PricePeriod]:
    """Return duration-weighted local-clock hourly averages.

    UTC offset and fold are part of the key, so both repeated hours on the
    autumn DST transition remain separate.
    """
    groups: dict[tuple[Any, ...], list[PricePeriod]] = {}
    for period in periods:
        local = period.start.astimezone(timezone)
        key = (local.date(), local.hour, local.fold, local.utcoffset())
        groups.setdefault(key, []).append(period)

    result: list[PricePeriod] = []
    for group in groups.values():
        group.sort(key=lambda item: item.start)
        seconds = sum((item.end - item.start).total_seconds() for item in group)
        contiguous = all(
            left.end == right.start for left, right in zip(group, group[1:], strict=False)
        )
        # Never label an incomplete or gapped local hour as an hourly price.
        if seconds != 3600 or not contiguous:
            continue
        average = (
            sum(item.price * (item.end - item.start).total_seconds() for item in group) / seconds
        )
        result.append(PricePeriod(group[0].start, group[-1].end, average))
    return sorted(result, key=lambda item: item.start)


def periods_for_resolution(
    periods: Sequence[PricePeriod], resolution: int, timezone: tzinfo
) -> list[PricePeriod]:
    """Normalize a series to the requested resolution."""
    if resolution == 15:
        return list(periods)
    if resolution == 60:
        return aggregate_hourly(periods, timezone)
    raise ValueError("resolution must be 15 or 60")


def period_at(periods: Iterable[PricePeriod], now: datetime) -> PricePeriod | None:
    """Find the market period containing now."""
    return next((item for item in periods if item.start <= now < item.end), None)


def _candidate_windows(
    periods: Sequence[PricePeriod], duration_minutes: int, not_before: datetime
) -> list[tuple[list[PricePeriod], float]]:
    candidates: list[tuple[list[PricePeriod], float]] = []
    for start_index, first in enumerate(periods):
        if first.start < not_before:
            continue
        group: list[PricePeriod] = []
        cursor = first.start
        seconds = 0.0
        weighted = 0.0
        for period in periods[start_index:]:
            if period.start != cursor:
                break
            period_seconds = (period.end - period.start).total_seconds()
            seconds += period_seconds
            weighted += period.price * period_seconds
            group.append(period)
            cursor = period.end
            if seconds == duration_minutes * 60:
                candidates.append((group, weighted / seconds))
                break
            if seconds > duration_minutes * 60:
                break
    return candidates


def cheapest_window(
    periods: Sequence[PricePeriod], duration_minutes: int, now: datetime
) -> BestWindow | None:
    """Find the cheapest future aligned contiguous window; ties choose earliest."""
    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be positive")
    current = period_at(periods, now)
    not_before = current.start if current else now
    candidates = _candidate_windows(periods, duration_minutes, not_before)
    if not candidates:
        return None
    group, average = min(candidates, key=lambda item: (item[1], item[0][0].start))
    current_candidate = next(
        (value for candidate, value in candidates if candidate[0].start == not_before), None
    )
    return BestWindow(
        start=group[0].start,
        end=group[-1].end,
        duration_minutes=duration_minutes,
        average_raw=average,
        starting_now_average_raw=current_candidate,
    )
