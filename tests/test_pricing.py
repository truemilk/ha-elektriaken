from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from custom_components.elektriaken.models import PricePeriod
from custom_components.elektriaken.pricing import (
    InvalidPriceData,
    aggregate_hourly,
    cheapest_window,
    parse_response,
    price_cents_kwh,
)


def periods(prices, start=datetime(2025, 1, 1, tzinfo=UTC), minutes=15):
    step = timedelta(minutes=minutes)
    return [
        PricePeriod(start + i * step, start + (i + 1) * step, value)
        for i, value in enumerate(prices)
    ]


def test_conversion_and_negative_prices():
    assert price_cents_kwh(100, 24) == pytest.approx(12.4)
    assert price_cents_kwh(100, 24, False) == 10
    assert price_cents_kwh(-50, 24) == pytest.approx(-6.2)


def test_parse_sorts_deduplicates_and_derives_periods():
    payload = {
        "success": True,
        "data": {
            "ee": [
                {"timestamp": 1735690500, "price": -2},
                {"timestamp": 1735689600, "price": 10},
                {"timestamp": 1735690500, "price": 20},
            ]
        },
    }
    result = parse_response(payload)
    assert [item.price for item in result] == [10.0, 20.0]
    assert all(item.minutes == 15 for item in result)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"success": False, "data": {}},
        {"success": True, "data": {}},
        {"success": True, "data": {"ee": [{"timestamp": "bad", "price": 1}]}},
        {"success": True, "data": {"ee": [{"timestamp": 1, "price": float("nan")}]}},
    ],
)
def test_malformed_response(payload):
    with pytest.raises(InvalidPriceData):
        parse_response(payload)


def test_hourly_aggregation_and_negative_value():
    result = aggregate_hourly(periods([-20, 0, 20, 40]), ZoneInfo("Europe/Tallinn"))
    assert len(result) == 1
    assert result[0].price == pytest.approx(10)
    assert result[0].minutes == 60


def test_incomplete_hour_is_not_published():
    assert aggregate_hourly(periods([1, 2, 3]), ZoneInfo("Europe/Tallinn")) == []


def test_cheapest_window_tie_chooses_earliest_and_savings():
    source = periods([8, 8, 1, 1, 1, 1, 1, 1])
    now = source[0].start + timedelta(minutes=2)
    result = cheapest_window(source, 30, now)
    assert result is not None
    assert result.start == source[2].start
    assert result.average_raw == 1
    assert result.starting_now_average_raw == 8


def test_window_crosses_midnight():
    source = periods([9, 5, 1, 1], datetime(2025, 1, 1, 23, 30, tzinfo=UTC))
    result = cheapest_window(source, 30, source[0].start)
    assert result is not None
    assert result.start.date().isoformat() == "2025-01-02"
    assert result.end.hour == 0 and result.end.minute == 30


def test_gap_and_unavailable_duration_are_rejected():
    source = periods([1, 2, 3])
    source[1] = PricePeriod(
        source[1].start + timedelta(minutes=15), source[1].end + timedelta(minutes=15), 2
    )
    assert cheapest_window(source, 30, source[0].start) is None
    assert cheapest_window(periods([1, 2]), 60, periods([1, 2])[0].start) is None


def test_dst_fall_back_keeps_both_local_hours():
    # Europe/Tallinn repeats 03:00 on 2025-10-26 (offsets +03 and +02).
    source = periods(range(12), datetime(2025, 10, 25, 23, 0, tzinfo=UTC))
    result = aggregate_hourly(source, ZoneInfo("Europe/Tallinn"))
    assert len(result) == 3
    local = [item.start.astimezone(ZoneInfo("Europe/Tallinn")) for item in result]
    repeated = [item for item in local if item.hour == 3]
    assert len(repeated) == 2
    assert repeated[0].utcoffset() != repeated[1].utcoffset()


def test_dst_days_have_23_and_25_hourly_periods():
    zone = ZoneInfo("Europe/Tallinn")
    spring = periods(range(23 * 4), datetime(2025, 3, 29, 22, tzinfo=UTC))
    fall = periods(range(25 * 4), datetime(2025, 10, 25, 21, tzinfo=UTC))
    assert len(aggregate_hourly(spring, zone)) == 23
    assert len(aggregate_hourly(fall, zone)) == 25
