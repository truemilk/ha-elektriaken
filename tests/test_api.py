from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from custom_components.elektriaken.api import query_range


def test_query_range_spring_dst_day_lengths():
    start, end = query_range(datetime(2025, 3, 30, 12, tzinfo=UTC), ZoneInfo("Europe/Tallinn"))
    assert start == datetime(2025, 3, 29, 22, tzinfo=UTC)
    assert (end - start).total_seconds() / 3600 == 47


def test_query_range_fall_dst_day_lengths():
    start, end = query_range(datetime(2025, 10, 26, 12, tzinfo=UTC), ZoneInfo("Europe/Tallinn"))
    assert start == datetime(2025, 10, 25, 21, tzinfo=UTC)
    assert (end - start).total_seconds() / 3600 == 49
