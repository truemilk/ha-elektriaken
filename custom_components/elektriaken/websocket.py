"""WebSocket API for price series used by the card."""

from __future__ import annotations

from datetime import UTC
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
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
from .pricing import cheapest_window, periods_for_resolution, price_cents_kwh


@websocket_api.websocket_command(
    {
        vol.Required("type"): "elektriaken/get_prices",
        vol.Optional("resolution", default=DEFAULT_RESOLUTION): vol.In([15, 60]),
        vol.Optional("duration_minutes", default=DEFAULT_DURATION): vol.All(
            int, vol.Range(min=15, max=1440)
        ),
        vol.Optional("include_vat", default=True): bool,
    }
)
@websocket_api.async_response
async def websocket_get_prices(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return normalized series without putting it in entity attributes."""
    entries = hass.data.get(DOMAIN, {})
    coordinator = next(iter(entries.values()), None)
    if coordinator is None or coordinator.data is None:
        connection.send_error(msg["id"], "not_ready", "Elektriaken price data is not ready")
        return

    options = coordinator.config_entry.options
    vat_rate = float(options.get(CONF_VAT_RATE, DEFAULT_VAT_RATE))
    resolution = int(msg.get("resolution", options.get(CONF_RESOLUTION, DEFAULT_RESOLUTION)))
    duration = int(msg.get("duration_minutes", options.get(CONF_DURATION, DEFAULT_DURATION)))
    include_vat = bool(msg["include_vat"])
    timezone = dt_util.get_time_zone(hass.config.time_zone) or UTC
    now = dt_util.utcnow()
    periods = periods_for_resolution(coordinator.data, resolution, timezone)
    best = cheapest_window(periods, duration, now)
    local_today = now.astimezone(timezone).date()

    def point(item: Any) -> dict[str, Any]:
        local = item.start.astimezone(timezone)
        return {
            "start": item.start.isoformat(),
            "end": item.end.isoformat(),
            "price": round(price_cents_kwh(item.price, vat_rate, include_vat), 4),
            "raw_eur_mwh": item.price,
            "day": "today" if local.date() == local_today else "tomorrow",
        }

    best_payload = None
    if best:
        current_average = best.starting_now_average_raw
        average = price_cents_kwh(best.average_raw, vat_rate, include_vat)
        best_payload = {
            "start": best.start.isoformat(),
            "end": best.end.isoformat(),
            "duration_minutes": best.duration_minutes,
            "average_price": round(average, 4),
            "savings_vs_now": (
                round(price_cents_kwh(current_average, vat_rate, include_vat) - average, 4)
                if current_average is not None
                else None
            ),
        }
    connection.send_result(
        msg["id"],
        {
            "resolution": resolution,
            "duration_minutes": duration,
            "include_vat": include_vat,
            "vat_rate": vat_rate,
            "currency": "c/kWh",
            "points": [point(item) for item in periods],
            "best_window": best_payload,
            "tomorrow_available": any(
                item.start.astimezone(timezone).date() > local_today for item in periods
            ),
            "updated_at": coordinator.fetched_at.isoformat() if coordinator.fetched_at else None,
        },
    )


def async_register_websocket(hass: HomeAssistant) -> None:
    """Register Elektriaken commands."""
    websocket_api.async_register_command(hass, websocket_get_prices)
