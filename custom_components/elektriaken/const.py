"""Constants for Elektriaken."""

from datetime import timedelta

DOMAIN = "elektriaken"
NAME = "Elektriaken"
VERSION = "0.1.0"

API_URL = "https://dashboard.elering.ee/api/nps/price"
AREA = "ee"
PLATFORMS = ["sensor"]

CONF_VAT_RATE = "vat_rate"
CONF_RESOLUTION = "resolution"
CONF_DURATION = "duration_minutes"

DEFAULT_VAT_RATE = 24.0
DEFAULT_RESOLUTION = 15
DEFAULT_DURATION = 60
UPDATE_INTERVAL = timedelta(minutes=30)

CARD_URL = f"/{DOMAIN}/elektriaken-card.js"
CARD_RESOURCE_URL = f"{CARD_URL}?v={VERSION}"
