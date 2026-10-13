"""Elering API client."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta, tzinfo
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import API_URL
from .models import PricePeriod
from .pricing import InvalidPriceData, parse_response


class ElektriakenApiError(Exception):
    """Raised when Elering cannot be queried."""


def query_range(now: datetime, timezone: tzinfo) -> tuple[datetime, datetime]:
    """Return UTC bounds covering today and tomorrow in the HA timezone."""
    local_date = now.astimezone(timezone).date()
    start = datetime.combine(local_date, time.min, timezone).astimezone(UTC)
    end = datetime.combine(local_date + timedelta(days=2), time.min, timezone).astimezone(UTC)
    return start, end


def _iso_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class EleringClient:
    """Small asynchronous client for the public Elering endpoint."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def async_get_prices(self, start: datetime, end: datetime) -> list[PricePeriod]:
        params = {
            "start": _iso_utc(start),
            # Elering treats end as inclusive. Keep the next local midnight out.
            "end": _iso_utc(end - timedelta(milliseconds=1)),
            "fields": "ee",
        }
        try:
            async with self._session.get(API_URL, params=params, timeout=20) as response:
                response.raise_for_status()
                payload: dict[str, Any] = await response.json()
            return parse_response(payload, range_start=start, range_end=end)
        except (ClientError, TimeoutError, ValueError, InvalidPriceData) as err:
            raise ElektriakenApiError(str(err)) from err
