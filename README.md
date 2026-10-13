# Elektriaken

Elektriaken is a Home Assistant custom integration and bundled Lovelace card for Estonia's Elering day-ahead electricity prices. It supports the native 15-minute market periods, hourly averages, configurable VAT, and cheapest contiguous windows across today and tomorrow.

Requires Home Assistant 2025.10 or newer. This is an early manual-installation release; it is structured for HACS but is not in the HACS default catalog.

## Install

1. Copy `custom_components/elektriaken` into the Home Assistant `/config/custom_components` directory.
2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration**, search for **Elektriaken**, and choose VAT, sensor resolution, and default window duration.

For a storage-mode dashboard, the integration registers its bundled card automatically. If the dashboard uses YAML mode, add this resource:

```yaml
lovelace:
  mode: yaml
  resources:
    - url: /elektriaken/elektriaken-card.js?v=0.1.0
      type: module
```

Then add the card visually or in YAML:

```yaml
type: custom:elektriaken-card
title: Electricity price
resolution: 15
duration_minutes: 60
duration_presets: [15, 30, 60, 120, 180, 240]
include_vat: true
```

In hourly mode, the default duration choices are 1, 2, 3, 4, 6, and 8 hours. All duration values in YAML are minutes.

## Entities and automation

- `sensor.elektriaken_current_price` is the current configured-resolution price in `c/kWh`. Attributes include the raw EUR/MWh value, VAT rate, and UTC period bounds.
- `sensor.elektriaken_best_window` is a timestamp sensor for the next cheapest configured-duration window. Attributes include its end, duration, average price, and savings compared with starting in the current market period.

The complete series is available only through the authenticated `elektriaken/get_prices` WebSocket command and is deliberately excluded from entity attributes to avoid Recorder growth.

Example automation:

```yaml
triggers:
  - trigger: time
    at: sensor.elektriaken_best_window
actions:
  - action: switch.turn_on
    target:
      entity_id: switch.water_heater
```

## Behavior

The integration requests explicit UTC bounds corresponding to local midnight today through local midnight after tomorrow. It refreshes every 30 minutes, retains the last successful dataset during temporary failures, and updates sensor state at each market boundary. UTC continuity is used internally, so negative prices, midnight windows, missing tomorrow data, repeated DST hours, and 23/25-hour local days are handled without assuming 96 periods per day.

Prices are Elering's market energy price only. Network charges, electricity tax, renewable-energy fees, supplier margin, consumption, and device control are not included. VAT defaults to 24% and is calculated as `EUR/MWh ÷ 10 × (1 + VAT/100)`.

## Local development

Backend tests and checks:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
pytest
ruff check .
```

Card development:

```bash
cd frontend
npm install
npm test
npm run typecheck
npm run build
```

The production build is written to `custom_components/elektriaken/frontend/elektriaken-card.js` and should be committed with source changes.

For a manual smoke test, install the integration in a Home Assistant 2025.10+ test instance, confirm both sensors populate, check that `/elektriaken/elektriaken-card.js?v=0.1.0` loads, add the card, and inspect 15-minute/hourly modes on mobile and desktop in light and dark themes. Temporarily blocking `dashboard.elering.ee` is a useful check that existing values survive a failed refresh.

## Data source and independence

Price data comes from the public [Elering dashboard API](https://dashboard.elering.ee/api/nps/price). Elektriaken is an independent, unofficial project. It is not affiliated with or endorsed by Elering, Nord Pool, or Home Assistant. Data availability and correctness remain the responsibility of the upstream source.

## License

MIT
