"""Update coordinator for Elektriaken."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import ElektriakenApiError, EleringClient, query_range
from .const import DOMAIN, UPDATE_INTERVAL
from .models import PricePeriod

_LOGGER = logging.getLogger(__name__)


class ElektriakenCoordinator(DataUpdateCoordinator[list[PricePeriod]]):
    """Keep the current two local delivery days available."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            config_entry=entry,
        )
        self.client = EleringClient(async_get_clientsession(hass))
        self.fetched_at: datetime | None = None

    async def _async_update_data(self) -> list[PricePeriod]:
        timezone = dt_util.get_time_zone(self.hass.config.time_zone) or UTC
        start, end = query_range(dt_util.utcnow(), timezone)
        try:
            values = await self.client.async_get_prices(start, end)
        except ElektriakenApiError as err:
            # DataUpdateCoordinator retains self.data after UpdateFailed.
            raise UpdateFailed(f"Unable to update Elering prices: {err}") from err
        if not values:
            raise UpdateFailed("Elering returned no prices")
        self.fetched_at = dt_util.utcnow()
        return values

    def now(self) -> datetime:
        """Return UTC now; separated for deterministic tests."""
        return dt_util.utcnow()
