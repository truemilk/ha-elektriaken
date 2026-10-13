"""Elektriaken sensors."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DURATION,
    CONF_RESOLUTION,
    CONF_VAT_RATE,
    DEFAULT_DURATION,
    DEFAULT_RESOLUTION,
    DEFAULT_VAT_RATE,
    DOMAIN,
)
from .coordinator import ElektriakenCoordinator
from .pricing import cheapest_window, period_at, periods_for_resolution, price_cents_kwh


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Elektriaken sensors."""
    coordinator: ElektriakenCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ElektriakenCurrentPrice(coordinator), ElektriakenBestWindow(coordinator)])


class ElektriakenEntity(CoordinatorEntity[ElektriakenCoordinator], SensorEntity):
    """Base sensor with market-boundary updates."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ElektriakenCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"elektriaken_{key}"
        self._cancel_boundary = None

    @property
    def available(self) -> bool:
        """Keep the last valid dataset available during transient API failures."""
        return bool(self.coordinator.data)

    @property
    def _vat_rate(self) -> float:
        return float(self.coordinator.config_entry.options.get(CONF_VAT_RATE, DEFAULT_VAT_RATE))

    @property
    def _resolution(self) -> int:
        return int(self.coordinator.config_entry.options.get(CONF_RESOLUTION, DEFAULT_RESOLUTION))

    @property
    def _periods(self):
        timezone = dt_util.get_time_zone(self.hass.config.time_zone) or UTC
        return periods_for_resolution(self.coordinator.data or [], self._resolution, timezone)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.async_add_listener(self._schedule_boundary))
        self.async_on_remove(self._cancel_scheduled_boundary)
        self._schedule_boundary()

    @callback
    def _cancel_scheduled_boundary(self) -> None:
        if self._cancel_boundary:
            self._cancel_boundary()
            self._cancel_boundary = None

    @callback
    def _schedule_boundary(self) -> None:
        if self._cancel_boundary:
            self._cancel_boundary()
            self._cancel_boundary = None
        now = dt_util.utcnow()
        future = next((item.end for item in self._periods if item.end > now), None)
        if future is not None:
            self._cancel_boundary = async_track_point_in_utc_time(
                self.hass, self._handle_boundary, future + timedelta(milliseconds=10)
            )

    @callback
    def _handle_boundary(self, now: datetime) -> None:
        self.async_write_ha_state()
        self._schedule_boundary()


class ElektriakenCurrentPrice(ElektriakenEntity):
    """Current configured-resolution price."""

    entity_description = SensorEntityDescription(
        key="current_price",
        translation_key="current_price",
        native_unit_of_measurement="c/kWh",
        icon="mdi:currency-eur",
    )
    _attr_suggested_display_precision = 3
    _attr_suggested_object_id = "elektriaken_current_price"

    def __init__(self, coordinator: ElektriakenCoordinator) -> None:
        super().__init__(coordinator, "current_price")

    @property
    def native_value(self) -> float | None:
        current = period_at(self._periods, dt_util.utcnow())
        return round(price_cents_kwh(current.price, self._vat_rate), 4) if current else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        current = period_at(self._periods, dt_util.utcnow())
        if not current:
            return {"vat_rate": self._vat_rate}
        return {
            "raw_eur_mwh": current.price,
            "vat_rate": self._vat_rate,
            "period_start": current.start.isoformat(),
            "period_end": current.end.isoformat(),
            "resolution_minutes": self._resolution,
        }


class ElektriakenBestWindow(ElektriakenEntity):
    """Timestamp of the next cheapest contiguous window."""

    entity_description = SensorEntityDescription(
        key="best_window",
        translation_key="best_window",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-check-outline",
    )
    _attr_suggested_object_id = "elektriaken_best_window"

    def __init__(self, coordinator: ElektriakenCoordinator) -> None:
        super().__init__(coordinator, "best_window")

    @property
    def _window(self):
        duration = int(self.coordinator.config_entry.options.get(CONF_DURATION, DEFAULT_DURATION))
        return cheapest_window(self._periods, duration, dt_util.utcnow())

    @property
    def native_value(self) -> datetime | None:
        return self._window.start if self._window else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        window = self._window
        if not window:
            return {}
        average = price_cents_kwh(window.average_raw, self._vat_rate)
        return {
            "end": window.end.isoformat(),
            "duration_minutes": window.duration_minutes,
            "average_price": round(average, 4),
            "savings_vs_starting_now": (
                round(price_cents_kwh(window.starting_now_average_raw, self._vat_rate) - average, 4)
                if window.starting_now_average_raw is not None
                else None
            ),
            "unit": "c/kWh",
        }
