# FlightGuard

**Will your flight be late?** FlightGuard forecasts delays for US airline flights and shows the carbon footprint of your seat, wrapped in a glossy, early-2000s *Frutiger Aero* look.

![FlightGuard search page](docs/screenshots/search.png)

---

## What it does

### Flight search and delay forecast
Enter a flight number (like `DL1234` or `WN 2531`) and a date. FlightGuard shows:

- **The flight:** route, airport-local departure and arrival times, duration, aircraft, and live status (scheduled, delayed, in the air, landed or cancelled). When the airline posts a new time, the original is struck through and the update is highlighted.
- **A delay forecast:** the chance the flight arrives 15+ minutes late, a low/medium/high risk level, and the expected minutes of delay.
- **The reasons behind it:** plain-language explanations ranked by impact, for example *"Historically 30% of LGA→DEN flights arrive late, most often from a late incoming aircraft"* or *"Thunderstorms forecast at ATL around arrival"*.

The forecast comes from a **gradient-boosting model trained on US Department of Transportation (BTS) on-time records**, covering five months of flights, with a test AUC of 0.70 on a held-out month. Live signals adjust it: **weather forecasts** at both airports (Open-Meteo) and **FAA airport status** (ground stops and delay programs). If the model file is missing, a transparent rule-based score takes over.

![Results page with delay forecast and carbon footprint](docs/screenshots/results.png)

### Carbon footprint
Each result includes the flight's **CO₂e per passenger** for economy, premium economy, business and first class.

- **Source:** estimates come from the **Google Travel Impact Model**. When Google has no data for a flight, they fall back to a typical-route estimate, then to a distance-based estimate. The card always says which kind it is.
- **Equivalents:** to make the number tangible, it's translated into four everyday comparisons:
  - km driven in an average gas car
  - days of an average American's emissions
  - urban tree seedlings needed to absorb it
  - smartphones fully charged

### Live flight map
- **Live aircraft** across the US from the OpenSky Network, refreshed every 15 seconds.
- **Plane popups:** the flight number, origin and destination, altitude, speed and heading, plus a **"Check delay forecast"** button that opens that flight's results page.
- **Airports:** 873 large and medium US airports. Clicking one shows its current weather, FAA status and delay risk.

![Live map with a plane popup](docs/screenshots/map.png)

### Three Frutiger Aero themes
Glass panels, glossy gel buttons, bubbles and nature-meets-technology scenery throughout. The sun/moon/fish button in the header cycles between:

| Day | Night | Aquarium |
|---|---|---|
| Sunny sky over a city skyline with an airport control tower and spinning wind turbines | Aurora night sky with stars, a full moon, lit windows and a blinking tower beacon | Bright turquoise water with light rays, tropical fish and a colorful coral reef |

<table>
  <tr>
    <td><img src="docs/screenshots/night.png" alt="Night theme" /></td>
    <td><img src="docs/screenshots/aquarium.png" alt="Aquarium theme" /></td>
  </tr>
</table>

Add `?theme=light`, `?theme=dark` or `?theme=aquarium` to any URL to open it in that theme. The choice is remembered.

### Works on phones
The layout adapts down to phone width, with a two-row header, full-width controls, and sections that stack into a single column.

<img src="docs/screenshots/mobile.png" alt="Mobile view in the aquarium theme" width="320" />

---

## How it works

```
 Browser (React + Vite)                     FastAPI backend                         Data sources
 ──────────────────────                     ───────────────                         ────────────
 Search ─► /flight/:number/:date ──► GET /api/flights/lookup ──► flight lookup ──► AeroDataBox (schedules, status)
                                                                 ├─ delay model ──► BTS-trained model + Open-Meteo + FAA NAS
                                                                 └─ emissions ────► Google Travel Impact Model
 Map ──────────────────────────────► GET /api/flights/live ───────────────────────► OpenSky Network
                                     GET /api/airports, /api/airports/{iata}
```

- **Frontend** (`frontend/`): React 19, TypeScript, Vite, React Router and Leaflet. The design system is plain CSS with shared tokens and components in `src/components/aero/`. In development, Vite proxies `/api` to the backend.
- **Backend** (`backend/`): Python and FastAPI, with httpx for upstream APIs, in-memory caching to stay within API quotas, and scikit-learn for the delay model. Every API call has a clear error path, so the UI can show a friendly message instead of breaking.

| Data | Used for |
|---|---|
| [AeroDataBox](https://aerodatabox.com/) | Flight schedules, live status, flight numbers for map planes |
| [BTS On-Time Performance](https://www.transtats.bts.gov/) | Training data for the delay model |
| [Open-Meteo](https://open-meteo.com/) | Weather forecasts at origin and destination |
| [FAA NAS Status](https://nasstatus.faa.gov/) | Ground stops, ground delay programs and other airport events |
| [Google Travel Impact Model](https://developers.google.com/travel/impact-model) | Per-passenger flight emissions |
| [EPA equivalencies](https://www.epa.gov/energy/greenhouse-gas-equivalencies-calculator) | Car, tree and smartphone comparisons |
| [OpenSky Network](https://opensky-network.org/) | Live aircraft positions |
| [OpenStreetMap](https://www.openstreetmap.org/) | Map tiles |
| [OurAirports](https://ourairports.com/) | US airport list |

---

## Running it locally

**You'll need:** Node.js 22.22 or newer, Python 3.14, and [uv](https://docs.astral.sh/uv/).

### 1. Backend
```bash
cd backend
cp .env.example .env      # then fill in your keys (see below)
uv sync
uv run fastapi dev app/main.py
```
The API runs at http://127.0.0.1:8000, with interactive docs at `/docs`.

| Variable | What it's for |
|---|---|
| `AERODATABOX_API_KEY` | RapidAPI key for flight lookups and map flight numbers |
| `GOOGLE_TIM_API_KEY` | Google Cloud key with the Travel Impact Model API enabled |
| `OPENSKY_CLIENT_ID`, `OPENSKY_CLIENT_SECRET` | OpenSky API client for the live map. It works anonymously without them, but with a much lower rate limit |
| `OPEN_METEO_BASE_URL`, `FAA_NAS_URL` | Preset, no key needed |
| `DEMO_MODE` | `true` serves a recorded sample flight (`DL1234` on 2026-10-11) with no keys at all |

### 2. Frontend
```bash
cd frontend
npm install
cp .env.example .env.local   # set VITE_USE_MOCKS=false to use the backend
npm run dev
```
Open http://localhost:5173.

`VITE_USE_MOCKS=true` runs the frontend with no backend at all, using sample data. In this mode, the flight numbers `ZZ1`, `ZZ2`, `ZZ404`, `ZZ502` and `ZZ503` preview the empty, delayed and error states.

### Retraining the delay model (optional)
A trained model is already included in `backend/app/data/`. To retrain it, download monthly "Reporting Carrier On-Time Performance" zips from BTS into `backend/ml/data/`, then run:
```bash
cd backend
uv run python ml/train.py
```

### Checks
```bash
cd frontend && npm run lint && npm run build
cd backend && uv run python -m unittest discover -s tests
```

---

## Project structure

```
backend/
  app/
    api/        # FastAPI routes (lookup, predict, eco, live map, airports)
    clients/    # thin wrappers for AeroDataBox, Google TIM, Open-Meteo, FAA, OpenSky
    services/   # flight lookup, delay predictor, emissions, caching
    models/     # Pydantic response schemas
    data/       # trained model, airport list, demo fixtures, eco constants
  ml/train.py   # delay model training
frontend/
  src/
    pages/       # Search, Results, Map, About
    components/  # aero (design system), results, eco, map, search
    api/         # typed API client (+ mock mode)
    types/       # TypeScript mirror of the API contract
docs/screenshots/
```

Contributors (human or AI) should read [`AGENTS.md`](AGENTS.md) first. It covers the API contract, file ownership, the theme guide and the team's working rules.

---

## Notes

- Delay forecasts and emissions are **estimates** to help you plan. They aren't guarantees, and FlightGuard isn't affiliated with any airline.
- FlightGuard currently covers **US passenger airlines** and flights to or from US airports.
