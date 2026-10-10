# Role C Spec: Delay Prediction and ML

> Working spec for Role C. `AGENTS.md` is the source of truth: if anything here changes the API contract (§8), update `AGENTS.md`, `schemas.py`, `types/api.ts` and `mocks/lookup.json` in the same PR and ping B.
>
> Field names marked **(verify)** are from memory. Hit each endpoint once and save the real response as a fixture before coding against it.

## 0. Repo notes before starting
- `models/schemas.py` doesn't exist yet (B owns it). Code against the §8 shapes and swap in B's models when they land.
- `/api/airports/{iata}` has no response shape in §8 yet. See the proposal in §4.3 and agree it with B.

## 1. Goal and definition
- **Delayed** means the flight arrives 15 or more minutes late (the BTS `ArrDel15` definition).
- For any flight, return a `DelayPrediction`: `risk`, `probability_delayed`, `estimated_delay_minutes`, `reported_delay_minutes`, `reasons[]` and `model`.
- The UI must always be able to show *why*.
- **MVP:** heuristic v1, `/api/predict`, `/api/airports/{iata}`.
- **Stretch:** BTS model v2, an accuracy number for the About page, historical chart data.

## 2. Files you own
| File | Purpose |
|---|---|
| `app/clients/open_meteo_client.py` | Thin wrapper that returns raw JSON. No logic. |
| `app/clients/faa_status_client.py` | Fetches and parses the FAA XML into dicts. No scoring. |
| `app/services/delay_predictor.py` | All scoring logic. The heuristic and the model blend live here. |
| `app/api/routes_predict.py` | `GET /api/predict` |
| `app/api/routes_airports.py` | `GET /api/airports/{iata}` (D owns `GET /api/airports`, the list route) |
| `backend/ml/*` | `train.py`, `data/` (gitignored) |

## 3. Data sources

| Source | Kind | Key | Used for |
|---|---|---|---|
| Open-Meteo | Live | None | Weather at origin and destination |
| FAA NAS Status | Live | None | Ground stops, ground delay programs, closures |
| AeroDataBox | Live, through Role B | B's | Flight details, reported delay |
| BTS On-Time Performance | Offline CSVs | None | Training the v2 model |

### 3.1 Open-Meteo Forecast API (weather)
- **Request:** `GET https://api.open-meteo.com/v1/forecast` (already set as `OPEN_METEO_BASE_URL`)
- **Auth and limits:** no key. Roughly 10,000 calls/day for non-commercial use.
- **Range:** about 16 days ahead. Past dates in the forecast window return recent data.

Suggested parameters:
```
latitude=35.88&longitude=-78.79
hourly=weather_code,precipitation,precipitation_probability,visibility,wind_speed_10m,wind_gusts_10m,cloud_cover,temperature_2m
wind_speed_unit=kn
timezone=GMT
start_date=2026-10-11&end_date=2026-10-11
```
- Comma-separated latitudes and longitudes let you fetch origin and destination in **one call**. The response is then a list.
- Use `timezone=GMT` so you can match hours against the flight's scheduled times converted to UTC.

What you get back:
```json
{
  "latitude": 35.875, "longitude": -78.79, "timezone": "GMT", "utc_offset_seconds": 0,
  "hourly_units": { "wind_gusts_10m": "kn", "visibility": "m", "precipitation": "mm" },
  "hourly": {
    "time": ["2026-10-11T00:00", "2026-10-11T01:00"],
    "weather_code": [3, 61],
    "precipitation": [0.0, 1.2],
    "precipitation_probability": [10, 70],
    "visibility": [24140, 8000],
    "wind_speed_10m": [8.2, 9.0],
    "wind_gusts_10m": [15.1, 18.4]
  }
}
```
The hourly values are parallel arrays indexed by `time`. Pick the hour nearest scheduled departure (at the origin) and scheduled arrival (at the destination).

WMO weather codes that matter:
| Code | Meaning | Delay signal |
|---|---|---|
| 95, 96, 99 | Thunderstorm (96 and 99 with hail) | **High.** The biggest single cause of US delays. |
| 71–77, 85–86 | Snow, snow showers | High (de-icing) |
| 56–57, 66–67 | Freezing drizzle or rain | High |
| 45, 48 | Fog, rime fog | Medium (also check `visibility` < 1600 m, about 1 statute mile) |
| 63–65, 81–82 | Moderate to heavy rain or showers | Low to medium |

- **Cache** by `(round(lat,2), round(lon,2), date)` for about 30–60 minutes.
- **Stretch:** the archive API (`https://archive-api.open-meteo.com/v1/archive`) has the same parameters for past dates. It's only useful if you add weather features to the v2 model.

### 3.2 FAA NAS Status (live airport programs)
- **Request:** `GET https://nasstatus.faa.gov/api/airport-status-information`
- **Auth:** no key.
- **Format:** **XML**. Parse it with the standard library's `xml.etree.ElementTree`, so no new dependency.
- One document covers the whole US National Airspace System.
- **Only airports with an active event appear.** If an airport isn't listed, treat it as normal.

Structure **(verify)** against a live response:
```xml
<AIRPORT_STATUS_INFORMATION>
  <Update_Time>Sat Oct 10 19:45:00 2026 GMT</Update_Time>
  <Delay_type>
    <Name>Ground Stop Programs</Name>
    <Ground_Stop_List><Program><ARPT>ATL</ARPT><Reason>thunderstorms</Reason><End_Time>8:30 pm EDT</End_Time></Program></Ground_Stop_List>
  </Delay_type>
  <Delay_type>
    <Name>Ground Delay Programs</Name>
    <Ground_Delay_List><Ground_Delay><ARPT>SFO</ARPT><Reason>low ceilings</Reason><Avg>1 hour and 12 minutes</Avg><Max>2 hours and 5 minutes</Max></Ground_Delay></Ground_Delay_List>
  </Delay_type>
  <Delay_type>
    <Name>General Arrival/Departure Delay Info</Name>
    <Arrival_Departure_Delay_List><Delay><ARPT>ORD</ARPT><Reason>WX:Thunderstorms</Reason>
      <Arrival_Departure Type="Departure"><Min>31 minutes</Min><Max>45 minutes</Max><Trend>Increasing</Trend></Arrival_Departure>
    </Delay></Arrival_Departure_Delay_List>
  </Delay_type>
  <Delay_type>
    <Name>Airport Closures</Name>
    <Airport_Closure_List><Airport><ARPT>...</ARPT><Reason>...</Reason><Start>...</Start><Reopen>...</Reopen></Airport></Airport_Closure_List>
  </Delay_type>
</AIRPORT_STATUS_INFORMATION>
```
- **Client output:** `dict[str, list[FaaEvent]]` keyed by airport code. Each event has `type` (`ground_stop | ground_delay | general_delay | closure`), `reason`, `avg_minutes`, `max_minutes` and `end_time`.
- Write a small parser that turns strings like "1 hour and 12 minutes" into a number of minutes.
- `ARPT` is the FAA code, which equals the IATA code for nearly all major US airports.
- **Live data only, no forecast.** Only apply it when departure is within about 6 hours. Otherwise skip it and add no reason.
- **Cache** the whole document for about 2–5 minutes. One fetch serves every airport.
- **Testing:** on a calm day the lists will be empty. Save a real XML response from a stormy day (or hand-write one) as a fixture.

### 3.3 AeroDataBox (flight details, consumed through Role B)
You don't call it directly. B's `flight_lookup` gives you the §8 `flight` object. The fields you need:

| Field | Used for |
|---|---|
| `airline.iata`, `number` | v2 model features (carrier), flight-level history |
| `origin` / `destination` `.iata`, `.lat`, `.lon` | Weather location, FAA lookup, model features |
| `scheduled_departure`, `scheduled_arrival` (ISO with offset) | Weather hour, time-of-day factor, day of week, month, model features |
| `estimated_departure`, `status` | **`reported_delay_minutes`** = estimated − scheduled. Shown separately from the prediction. |

- **Ask B to add:** `distance_km` (AeroDataBox returns `greatCircleDistance.km`) and `estimated_arrival`. Both feed the model.
- **Optional (verify the cost in units):** AeroDataBox also has airport-delay and flight-delay-statistics endpoints. They'd be strong signals, but they spend B's quota. Only use them with B's agreement.

### 3.4 BTS On-Time Performance (offline training data, v2)
- **Download:** `https://www.transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{YYYY}_{M}.zip`
- Each month is about 25 MB zipped and about 500–600k rows. The data lags about 2–3 months behind today.
- Save to `backend/ml/data/`, and add that folder to `.gitignore`.

Columns to keep:
| Column | Use |
|---|---|
| `FlightDate`, `Month`, `DayOfWeek` | Features |
| `Reporting_Airline` | Feature (carrier) |
| `Flight_Number_Reporting_Airline` | Flight-level history table |
| `Origin`, `Dest` | Categorical features |
| `CRSDepTime` (local hhmm) → dep hour | Feature |
| `Distance` (miles) | Feature |
| `ArrDel15` | **Target** |
| `ArrDelayMinutes` | Optional regression target |
| `Cancelled`, `Diverted` | Drop these rows (`ArrDel15` is null) |
| `CarrierDelay`, `WeatherDelay`, `NASDelay`, `LateAircraftDelay` | Explanatory stats per route or airport for `reasons[]` and charts |

**Carrier mismatch:** BTS reports the *operating* carrier. Regional flights sold as DL, AA or UA are operated by 9E, OO, YX, MQ and others. A searched `DL1234` may not match in BTS. Unknown carriers fall back to "unknown" (the gradient-boosting model handles that). Don't burn time on a perfect mapping.

## 4. Interfaces

### 4.1 Service function (agree with B)
```python
# app/services/delay_predictor.py
async def predict_delay(flight: Flight) -> DelayPrediction | None
async def airport_status(iata: str) -> AirportStatus | None
```
- B's `/api/flights/lookup` calls `predict_delay(flight)`.
- `/api/predict?number&date` calls B's flight lookup to get the `Flight`, then calls `predict_delay`. Agree with B on a lookup function that skips prediction, so the two don't call each other in a loop.
- Never raise past this layer. Catch the error, log it, and return `None`. In `DEMO_MODE`, return a fixture.

### 4.2 `DelayPrediction` (from §8, unchanged)
Propose these `factor` values to B so the frontend can show icons:
`weather_origin`, `weather_destination`, `faa_origin`, `faa_destination`, `time_of_day`, `day_of_week`, `season`, `historical_route`, `reported_delay`.

### 4.3 Proposed `AirportStatus` for `GET /api/airports/{iata}`
This needs to be added to §8, and `schemas.py` updated in the same PR.
```json
{
  "iata": "ATL",
  "name": "Hartsfield-Jackson Atlanta Intl",
  "weather": { "time": "2026-10-11T19:00Z", "weather_code": 95, "description": "Thunderstorm",
               "wind_gusts_kt": 32, "visibility_m": 4000, "precipitation_mm": 6.1 },
  "faa_events": [ { "type": "ground_delay", "reason": "thunderstorms", "avg_minutes": 72, "max_minutes": 125 } ],
  "risk": "high",
  "reasons": [ { "factor": "faa_origin", "detail": "Ground delay program at ATL (avg 72 min)", "impact": "high" } ]
}
```
- Airport name and coordinates come from D's `data/airports.json`.
- Until D's file exists, hard-code about 10 demo airports.

## 5. Heuristic v1 (build first, done by about hour 6)
- Work in **log-odds**, so the contributions add cleanly and the result stays within 0–1.
- The base rate is about 20%, roughly the US share of arrivals 15+ minutes late, so start at logit(0.20) ≈ −1.39.

| Signal | Condition | Δ log-odds | Impact |
|---|---|---|---|
| FAA (origin or destination) | Ground stop or closure | +2.5 | high |
| | Ground delay program | +1.5 (+ avg_min/60) | high |
| | General delay > 30 min | +0.8 | medium |
| Weather (at origin around departure, at destination around arrival) | Thunderstorm code 95–99 | +1.5 | high |
| | Snow, freezing precipitation | +1.2 | high |
| | Gusts ≥ 35 kt | +0.8 | medium |
| | Visibility < 1600 m or fog | +0.7 | medium |
| | Heavy rain | +0.4 | low |
| Time of day (local departure hour) | 17:00–21:59 | +0.5 | low |
| | Before 09:00 | −0.4 | low |
| Day / season | Fri/Sun, or Jun–Aug, or Dec holidays | +0.2 | low |

- `probability = sigmoid(sum)`
- **Risk:** low if probability < 0.25, medium if < 0.50, otherwise high.
- `estimated_delay_minutes = round(probability × 45)`, or the FAA average delay if larger. It's a rough number; label it an estimate.
- `reasons` = the top 3 contributions by size, plus a calm "No weather or airport issues expected" if none apply.
- If departure is more than 16 days out, there's no weather. Add a reason saying so, and use time-of-day factors only.
- `model: "heuristic-v1"`

## 6. Model v2 (stretch, start the download before sleeping)
1. **`ml/train.py`:** load the last 3–12 monthly CSVs and keep the columns above. Drop cancelled and diverted rows.
2. **Features:** carrier, origin, dest (categorical), month, day of week, dep_hour, distance.
3. **Model:** `HistGradientBoostingClassifier(categorical_features=[...])`. Split by time: train on months 1..N−1 and test on month N.
4. **Report:** test AUC and the base rate. Write them to `app/data/model_meta.json` for the About page.
5. **Save:** `joblib.dump({"model", "categories", "meta"}, "app/data/delay_model.joblib")`.
6. **Extra lookup table:** `app/data/route_stats.json` with the historical delay rate and dominant delay cause per origin–dest pair and per departure hour. It feeds both `reasons` ("Historically 27% of RDU→ATL flights arrive late") and the Recharts chart.
7. **At runtime:**
   - Load the model once at startup. If it's missing, fall back to the heuristic.
   - Start from `logit(model_prob)`, then add the live FAA and weather deltas from §5. Skip the time-of-day and season rows, since the model already covers those.
   - Report `model: "bts-gbm-v1"`.

## 7. Caching, config, failure handling
- **TTL cache:** use B's `services/cache.py` once it exists. Until then, use a small in-module dict. Open-Meteo 30–60 min, FAA 3 min, predictions 5 min keyed by `(number, date)`.
- **Env vars:** none new besides `OPEN_METEO_BASE_URL`. Optionally add `FAA_NAS_URL` and ask B to add it to `.env.example`.
- **Failures:**
  - Weather fails: skip the weather factors and still return a prediction.
  - FAA fails: skip the FAA factors.
  - Both fail: return time-of-day factors only.
  - Return `None` only if the flight itself is missing.
- **Fixtures:** record one real Open-Meteo JSON and one FAA XML (from a stormy day) into `app/data/fixtures/` for `DEMO_MODE`.

## 8. Task checklist (in order)
| # | Task | Done when |
|---|---|---|
| 1 | Branch, rename the file, register stub routes returning a hard-coded `DelayPrediction` | `/docs` shows both routes with the correct shape |
| 2 | Open-Meteo client + fixture | Returns hourly data for RDU and ATL in one call |
| 3 | FAA client + XML parser + fixture | Parses the fixture into the event dict |
| 4 | Heuristic in `delay_predictor.py` | Unit-check: a stormy fixture gives high risk, a calm one gives low |
| 5 | Wire `/api/predict` and `/api/airports/{iata}`, hand `predict_delay` to B | Real search returns a prediction (integration checkpoint, hours 7–9) |
| 6 | Start the BTS download and training overnight | `delay_model.joblib` and `model_meta.json` exist |
| 7 | Blend the model, add route stats and chart data | `model: "bts-gbm-v1"` in responses, AUC on the About page |
| 8 | Update `AGENTS.md` §5 | — |

## 9. Open questions for the team
1. **B:** add `distance_km` and `estimated_arrival` to `flight`? Also, which flight lookup function should `/api/predict` call so the two services don't call each other in a loop?
2. **B:** approve the `AirportStatus` schema and the `factor` enum.
3. **D:** when will `airports.json` land, and with which fields (`iata`, `name`, `lat`, `lon`, `tz`)?
4. **A:** do you want chart data such as `hourly_delay_rate[]` on the results page or only on About?
