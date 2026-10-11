# Project Overview — (name TBD, code currently says "FlightGuard")

> **Read this first.** This is the source of truth for every AI assistant (Claude, Copilot, Cursor, Codex, etc.) and every human on the team. When a decision gets made, update this file in the same PR.

HackNC 2026 hackathon project. **4 people, 22 hours, and we want to sleep.** Favor working demos over perfect architecture. Cut scope before cutting sleep.

---

## 1. The Pitch

A **Frutiger Aero–themed flight delay predictor** for **US airlines**, with built-in **eco awareness**.

**Main flow (flight search first):**
1. User searches a flight by number and date (e.g. `DL1234`, tomorrow).
2. Results page shows:
   - flight details (route, times, live status),
   - a **delay prediction** (risk, estimated minutes, and *why*),
   - the flight's **CO2 per passenger** with relatable comparisons.
3. A separate **Map tab** shows live planes and airports. It's secondary: nice to have and good for the demo, but not the core.

Frutiger Aero (the Windows Vista/7, early-2000s "nature + technology" look) fits an eco app well: its style is already full of skies, water, leaves and clean energy.

---

## 2. Decisions So Far

| Topic | Decision |
|---|---|
| Name | TBD. Use "FlightGuard" in code until renamed. |
| Home screen | **Flight search** (delay prediction is the main goal). Map lives in its own tab. |
| Routing | **React Router** (`react-router` v8, declarative mode with `BrowserRouter`). Routes in §8. |
| Roles | Assigned by the team (§9). |
| Scope | **US passenger airlines only, with at least one US airport.** International routes qualify when they start or end in the US. FAA and BTS signals may cover only the US portion of a route. |
| Flight data API | **AeroDataBox** via RapidAPI (see §6.1). Pro tier is subscribed; the key is kept in the local `backend/.env`. |
| Delay prediction | Heuristic first, then **train a model on BTS data if time permits**. |
| CO2 source | **Google Travel Impact Model (TIM) API.** |
| OpenSky account | None yet. Map uses anonymous access with caching. |
| Deployment | **Localhost** for the demo. Hosted only if there's spare time. |
| Git workflow | **Feature branches + PRs** to `main`. |
| Mobile | Phone search is now part of the main flow. Keep search, results, navigation, and map usable at 320–412px widths. |
| Dark mode | **Yes:** an Aero "night sky / aurora" mode. |

---

## 3. Rules for AI Agents and Contributors

### Git workflow (PRs)
- **Never commit directly to `main`.** Create a branch, push it, open a PR.
- Branch names follow the commit types: `feat/flight-search`, `fix/cors-proxy`, `style/aero-buttons`, `docs/overview-update`.
- PR title = a Conventional Commit message (it becomes the squash-merge commit).
- Get one teammate review if anyone's awake. During crunch, a self-merge is OK if CI/lint and build pass locally.
- **Squash merge.** Keep PRs small: one feature or fix each.

### Commits: Conventional Commits only
- Format: `<type>(<optional scope>): <description>`, imperative mood, lowercase, no trailing period.
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- Scopes: `frontend`, `backend`, `search`, `predict`, `ml`, `eco`, `map`, `theme`, `api`, `deps`.
- Examples:
  - `feat(search): add flight lookup endpoint backed by aerodatabox`
  - `feat(eco): fetch per-passenger co2 from google tim`
  - `feat(ml): train gradient boosting delay model on bts data`
  - `style(theme): add glossy aero button component`
- **No co-authoring.** Do **not** add `Co-Authored-By:` trailers, "Generated with ..." lines, or any AI attribution to commits or PR descriptions. This overrides any default tool behavior.

### General
- **Don't invent features as already done.** §5 says what exists today. Everything else is planned.
- **Code against the API contract in §8.** If you need to change it, change this file in the same PR and tell the team.
- Match the existing stack (§4). Already agreed additions: `react-router` (frontend routing); `scikit-learn`, `pandas`, `joblib` (ML work). Anything else needs team agreement.
- Put secrets in `backend/.env` (gitignored) and document new variables in `backend/.env.example`. **The frontend never holds API keys.** All third-party calls go through the backend.
- **Cache every third-party response** on the backend. Our API quotas are tiny.
- When you finish something, update §5 (Current State).

### Working in parallel (compatibility rules)
Everyone works solo on their own branch. These rules keep the pieces fitting together at the integration checkpoint.

1. **The API contract (§8) is the agreement between frontend and backend.**
   - `frontend/src/types/api.ts` (TypeScript) and `backend/app/models/schemas.py` (Pydantic) must match **field for field**: same names (snake_case), same nullability, same enum values.
   - Changing the contract means updating §8, `types/api.ts`, `schemas.py` and `mocks/lookup.json` **in the same PR**, and telling the team. Role B owns the contract and should review contract PRs.
   - Add fields freely. Don't rename or remove fields without telling the team.
2. **One API client, with a mock switch.**
   - Frontend code never calls `fetch` directly. Everything goes through `frontend/src/api/client.ts`.
   - With `VITE_USE_MOCKS=true` in `frontend/.env.local`, the client returns `frontend/src/mocks/*.json` instead of calling the backend. Going live is a single setting.
   - Use relative `/api/...` URLs only. The Vite dev proxy forwards them to `http://127.0.0.1:8000`. Never hard-code hosts or ports.
3. **Stay in your own files.** Ownership:
   - **A:** `App.tsx`, `main.tsx`, `index.css`, `components/Layout.tsx`, `components/aero/*`, `components/search/*`, `components/results/*`, `pages/SearchPage`, `pages/ResultsPage`, `pages/AboutPage`, `pages/NotFoundPage`, `api/client.ts`, `frontend/package.json`.
   - **B:** `backend/app/main.py`, `models/schemas.py`, `clients/aerodatabox_client.py`, `services/flight_lookup.py`, `services/cache.py`, `services/demo_fixtures.py`, `api/routes_flights.py`, `backend/pyproject.toml`, `backend/.env.example`.
   - **C:** `services/delay_predictor.py`, `clients/open_meteo_client.py`, `clients/faa_status_client.py`, `api/routes_predict.py`, `api/routes_airports.py`, `backend/ml/*`.
   - **D:** `services/emissions.py`, `clients/google_tim_client.py`, `clients/opensky_client.py`, `api/routes_eco.py`, `data/eco_constants.py`, `data/airports.json`, `components/eco/*`, `components/map/*`, `pages/MapPage`.
   - **Shared, small edits OK (keep them minimal):** `AGENTS.md`, `types/api.ts`, `mocks/*`.
   - If you need a change in someone else's file, ask them or keep the PR tiny and tag them.
4. **Use placeholder versions of cross-owner components.** A creates placeholder versions of `EmissionsCard` (props: `{ emissions: Emissions | null }`) and `MapPage`, so pages can include them from day one. D replaces the insides **without changing the props**. Backend routes do the same: register the route early with a placeholder response that matches the schema, then fill it in.
5. **Shared UI comes from the Aero components.** Use `GlassPanel`, `AeroButton` and the CSS custom properties in `index.css` (`var(--aero-*)`). Don't hard-code colors, and don't create your own glass or button styles. If you need a variant, add a prop or ask A.
6. **Plan for failure.** `prediction` and `emissions` can be `null`, and APIs can fail or hit rate limits. Every component handles loading, error and `null` states. Backend services catch third-party errors and return `null` (or fixtures in `DEMO_MODE`) rather than a 500 for the whole lookup.
7. **Dependencies go through the owner.**
   - Only A adds frontend packages (`npm install ...`). Only B edits `pyproject.toml` (`uv add ...`). Exception: C may `uv add` the agreed ML packages.
   - Lockfile conflicts: take `main`'s version of `package-lock.json` / `uv.lock`, then rerun `npm install` / `uv sync` and commit the result. Never hand-edit lockfiles.
   - Don't commit lockfile churn that has no dependency change behind it, such as npm flipping `"peer": true` flags.
8. **Keep in sync.**
   - Pull `main` into your branch (`git pull origin main`) at least before opening each PR.
   - Aim for PRs that are open less than about 2 hours. A small PR merged early beats a big one merged late.
9. **Check before you PR.**
   - Frontend: `npm run lint` **and** `npm run build`. The build runs the TypeScript checks, which catch contract mismatches.
   - Backend: the app starts (`uv run fastapi dev app/main.py`), and your endpoints return the documented shape at `/docs`.
10. **AI assistants:** begin sessions with "I'm Role X. Read AGENTS.md. Only edit files I own." If a task would cross ownership lines, stop and say so instead of editing.

---

## 4. Tech Stack (already set up in the repo)

| Layer | Tech | Notes |
|---|---|---|
| Frontend | React 19 + TypeScript 6 + Vite 8 | `frontend/` |
| Map | Leaflet 1.9 + react-leaflet 5 | installed, not used yet |
| Charts | Recharts 3 | installed, not used yet. Use for delay/CO2 visuals |
| Lint | oxlint | `npm run lint` |
| Backend | Python ≥ 3.14 + FastAPI | `backend/`, managed with **uv** |
| HTTP client | httpx (async) | for third-party APIs |
| Config | python-dotenv | `backend/.env` |

### Running locally
```bash
# Backend (http://127.0.0.1:8000, interactive docs at /docs)
cd backend
uv sync
uv run fastapi dev app/main.py

# Frontend (http://localhost:5173)
cd frontend
npm install
npm run dev
```
Copy `backend/.env.example` → `backend/.env` and fill in values. Add Python deps with `uv add <pkg>`, never with bare pip.

### Planned environment variables
| Var | For |
|---|---|
| `AERODATABOX_API_KEY` | RapidAPI key for AeroDataBox (flight search) |
| `GOOGLE_TIM_API_KEY` | Google Cloud key with the Travel Impact Model API enabled |
| `OPEN_METEO_BASE_URL` | already in `.env.example` |
| `OPENSKY_*` | already in `.env.example`. Unused until we get an account |
| `DEMO_MODE` | `true` = serve an offline fixture instead of calling APIs |

---

## 5. Current State (update as you go)

**Backend** (`backend/app/`)
- `main.py`: FastAPI app "FlightGuard API". CORS allows `http://localhost:5173` only.
- `GET /` and `GET /api/health` → `{"status": "ok"}`.
- `api/routes_flights.py`: `GET /api/flights/demo` returns one hard-coded demo flight.
- `GET /api/flights/lookup` accepts supported US passenger airline codes only and requires the origin or destination to be in the US. It caches successful lookups for 10 minutes and returns clear 404/422/502/503 errors. Live mode needs `AERODATABOX_API_KEY`.
- `models/schemas.py` mirrors the TypeScript lookup contract. `DEMO_MODE=true` serves the **synthetic** `DL1234`/`2026-10-11` fixture without an API key. Live lookup calls Role D's emissions service; prediction remains `null` until Role C adds its service hook below.
- `services/cache.py` provides an in-process async TTL cache with one in-flight fetch per key. Each backend process has its own cache.
- `GET /api/flights/live` serves OpenSky aircraft within the map viewport from a 60-second backend cache.
- `GET /api/flights/live/{icao24}/details` looks up flight number and origin/destination via AeroDataBox only when a plane popup opens. Results, including unavailable matches, are cached for 10 minutes per aircraft and callsign; an unconfirmed route is never guessed.

**Frontend** (`frontend/src/`)
- **Routing:** React Router v8 is set up in `main.tsx` (`BrowserRouter`) and `App.tsx`. Every route from §8 exists, inside `components/Layout.tsx` (header + nav + `<Outlet />`).
- **Pages:**
  - `SearchPage` is done: a hero panel with `FlightSearchForm` and a compact row of feature pills (`<FeatureList variant="compact" />`). It's kept light so the skyline stays visible.
  - The form validates the flight number and date with inline errors and navigates to `/flight/:number/:date`.
  - Parsing lives in `utils/flightSearch.ts`:
    - `normalizeFlightNumber` accepts `dl 1234`, `DL-1234` and `B6 623`, and returns uppercase with no spaces, or `null`.
    - It allows the same flight numbers as the backend's check in `routes_flights.py`: a 2-character IATA code plus 1–4 digits. No ICAO codes like `DAL1234` and no suffix letters. Change both together.
    - The search date range is 7 days back to 30 days ahead, set by `SEARCH_PAST_DAYS` / `SEARCH_FUTURE_DAYS`.
  - `ResultsPage` is done:
    - A compact search bar at the top, prefilled from the URL.
    - `FlightSummary`: route card with airport-local times, duration, a status badge, and the scheduled time struck through when the airline posts a new one.
    - The "Delay forecast" panel: `DelayGauge` (half-circle dial, risk badge, estimated minutes, reported-delay note) plus `ReasonList` (high impact first).
    - Role D's `EmissionsCard`, which brings its own panel, next to the delay forecast.
    - A loading orb, and a friendly message for each API error (404, 422, 502, 503, network). "Try again" only appears for 502 and network errors.
    - Empty-state copy when `prediction` or `emissions` is `null`.
    - Messy URLs (`/flight/dl-1234/...`) redirect to the clean form. Invalid flight numbers or dates in the URL show a message without calling the API.
  - `hooks/useFlightLookup.ts` wraps `lookupFlight` with loading/error/ready state and `retry()`. `utils/format.ts` has the time, date and duration formatters.
  - The Search nav tab stays highlighted on `/flight/*`.
  - `AboutPage` has an intro, full feature cards (`<FeatureList variant="cards" />`) and data credits. Model accuracy and methodology are still to come.
  - `MapPage` shows live aircraft and airports. Plane popups load the passenger flight number and route on demand, with unavailable fallbacks. `NotFoundPage` is done.
  - `components/features/FeatureList.tsx` holds the feature copy (title, text, orb color) in one place for both pages.
- **API:**
  - `api/client.ts` has `lookupFlight(number, date, signal?)`, `getLiveAircraft`, and `getLiveFlightDetails`, plus `ApiError` (with `.status`) and the `VITE_USE_MOCKS` switch (see `frontend/.env.example`).
  - **Mock test flights** (mocks only):
    - `ZZ404`, `ZZ502`, `ZZ503` return those errors.
    - `ZZ1` has `null` prediction and emissions.
    - `ZZ2` is a delayed, high-risk flight.
    - Any other number returns the sample flight.
  - Mocks vs real backend:
    - With mocks off and the backend in `DEMO_MODE=true`, only `DL1234` on `2026-10-11` exists. Everything else returns 404.
    - `.env.local` overrides `.env.example`, so to test against the real backend, set `VITE_USE_MOCKS=false` there (or prefix the command) and restart Vite.
  - `types/api.ts` mirrors the §8 contract, and `mocks/lookup.json` is a sample response.
- **Vite dev proxy:** `/api` → `http://127.0.0.1:8000`, so the frontend uses relative URLs only and CORS isn't involved in dev.
- `components/eco/EmissionsCard.tsx` (Role D) is built: cabin-class picker, kg CO2e per passenger, estimate tier, `EcoComparison`, and the source note. Props: `{ emissions: Emissions | null }`.
  - It renders **its own** `GlassPanel` and "Carbon Footprint" heading, including the `null` state. `ResultsPage` places it straight into the results grid without wrapping it.
- `config.ts` holds `APP_NAME`. `<title>` is "FlightGuard".
- **Aero theme:** done. Tokens for light and dark are in `index.css`, the shared components are in `components/aero/`, and the glass nav bar, sky background (bubbles, city skyline with control tower and wind turbines, stars and a full moon at night), theme toggle and Aero favicon are in place. Page content is centered. See §7 "Using the theme".
- Mobile layout uses a two-row header with 44px nav and theme controls, narrower panel spacing, full-width search actions, wrapped airport names and popups, and a shorter map. Touch devices use a scrolling page background and extra scroll margin for focused inputs. The date field uses `AeroDateInput`, which constrains the native picker inside the same width as the flight-number field.
- `SearchPage`, `ResultsPage`, `AboutPage` and `NotFoundPage` are wrapped in `GlassPanel`. `MapPage` has its own themed panels and map overlays.

**Known gotchas**
- OpenSky anonymous access is heavily rate-limited. Cache about 15 s and keep bounding boxes small.
- Existing `api/eco.py` reads `GOOGLE_API_KEY`, while the agreed environment variable is `GOOGLE_TIM_API_KEY`; Role D needs to reconcile this in the eco service.

---

## 6. Core Features (MVP)

### 6.1 Flight Search (home page) — data source
**Recommendation: AeroDataBox via RapidAPI.**
- Its "flight status" endpoint looks up a flight by number + date. It returns scheduled/estimated/actual times, origin/destination, status and aircraft type: everything the prediction and CO2 features need.
- **Free Basic tier (400 units/month as of October 2026)** is enough for development if we cache. Upgrade to **Pro ($8/month as of October 2026)** before the demo. **Budget approved: about $10 total.** Units ≠ requests; the single-day flight status endpoint is Tier 2. Basic requires visible AeroDataBox attribution. Check the [live pricing page](https://rapidapi.com/aedbx-aedbx/api/aerodatabox/pricing) before subscribing.
- Backup: **FlightAware AeroAPI Personal** (pay per query, with about $5/month of usage credit, max 10 result sets/min, no historical data). Better US data, but tighter limits and more setup.
- Not recommended: AviationStack (free tier is about 100 requests/month and too limited).

**Rules:** cache lookups by `(flight_number, date)` for about 10 minutes. A synthetic fixture is checked in for offline demo mode. [AeroDataBox Basic/Pro terms](https://aerodatabox.com/2026-09-terms-update) currently cap retained provider data at 7 days; any real response recorded for judging must be deleted within that window. Do not commit provider responses as permanent fixtures.

### 6.2 Delay Prediction
"Delayed" = **arrival 15+ minutes late** (the FAA/BTS standard definition).

**v1, heuristic (MVP, build first).** Score from:
- weather at origin and destination around scheduled times (Open-Meteo: gusts, precipitation, visibility, thunderstorm weather codes),
- live airport status from the **FAA NAS Status** feed (ground stops, ground delay programs; nasstatus.faa.gov),
- time of day (evening flights accumulate delays) and day of week,
- live status: if AeroDataBox already reports a later estimated time, show it as **"Reported delay"**, separate from our prediction.

Output: `risk` (low/medium/high), `probability_delayed`, `estimated_delay_minutes`, and the top `reasons[]`. The UI must always show *why*.

**v2, trained model (time permitting).**
- Data: **BTS "Reporting Carrier On-Time Performance"** monthly CSVs (free, US domestic). Use the last 12 months, or fewer if download time is a problem.
- Features: carrier, origin, destination, month, day of week, scheduled departure hour, distance.
- Model: scikit-learn `HistGradientBoostingClassifier`, which handles categoricals and trains in minutes. Optionally add a regressor for delay minutes.
- Training script: `backend/ml/train.py`. Raw CSVs go in `backend/ml/data/`, which must be **gitignored**. Output goes to `backend/app/data/delay_model.joblib`.
- At runtime, use the model's probability as the base and adjust it with live weather/FAA signals from v1. Report `"model": "bts-gbm-v1"` vs `"heuristic-v1"`.
- Show a simple accuracy number (e.g. AUC on a held-out month) on an "About our model" section. Judges like it.

### 6.3 CO2 per Flight (eco feature) — Google Travel Impact Model
- Endpoint: `POST https://travelimpactmodel.googleapis.com/v1/flights:computeFlightEmissions`
- Request per leg: origin, destination, operating carrier code, flight number, departure date (all available from the flight search).
- Returns **grams CO2e per passenger by cabin class** (economy, premium economy, business, first). Convert to kg for display.
- TIM uses a **fallback cascade**: an exact-flight estimate first, then the typical estimate for the route that year, then a distance-based estimate. Store and display which tier was used (`estimate_tier`).
- Gotchas: past flight dates, and some future dates, fall back to route-typical estimates. Flights outside the current calendar year can come back **empty**. If TIM returns nothing, use a simple fallback: `great_circle_km × ~0.09 kg CO2/pax-km`, labeled "rough estimate".
- Display: per-passenger kg for the selected cabin, plus **relatable comparisons** ("= X km in a gas car", "= X days of an average American's emissions", "= X trees absorbing CO2 for a year"). Keep comparison constants in one file with source comments.
- Always label values as **estimates** and credit "Google Travel Impact Model".

### 6.4 Map Tab (secondary)
- Leaflet map with live aircraft from OpenSky (anonymous), filtered to the viewport within the US. Markers are rotated by heading. Poll about every 15 s via the backend cache.
- Airports from the free **OurAirports** dataset, filtered to US `large_airport` / `medium_airport`, stored as a trimmed JSON in `backend/app/data/airports.json`.
- Click an airport → its weather + FAA status + delay risk (reuses prediction services).
- Stretch: highlight the searched flight's route as a great-circle arc. If its `icao24` is known, show the live plane.
- Tiles: light, airy (e.g. CARTO Voyager/Positron with attribution). Dark mode uses a dark tile variant.

---

## 7. Frutiger Aero Theme Guide

**Vibe:** Windows Vista/7, early iPod/iTunes, Wii, aquariums, clean energy ads. Optimistic, glossy, airy, natural tech.

| Element | Guidance |
|---|---|
| Colors (light) | Sky blue → white gradients, aqua/teal, fresh lime/leaf green, white highlights. |
| Colors (dark) | **Night sky with aurora**: deep navy → indigo gradients, teal/green aurora glows, star specks. Never flat black. |
| Glass | Translucent panels: `backdrop-filter: blur()`, semi-transparent white (dark mode: semi-transparent navy), thin bright border, soft shadow. |
| Gloss | Gel buttons and pills with a top-half white→transparent highlight, rounded shapes. |
| Motifs | Bubbles, water droplets, lens flares, clouds, leaves, grass, light rays, aurora swooshes. |
| Typography | Frutiger and Segoe UI are licensed, so use the system `Segoe UI` stack with free fallbacks (Nunito, Open Sans). |
| Icons | Glossy, rounded, slightly 3D. Eco stats use leaf/droplet icons. |
| Motion | Floating bubbles, soft fades, shine sweep on hover. Respect `prefers-reduced-motion`. |

**Eco tie-in:** low-CO2 flights get a green leaf glow, high-CO2 an amber tint. Delay risk uses aqua (low) → amber → coral (high), never harsh red.

### Using the theme (built, in `frontend/src`)
**How theming works**
- The theme lives on `<html data-theme="light|dark">`. An inline script in `index.html` sets it before first paint, from `localStorage["theme"]` or the OS setting. `ThemeToggle` switches it and saves the choice.
- Styling for dark mode means **overriding tokens** under `:root[data-theme='dark']` (or `:root[data-theme='dark'] .your-class`). Never use `@media (prefers-color-scheme)` in components.

**Tokens** (`index.css`, always `var(--aero-*)`)

| Group | Tokens |
|---|---|
| Text | `--aero-text`, `--aero-text-muted`, `--aero-heading`, `--aero-heading-glow`, `--aero-link` |
| Palette | `--aero-accent`, `--aero-accent-strong`, `--aero-leaf`, `--aero-amber`, `--aero-coral` |
| Delay risk | `--aero-risk-low` / `-medium` / `-high` |
| Eco | `--aero-eco-low` (green), `--aero-eco-high` (amber) |
| Glass | `--aero-glass-bg`, `--aero-glass-strong`, `--aero-glass-border`, `--aero-glass-inner`, `--aero-gloss`, `--aero-shadow`, `--aero-blur` |
| Shape | `--aero-radius-sm` / `-md` / `-lg` / `-pill` |
| Focus | `--aero-focus` (box-shadow ring) |
| Gel | `--aero-gel-primary-*`, `--aero-gel-eco-*` (`-top`, `-bottom`, `-border`, `-glow`) |

**Components** (`components/aero/`)
- `<GlassPanel as="section" className="...">`: frosted card, the base for every panel. `as` can be `div` (default), `section`, `article`, `aside`, `header` or `footer`. Accepts all div props. Adjacent panels get a 20px gap automatically.
- `<AeroButton variant="primary|eco|glass" size="md|lg">`: glossy gel button with all normal button props. `type` defaults to `"button"`. Use `eco` (green) for eco actions.
- `<AeroInput>`: glassy pill text input that takes all normal input props. Set `aria-invalid={true}` to show the coral error border. Pair it with a `<label htmlFor>`.
- `<AeroDateInput>`: glassy date field with a constrained native date picker. It takes normal date input props, including `aria-invalid`, and also needs a `<label htmlFor>`.
- `aeroButtonClass(variant?, size?, className?)` from `components/aero/classes.ts`: use this to style a **link** as an Aero button, e.g. `<Link className={aeroButtonClass("primary", "lg")}>`. `cx(...)` from the same file joins class names.
- `<SkyBackground />` and `<ThemeToggle />` are already rendered by `Layout`. Don't add them again.
  - `SkyBackground` is the fixed decorative scene behind everything: stars, the full moon (night only), `Skyline` (SVG city, control tower and wind turbines along the bottom) and rising bubbles.
  - Its colors come from the `--aero-skyline-*`, `--aero-moon-opacity`, `--aero-beacon-opacity`, `--aero-stars-opacity` and `--aero-bubble-opacity` tokens.
- `.app-main` centers text (`text-align: center`). Set `text-align: left` on anything that reads better left-aligned, such as lists, tables and long paragraphs.
- `<AeroBadge tone="sky|aqua|leaf|amber|coral|muted">`: small glossy pill for statuses, delay risk, an eco score and so on. Amber uses dark text for contrast.
- Utility classes: `.text-muted`, and `.visually-hidden` (hidden on screen, still read by screen readers).

**Gotchas**
- When writing `backdrop-filter` with a `-webkit-` prefix, put the **prefixed line first**. The build minifier keeps only the last of the pair, and Chrome/Edge ignore the prefixed version. Dev mode won't show the problem.
- Respect `prefers-reduced-motion` for any animation.

---

## 8. Architecture and API Contract

> Agree on this contract in hour 1. Then everyone builds against it in parallel. Frontend uses mock JSON until the backend is ready.

### Endpoints
| Method | Path | Owner | Returns |
|---|---|---|---|
| GET | `/api/flights/lookup?number=DL1234&date=2026-10-11` | Backend | `FlightLookupResponse` (below): the main search call |
| GET | `/api/predict?number=...&date=...` | Prediction | `DelayPrediction` |
| GET | `/api/eco/emissions?carrier=DL&number=1234&origin=RDU&destination=ATL&date=...` | Eco | `Emissions` |
| GET | `/api/flights/live?lamin&lamax&lomin&lomax` | Eco/Map | live aircraft (cached) |
| GET | `/api/flights/live/{icao24}/details?callsign=DAL214` | Eco/Map | `LiveFlightDetails` (below), fetched on popup open |
| GET | `/api/airports` | Eco/Map | trimmed US airport list |
| GET | `/api/airports/{iata}` | Prediction | weather + FAA status + risk |

`/api/flights/lookup` calls the flight client and then the prediction and emissions services. The frontend makes **one call** for the results page.

`LiveFlightDetails` has `flight_number`, `origin`, and `destination`, each a nullable string. For example: `{ "flight_number": "DL214", "origin": "ATL — Hartsfield-Jackson Atlanta International Airport", "destination": "FCO — Leonardo da Vinci International Airport" }`. When the provider cannot confirm that an active flight matches both the aircraft and callsign, all three fields are `null`. The map keeps altitude, speed, and heading from OpenSky without a details lookup until the popup opens.

**Backend service hooks:** Role C exposes `async predict_delay(flight: Flight) -> DelayPrediction | None` in `services/delay_predictor.py`. Role D exposes `async get_emissions_for_flight(flight: Flight) -> Emissions | None` in `services/emissions.py`. The lookup route calls either when its module exists; a failure in one service yields `null` for that field.

### `FlightLookupResponse` (shape to match in Pydantic `models/` and TS `types/`)
```json
{
  "flight": {
    "number": "DL1234",
    "airline": { "iata": "DL", "name": "Delta Air Lines" },
    "date": "2026-10-11",
    "origin":      { "iata": "RDU", "name": "Raleigh-Durham Intl", "lat": 35.88, "lon": -78.79 },
    "destination": { "iata": "ATL", "name": "Hartsfield-Jackson Atlanta Intl", "lat": 33.64, "lon": -84.43 },
    "scheduled_departure": "2026-10-11T14:05:00-04:00",
    "scheduled_arrival":   "2026-10-11T15:40:00-04:00",
    "estimated_departure": null,
    "actual_departure": null,
    "status": "scheduled",
    "aircraft_type": "B739",
    "icao24": null
  },
  "prediction": {
    "risk": "medium",
    "probability_delayed": 0.38,
    "estimated_delay_minutes": 17,
    "reported_delay_minutes": null,
    "reasons": [
      { "factor": "weather_destination", "detail": "Thunderstorms forecast at ATL around arrival", "impact": "high" },
      { "factor": "time_of_day", "detail": "Afternoon departures run later on average", "impact": "low" }
    ],
    "model": "heuristic-v1"
  },
  "emissions": {
    "co2e_kg_per_passenger": { "economy": 92.1, "premium_economy": 138.2, "business": 184.2, "first": 276.3 },
    "estimate_tier": "flight",
    "source": "google_tim",
    "comparisons": [
      { "label": "km in an average gas car", "value": 230 }
    ]
  }
}
```
- `status`: `scheduled | delayed | departed | en_route | landed | cancelled | unknown`
- `risk`: `low | medium | high`. `impact`: `low | medium | high`
- `estimate_tier`: `flight | route | distance | fallback`
- `prediction` and `emissions` can be `null` if that service fails. The UI must handle this gracefully.

### Backend layout
```
backend/app/
  main.py
  api/       routes_flights.py, routes_predict.py, routes_eco.py, routes_airports.py
  clients/   aerodatabox_client.py, google_tim_client.py, open_meteo_client.py,
             faa_status_client.py, opensky_client.py      # thin wrappers, no logic
  services/  flight_lookup.py, delay_predictor.py, emissions.py, cache.py, demo_fixtures.py
  models/    schemas.py                                   # Pydantic models for the contract above
  data/      airports.json, delay_model.joblib, eco_constants.py, fixtures/
backend/ml/  train.py, data/ (gitignored)
```

### Frontend layout
```
frontend/src/
  api/client.ts            # typed fetch helpers, relative /api URLs
  types/api.ts             # TS mirror of the contract
  pages/SearchPage.tsx, ResultsPage.tsx, MapPage.tsx, AboutPage.tsx, NotFoundPage.tsx
  components/Layout.tsx    # glass nav + ThemeToggle + <Outlet />
  components/
    search/FlightSearchForm.tsx          # utils/flightSearch.ts holds the parsing/date helpers
    results/FlightSummary.tsx, DelayGauge.tsx, ReasonList.tsx
    eco/EmissionsCard.tsx, EcoComparison.tsx
    map/FlightMap.tsx, PlaneMarker.tsx, AirportMarker.tsx
    aero/GlassPanel.tsx, AeroButton.tsx, SkyBackground.tsx, Skyline.tsx, ThemeToggle.tsx
  mocks/lookup.json        # sample FlightLookupResponse for building UI before the backend is ready
```
### Routes (React Router)
| Path | Page | Notes |
|---|---|---|
| `/` | `SearchPage` | Home: flight number + date form |
| `/flight/:number/:date` | `ResultsPage` | e.g. `/flight/DL1234/2026-10-11`. Shareable and bookmarkable. Reads params, calls `/api/flights/lookup` |
| `/map` | `MapPage` | Live planes + airports |
| `/about` | `AboutPage` | How prediction and CO2 work, model accuracy, data credits |
| `*` | `NotFoundPage` | Friendly Aero-styled 404 |

- Installed as `react-router` v8 (requires Node ≥ 22.22). There is no `react-router-dom` package anymore. Import everything from `react-router`. Official docs ship locally in `node_modules/react-router/docs/`.
- Put routes in `src/App.tsx` inside a shared `Layout` component: glass nav bar (Search · Map · About) + `ThemeToggle` + `<Outlet />`.
- Use `<NavLink>` for nav tabs so the active tab gets a glossy "selected" style.
- The search form navigates with `useNavigate()` to `/flight/:number/:date`. Normalize the number to uppercase with no spaces.
- Vite dev server handles client-side routes already. If we host later, the host needs an SPA fallback to `index.html`.

---

## 9. Team Split (4 people)

The team has assigned these roles. Fill in the Owner column so AI agents know who to defer to.

| Role | Owner | Owns | MVP deliverables | Stretch |
|---|---|---|---|---|
| **A — Frontend and Aero Theme** | _TBD_ | `frontend/` UI, design system, pages | Vite proxy fix; React Router setup (`Layout`, routes, nav); design tokens (light and dark); `GlassPanel`/`AeroButton`/`SkyBackground`/`ThemeToggle`; Search page; Results page rendering `FlightLookupResponse` from mocks, then the real API; loading/error/empty states | Sounds/music toggle, animated sky, splash screen, mobile layout |
| **B — Flight Data and Backend Core** | _TBD_ | `clients/aerodatabox_client.py`, `services/flight_lookup.py`, `cache.py`, `models/schemas.py`, demo mode | Pydantic schemas for the contract; AeroDataBox client; `/api/flights/lookup` (combines prediction and emissions); TTL cache; offline fixture + `DEMO_MODE`; `.env.example` updates | "Recent searches", hosting/deploy |
| **C — Delay Prediction and ML** | _TBD_ | `services/delay_predictor.py`, weather/FAA clients, `backend/ml/` | Open-Meteo + FAA NAS clients; heuristic v1 with reasons; `/api/predict`; `/api/airports/{iata}` | **BTS model v2** (`ml/train.py`, joblib model, blended prediction), accuracy stat for the About page, historical delay chart data |
| **D — Eco and Map** | _TBD_ | `services/emissions.py`, TIM client, eco UI, map tab | Google TIM client + fallback; `/api/eco/emissions`; comparison constants; `EmissionsCard` + `EcoComparison` UI; Map tab with OpenSky live planes + airports | Route arc on map, eco score badge, greener alternatives (train/car), "delay carbon cost" |

Pairing: A ↔ D share the eco UI components and theme. B ↔ C agree on how lookup calls the predictor. B owns the contract; anyone changing it pings B. File ownership and the rules for working in parallel are in §3 ("Working in parallel").

### Timeline (22 h, relative to start)
| Hours | Goal |
|---|---|
| **0–1** | Everyone together: claim roles, everyone gets the app running, agree on the §8 contract, B commits schemas + A commits `mocks/lookup.json`, sign up for AeroDataBox + Google Cloud (TIM) keys. |
| **1–7** | Parallel MVP build against mocks. A: theme + search/results UI. B: lookup endpoint. C: heuristic predictor. D: TIM + eco card + basic map. |
| **7–9** | **Integration checkpoint:** a real search → results page with prediction + CO2 working end to end on `main`. Record demo fixtures. |
| **9–15** | **Sleep** (stagger if someone is mid-task, but everyone gets a real block). Optionally leave the BTS download/training running overnight. |
| **15–19** | Stretch features by priority: (1) BTS model, (2) dark-mode polish, (3) map polish + route arc, (4) eco extras, (5) music/sounds. |
| **19** | **Feature freeze.** Bug fixes only after this. |
| **19–22** | Demo prep: test with `DEMO_MODE=true`, write README + Devpost, record a backup demo video, rehearse the pitch. |

---

## 10. Feature Ideas Backlog (post-MVP)

**Eco**
- **"Delay carbon cost":** extra fuel burned holding or taxiing during a delay. Connects the two main features directly.
- **Greener alternatives:** for short routes (< ~500 km), compare against train, bus, car or EV.
- **Eco score badge** (A–F) on the results page, also shown as a marker glow on the map.
- **Airline comparison** on the same route: TIM can estimate several flights in one request.
- **Offset explainer** with honest caveats about offsets.

**Prediction / tracking**
- "My flights" saved in `localStorage` with a status refresh.
- Airport departure board styled like a glossy Vista sidebar gadget.
- Historical delay heatmap by hour/day from BTS data (Recharts).
- Weather radar overlay on the map.

**Theme / fun**
- **Ambient music toggle:** chill Aero-style background music. Start it on a user click (browsers block autoplay). Royalty-free tracks only.
- UI sounds: bubble pop on click, soft chime when results load.
- Sky gradient that follows the origin airport's local time.
- Startup splash with an Aero boot animation.

---

## 11. Open Questions

1. **Name:** team to decide later. Ideas: *AeroSky*, *SkyBubble*, *Cloudline*, *GreenGlide*, *Delayr Aero*.
