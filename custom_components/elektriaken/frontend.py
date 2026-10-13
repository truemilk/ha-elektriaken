"""Serve and register the bundled Elektriaken card."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import CARD_RESOURCE_URL, CARD_URL

_LOGGER = logging.getLogger(__name__)


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the bundle and add it to storage-mode Lovelace once."""
    bundle = Path(__file__).parent / "frontend" / "elektriaken-card.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(bundle), cache_headers=True)]
    )

    lovelace: Any = hass.data.get("lovelace")
    resources = getattr(lovelace, "resources", None)
    if resources is None:
        _LOGGER.debug("Lovelace resource storage unavailable; YAML resource entry may be required")
        return
    try:
        # async_get_info forces the lazy storage collection to load before a
        # create, preventing existing resources from being overwritten.
        await resources.async_get_info()
        items = resources.async_items()
        existing = next(
            (item for item in items if str(item.get("url", "")).split("?", 1)[0] == CARD_URL),
            None,
        )
        if existing is None:
            await resources.async_create_item({"res_type": "module", "url": CARD_RESOURCE_URL})
        elif existing.get("url") != CARD_RESOURCE_URL:
            await resources.async_update_item(
                existing["id"], {"res_type": "module", "url": CARD_RESOURCE_URL}
            )
    except (AttributeError, ValueError) as err:
        _LOGGER.warning("Could not auto-register Elektriaken card resource: %s", err)
