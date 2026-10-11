"""Delay prediction: BTS model when it is trained, heuristic otherwise.

Scores in log-odds so live weather and FAA programs shift the probability
without pushing it outside 0–1. With ``delay_model.joblib`` present, the
base rate comes from the model (carrier, route, month, weekday, hour,
distance). Only weather and FAA are added on top. Without the file, the
heuristic starts at the US base rate and adds a small schedule adjustment.

`predict_delay` is what flight lookup calls. It returns None only when the
flight itself is missing or unusable. A failed weather or FAA fetch still
produces a prediction.
"""

import json
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import cache
from pathlib import Path
from zoneinfo import ZoneInfo

import joblib
from pydantic import BaseModel, ValidationError

from app.clients.faa_status_client import get_airport_events
from app.clients.open_meteo_client import get_forecast
from app.models.schemas import ModelInfo
from app.services.cache import TTLCache
from app.services.prediction_models import (
    AirportStatus,
    AirportWeather,
    DelayPrediction,
    DelayReason,
    FaaEventModel,
    Flight,
)

logger = logging.getLogger(__name__)

# US arrivals are late (15+ minutes) about 20% of the time.
BASE_RATE = 0.20
BASE_LOG_ODDS = math.log(BASE_RATE / (1 - BASE_RATE))
# A flat +0.5 from 5–10 pm scored every calm evening near 29% (medium).
# The real gap over the daytime base is a few points, larger after 7 pm
# as inbound delays stack. These stay under the 25% medium cutoff on a
# calm weekday; Friday and summer still add their own small bump.
EARLY_DELTA = -0.4
EARLY_EVENING_DELTA = 0.12  # 17:00–18:59 local → about 22%
LATE_EVENING_DELTA = 0.20  # 19:00–21:59 local → about 23%
DAY_SEASON_DELTA = 0.2
PREDICTION_TTL_SECONDS = 5 * 60
AIRPORT_TTL_SECONDS = 3 * 60
FAA_WINDOW = timedelta(hours=6)
FORECAST_LIMIT = timedelta(days=16)
MODEL_NAME = "bts-gbm-v1"
HEURISTIC_NAME = "heuristic-v1"
# Typical minutes late when a ground stop or airline-affecting closure
# is active and the feed does not publish an average.
GROUND_STOP_MINUTES = 60
CLOSURE_MINUTES = 90

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
AIRPORTS_FILE = DATA_DIR / "airports.json"
MODEL_PATH = DATA_DIR / "delay_model.joblib"
ROUTE_STATS_PATH = DATA_DIR / "route_stats.json"
MODEL_META_PATH = DATA_DIR / "model_meta.json"

CAUSE_PHRASE = {
    "carrier": "the airline",
    "weather": "weather",
    "nas": "air traffic",
    "late_aircraft": "a late incoming aircraft",
}

# Hubs with checked time zones. airports.json has no `tz` field; every
# other US airport's zone is estimated from coordinates.
DEMO_AIRPORTS: dict[str, dict[str, str | float]] = {
    "ATL": {
        "name": "Hartsfield-Jackson Atlanta Intl",
        "lat": 33.64,
        "lon": -84.43,
        "tz": "America/New_York",
    },
    "RDU": {
        "name": "Raleigh-Durham Intl",
        "lat": 35.88,
        "lon": -78.79,
        "tz": "America/New_York",
    },
    "ORD": {
        "name": "Chicago O'Hare Intl",
        "lat": 41.97,
        "lon": -87.91,
        "tz": "America/Chicago",
    },
    "DFW": {
        "name": "Dallas/Fort Worth Intl",
        "lat": 32.90,
        "lon": -97.04,
        "tz": "America/Chicago",
    },
    "DEN": {
        "name": "Denver Intl",
        "lat": 39.86,
        "lon": -104.67,
        "tz": "America/Denver",
    },
    "LAX": {
        "name": "Los Angeles Intl",
        "lat": 33.94,
        "lon": -118.41,
        "tz": "America/Los_Angeles",
    },
    "JFK": {
        "name": "John F. Kennedy Intl",
        "lat": 40.64,
        "lon": -73.78,
        "tz": "America/New_York",
    },
    "SFO": {
        "name": "San Francisco Intl",
        "lat": 37.62,
        "lon": -122.38,
        "tz": "America/Los_Angeles",
    },
    "MIA": {
        "name": "Miami Intl",
        "lat": 25.80,
        "lon": -80.29,
        "tz": "America/New_York",
    },
    "SEA": {
        "name": "Seattle-Tacoma Intl",
        "lat": 47.45,
        "lon": -122.31,
        "tz": "America/Los_Angeles",
    },
    "PHX": {
        "name": "Phoenix Sky Harbor Intl",
        "lat": 33.44,
        "lon": -112.01,
        "tz": "America/Phoenix",
    },
}

_prediction_cache: TTLCache[DelayPrediction] = TTLCache()
_airport_cache: TTLCache[AirportStatus] = TTLCache()


@dataclass
class _Contribution:
    factor: str
    detail: str
    impact: str
    delta: float
    delay_minutes: int = 0
    explain_only: bool = False


def clear_caches() -> None:
    global _prediction_cache, _airport_cache
    _prediction_cache = TTLCache()
    _airport_cache = TTLCache()


def pick_hour(payload: dict, moment: datetime) -> dict | None:
    """Hourly row closest to `moment`. None if the forecast doesn't cover it."""
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        return None
    target = _aware(moment).astimezone(timezone.utc)
    best_index = 0
    best_diff: float | None = None
    for index, stamp in enumerate(times):
        hour = datetime.fromisoformat(str(stamp)).replace(tzinfo=timezone.utc)
        diff = abs((hour - target).total_seconds())
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best_index = index
    if best_diff is None or best_diff > 90 * 60:
        return None

    def value(key: str) -> float | int | None:
        series = hourly.get(key) or []
        if best_index >= len(series):
            return None
        item = series[best_index]
        if item is None:
            return None
        return item

    code = value("weather_code")
    return {
        "time": str(times[best_index]),
        "weather_code": int(code) if code is not None else None,
        "precipitation_mm": value("precipitation"),
        "visibility_m": value("visibility"),
        "wind_gusts_kt": value("wind_gusts_10m"),
    }


def describe_weather(code: int | None) -> str:
    if code is None:
        return "Unknown"
    if code == 0:
        return "Clear"
    if code == 1:
        return "Mostly clear"
    if code == 2:
        return "Partly cloudy"
    if code == 3:
        return "Overcast"
    if code in (45, 48):
        return "Fog"
    if code in (51, 53, 55):
        return "Drizzle"
    if code in (56, 57):
        return "Freezing drizzle"
    if code in (61, 63, 65):
        return "Rain"
    if code in (66, 67):
        return "Freezing rain"
    if code in (71, 73, 75, 77):
        return "Snow"
    if code in (80, 81, 82):
        return "Rain showers"
    if code in (85, 86):
        return "Snow showers"
    if code in (95, 96, 99):
        return "Thunderstorm"
    return "Unknown"


def score_delay(
    *,
    origin_iata: str,
    destination_iata: str,
    departure: datetime,
    arrival: datetime,
    origin_weather: dict | None,
    destination_weather: dict | None,
    faa_events: dict[str, list[dict]] | None,
    now: datetime,
    reported_delay_minutes: int | None = None,
    include_destination: bool = True,
    weather_unknown: bool = False,
    weather_out_of_range: bool = False,
    faa_unknown: bool = False,
    base_probability: float | None = None,
    model_name: str = HEURISTIC_NAME,
    history: _Contribution | None = None,
    history_baseline: dict | None = None,
    hour_note: _Contribution | None = None,
) -> DelayPrediction:
    """Turn already-fetched signals into a DelayPrediction. No I/O.

    ``base_probability`` replaces the 20% heuristic base. The BTS model
    path sets it and skips schedule adjustments, which the model already
    learned. ``history`` is an explanation only; it does not move the score.
    """
    departure = _aware(departure)
    now = _aware(now)
    use_model = model_name == MODEL_NAME
    contributions: list[_Contribution] = []

    if not weather_out_of_range:
        contributions.extend(
            _weather_contributions(origin_iata, "departure", "weather_origin", origin_weather)
        )
        if include_destination:
            contributions.extend(
                _weather_contributions(
                    destination_iata,
                    "arrival",
                    "weather_destination",
                    destination_weather,
                )
            )

    if faa_events is None:
        faa_events = {}
    if _faa_applies(departure, now):
        contributions.extend(
            _faa_contributions(origin_iata, faa_events.get(origin_iata.upper(), []), "faa_origin")
        )
        if include_destination and destination_iata.upper() != origin_iata.upper():
            contributions.extend(
                _faa_contributions(
                    destination_iata,
                    faa_events.get(destination_iata.upper(), []),
                    "faa_destination",
                )
            )

    if not use_model:
        contributions.extend(_schedule_contributions(departure))
    if history is not None:
        contributions.append(history)
    if hour_note is not None and use_model:
        contributions.append(hour_note)

    base = BASE_LOG_ODDS if base_probability is None else _logit(_clip_probability(base_probability))
    probability = _sigmoid(base + sum(item.delta for item in contributions if not item.explain_only))
    shown = round(probability, 2)
    if shown < 0.25:
        risk = "low"
    elif shown < 0.50:
        risk = "medium"
    else:
        risk = "high"

    return DelayPrediction(
        risk=risk,
        probability_delayed=shown,
        estimated_delay_minutes=_estimate_minutes(
            probability,
            contributions,
            history_baseline,
            anchor_probability=base_probability,
        ),
        reported_delay_minutes=reported_delay_minutes,
        reasons=_reasons(
            contributions,
            weather_unknown=weather_unknown,
            weather_out_of_range=weather_out_of_range,
            faa_unknown=faa_unknown,
        ),
        model=MODEL_NAME if use_model else HEURISTIC_NAME,
    )


async def predict_delay(flight: Flight | dict | None) -> DelayPrediction | None:
    """Predict arrival delay for one flight. None if the flight is missing."""
    try:
        parsed = _coerce_flight(flight)
    except ValidationError:
        logger.warning("predict_delay received a flight that doesn't match the contract")
        return None
    if parsed is None:
        return None

    cache_key = (
        parsed.number,
        parsed.date,
        parsed.scheduled_departure,
        parsed.origin.iata.upper(),
        parsed.destination.iata.upper(),
    )

    async def build() -> DelayPrediction:
        return await _predict_uncached(parsed)

    try:
        return await _prediction_cache.get_or_set(cache_key, PREDICTION_TTL_SECONDS, build)
    except Exception:
        logger.exception("delay prediction failed for %s", parsed.number)
        return None


async def airport_status(iata: str) -> AirportStatus | None:
    """Current weather, FAA programs, and delay risk for one US airport."""
    code = iata.strip().upper()
    airport = find_airport(code)
    if airport is None:
        return None

    async def build() -> AirportStatus:
        return await _airport_status_uncached(code, airport)

    try:
        return await _airport_cache.get_or_set(code, AIRPORT_TTL_SECONDS, build)
    except Exception:
        logger.exception("airport status failed for %s", code)
        return None


def find_airport(code: str) -> dict[str, str | float] | None:
    """Name, coordinates, and time zone for a US airport IATA code."""
    if code in DEMO_AIRPORTS:
        return DEMO_AIRPORTS[code]
    entry = _airport_index().get(code)
    if entry is None:
        return None
    lat = float(entry["lat"])
    lon = float(entry["lon"])
    return {
        "name": str(entry["name"]),
        "lat": lat,
        "lon": lon,
        "tz": _estimate_us_zone(lat, lon),
    }


@cache
def _airport_index() -> dict[str, dict]:
    try:
        entries = json.loads(AIRPORTS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("could not read %s; only demo airports resolve", AIRPORTS_FILE)
        return {}
    return {
        str(entry["iata"]).upper(): entry
        for entry in entries
        if isinstance(entry, dict)
        and entry.get("iata")
        and isinstance(entry.get("lat"), (int, float))
        and isinstance(entry.get("lon"), (int, float))
    }


def _estimate_us_zone(lat: float, lon: float) -> str:
    """Rough US zone from coordinates. Only feeds the low-impact time-of-day factor."""
    if lon < -154 and lat < 30:
        return "Pacific/Honolulu"
    if lon < -130 and lat > 50:
        return "America/Anchorage"
    if lon > -68 and lat < 20:
        return "America/Puerto_Rico"
    if lon >= -87.5:
        return "America/New_York"
    if lon >= -102:
        return "America/Chicago"
    if lon >= -114.5:
        return "America/Denver"
    return "America/Los_Angeles"


async def _predict_uncached(flight: Flight) -> DelayPrediction:
    departure = _parse_dt(flight.scheduled_departure)
    arrival = _parse_dt(flight.scheduled_arrival)
    now = datetime.now(timezone.utc)
    weather_out_of_range = departure - now > FORECAST_LIMIT
    origin_weather = None
    destination_weather = None
    weather_unknown = False

    if not weather_out_of_range:
        try:
            start = departure.astimezone(timezone.utc).date()
            end = arrival.astimezone(timezone.utc).date()
            payloads = await get_forecast(
                [
                    (flight.origin.lat, flight.origin.lon),
                    (flight.destination.lat, flight.destination.lon),
                ],
                start,
                end if end >= start else start,
            )
            if payloads and payloads[0] is not None:
                origin_weather = pick_hour(payloads[0], departure)
            if len(payloads) > 1 and payloads[1] is not None:
                destination_weather = pick_hour(payloads[1], arrival)
            if origin_weather is None and destination_weather is None:
                weather_unknown = True
        except Exception:
            logger.warning("weather lookup failed for %s", flight.number, exc_info=True)
            weather_unknown = True

    faa_events: dict[str, list[dict]] = {}
    faa_unknown = False
    if _faa_applies(departure, now):
        try:
            faa_events = await get_airport_events()
        except Exception:
            logger.warning("FAA status lookup failed for %s", flight.number, exc_info=True)
            faa_unknown = True
            faa_events = {}

    model_probability = _model_probability(flight, departure)
    history, baseline = _history(flight, departure)
    return score_delay(
        origin_iata=flight.origin.iata,
        destination_iata=flight.destination.iata,
        departure=departure,
        arrival=arrival,
        origin_weather=origin_weather,
        destination_weather=destination_weather,
        faa_events=faa_events,
        now=now,
        reported_delay_minutes=_reported_delay_minutes(flight),
        weather_unknown=weather_unknown,
        weather_out_of_range=weather_out_of_range,
        faa_unknown=faa_unknown,
        base_probability=model_probability,
        model_name=MODEL_NAME if model_probability is not None else HEURISTIC_NAME,
        history=history if model_probability is not None else None,
        history_baseline=baseline,
        hour_note=_hour_note(departure) if model_probability is not None else None,
    )


async def _airport_status_uncached(code: str, airport: dict[str, str | float]) -> AirportStatus:
    now = datetime.now(timezone.utc)
    local_now = now.astimezone(ZoneInfo(str(airport["tz"])))
    weather_hour = None
    weather_unknown = False
    try:
        payloads = await get_forecast([(float(airport["lat"]), float(airport["lon"]))], now.date())
        if payloads and payloads[0] is not None:
            weather_hour = pick_hour(payloads[0], now)
        if weather_hour is None:
            weather_unknown = True
    except Exception:
        logger.warning("weather lookup failed for %s", code, exc_info=True)
        weather_unknown = True

    faa_unknown = False
    try:
        faa_events = await get_airport_events()
    except Exception:
        logger.warning("FAA status lookup failed for %s", code, exc_info=True)
        faa_events = {}
        faa_unknown = True

    prediction = score_delay(
        origin_iata=code,
        destination_iata=code,
        departure=local_now,
        arrival=local_now,
        origin_weather=weather_hour,
        destination_weather=None,
        faa_events=faa_events,
        now=now,
        include_destination=False,
        weather_unknown=weather_unknown,
        faa_unknown=faa_unknown,
    )
    weather = None
    if weather_hour is not None:
        weather = AirportWeather(
            time=f"{weather_hour['time']}Z",
            weather_code=weather_hour["weather_code"],
            description=describe_weather(weather_hour["weather_code"]),
            wind_gusts_kt=_as_float(weather_hour.get("wind_gusts_kt")),
            visibility_m=_as_float(weather_hour.get("visibility_m")),
            precipitation_mm=_as_float(weather_hour.get("precipitation_mm")),
        )
    return AirportStatus(
        iata=code,
        name=str(airport["name"]),
        weather=weather,
        faa_events=[FaaEventModel.model_validate(event) for event in faa_events.get(code, [])],
        risk=prediction.risk,
        reasons=prediction.reasons,
    )


def _weather_contributions(
    iata: str,
    when: str,
    factor: str,
    hour: dict | None,
) -> list[_Contribution]:
    if not hour:
        return []
    code = hour.get("weather_code")
    if code is not None:
        code = int(code)
    gusts = hour.get("wind_gusts_kt")
    visibility = hour.get("visibility_m")
    found: list[_Contribution] = []

    if code in (95, 96, 99):
        found.append(
            _Contribution(
                factor,
                f"Thunderstorms forecast at {iata} around {when}",
                "high",
                1.5,
            )
        )
    elif code in range(71, 78) or code in (85, 86):
        found.append(
            _Contribution(factor, f"Snow forecast at {iata} around {when}", "high", 1.2)
        )
    elif code in (56, 57, 66, 67):
        found.append(
            _Contribution(
                factor,
                f"Freezing precipitation forecast at {iata} around {when}",
                "high",
                1.2,
            )
        )
    elif code in (63, 64, 65, 81, 82):
        found.append(
            _Contribution(factor, f"Heavy rain forecast at {iata} around {when}", "low", 0.4)
        )

    # Fog codes and visibility under about 1 statute mile are one signal.
    low_visibility = visibility is not None and float(visibility) < 1600
    if code in (45, 48) or low_visibility:
        if visibility is not None:
            detail = (
                f"Low visibility at {iata} around {when} ({round(float(visibility))} m)"
            )
        else:
            detail = f"Fog forecast at {iata} around {when}"
        found.append(_Contribution(factor, detail, "medium", 0.7))

    if gusts is not None and float(gusts) >= 35:
        found.append(
            _Contribution(
                factor,
                f"Wind gusts near {round(float(gusts))} kt at {iata} around {when}",
                "medium",
                0.8,
            )
        )
    return found


def _faa_contributions(
    iata: str,
    events: list[dict],
    factor: str,
) -> list[_Contribution]:
    best: _Contribution | None = None
    for event in events:
        scored = _score_faa_event(iata, event, factor)
        if scored is not None and (best is None or scored.delta > best.delta):
            best = scored
    return [best] if best is not None else []


def _score_faa_event(iata: str, event: dict, factor: str) -> _Contribution | None:
    kind = event.get("type")
    reason = str(event.get("reason") or "unspecified")
    average = event.get("avg_minutes") or 0
    if kind == "ground_stop":
        return _Contribution(
            factor,
            f"Ground stop at {iata} ({reason})",
            "high",
            2.5,
            delay_minutes=GROUND_STOP_MINUTES,
        )
    if kind == "closure":
        # The feed's "closures" are often GA-only restrictions, which don't
        # hold airline flights. Those stay on the airport payload and are
        # left out of the score.
        if not _closure_affects_airlines(reason):
            return None
        return _Contribution(
            factor,
            f"Airport closure at {iata}",
            "high",
            2.5,
            delay_minutes=CLOSURE_MINUTES,
        )
    if kind == "ground_delay":
        return _Contribution(
            factor,
            f"Ground delay program at {iata} (avg {average} min, {reason})",
            "high",
            1.5 + average / 60,
            delay_minutes=int(average),
        )
    if kind == "general_delay" and average > 30:
        return _Contribution(
            factor,
            f"Arrival/departure delay at {iata} (avg {average} min, {reason})",
            "medium",
            0.8,
            delay_minutes=int(average),
        )
    return None


def _closure_affects_airlines(reason: str) -> bool:
    text = reason.upper()
    return "NON SKED" not in text and "NON-SKED" not in text and "TRANSIENT" not in text


def _schedule_contributions(departure: datetime) -> list[_Contribution]:
    found: list[_Contribution] = []
    hour = departure.hour
    if 17 <= hour <= 18:
        found.append(
            _Contribution(
                "time_of_day",
                "Early-evening departures (5–7 pm local) are a little later on average",
                "low",
                EARLY_EVENING_DELTA,
            )
        )
    elif 19 <= hour <= 21:
        found.append(
            _Contribution(
                "time_of_day",
                "Later evening departures (7–10 pm local) pick up some delay as the day stacks up",
                "low",
                LATE_EVENING_DELTA,
            )
        )
    elif hour < 9:
        found.append(
            _Contribution(
                "time_of_day",
                "Early morning departures are delayed less often",
                "low",
                EARLY_DELTA,
            )
        )

    weekday = departure.weekday()
    month = departure.month
    day = departure.day
    bits: list[str] = []
    if weekday == 4:
        bits.append("Friday")
    elif weekday == 6:
        bits.append("Sunday")
    if month in (6, 7, 8):
        bits.append("the summer travel season")
    if (month == 12 and day >= 18) or (month == 1 and day == 1):
        bits.append("the holiday travel period")
    if bits:
        factor = "day_of_week" if weekday in (4, 6) else "season"
        if bits == ["Friday"] or bits == ["Sunday"]:
            detail = f"{bits[0]} departures add a little delay risk"
        else:
            detail = f"{' and '.join(bits)} add a little delay risk"
        found.append(_Contribution(factor, detail, "low", DAY_SEASON_DELTA))
    return found


def _reasons(
    contributions: list[_Contribution],
    *,
    weather_unknown: bool,
    weather_out_of_range: bool,
    faa_unknown: bool,
) -> list[DelayReason]:
    explain = [item for item in contributions if item.explain_only]
    ranked = sorted(
        (item for item in contributions if not item.explain_only and item.delta != 0),
        key=lambda item: abs(item.delta),
        reverse=True,
    )
    reasons = [
        DelayReason(factor=item.factor, detail=item.detail, impact=item.impact) for item in ranked[:3]
    ]
    reasons.extend(
        DelayReason(factor=item.factor, detail=item.detail, impact=item.impact) for item in explain
    )

    if ranked:
        if weather_out_of_range:
            reasons.append(
                DelayReason(
                    factor="weather_origin",
                    detail=(
                        "Departure is more than 16 days away, so no weather "
                        "forecast is available yet"
                    ),
                    impact="low",
                )
            )
        elif weather_unknown:
            reasons.append(
                DelayReason(
                    factor="weather_origin",
                    detail="Weather forecast is unavailable right now",
                    impact="low",
                )
            )
        return reasons

    if weather_out_of_range:
        detail = "Departure is more than 16 days away, so this estimate uses the time of day only"
        factor = "weather_origin"
    elif weather_unknown and faa_unknown:
        detail = "Live weather and FAA status are unavailable, so this is a base-rate estimate"
        factor = "weather_origin"
    elif weather_unknown:
        detail = "Weather forecast is unavailable, so this estimate does not include weather"
        factor = "weather_origin"
    elif faa_unknown:
        detail = "FAA airport status is unavailable. No weather issues are in the forecast"
        factor = "faa_origin"
    else:
        detail = "No weather or airport issues expected"
        factor = "time_of_day"
    reasons.append(DelayReason(factor=factor, detail=detail, impact="low"))
    return reasons


def _faa_applies(departure: datetime, now: datetime) -> bool:
    delta = _aware(departure) - _aware(now)
    return timedelta(minutes=-30) <= delta <= FAA_WINDOW


def _reported_delay_minutes(flight: Flight) -> int | None:
    if not flight.estimated_departure:
        return None
    try:
        estimated = _parse_dt(flight.estimated_departure)
        scheduled = _parse_dt(flight.scheduled_departure)
    except ValueError:
        return None
    minutes = round((estimated - scheduled).total_seconds() / 60)
    if minutes < 1:
        return None
    return minutes


def _coerce_flight(flight: Flight | dict | None) -> Flight | None:
    if flight is None:
        return None
    if isinstance(flight, Flight):
        return flight
    if isinstance(flight, BaseModel):
        # B's schemas.Flight carries date/datetime objects; this model wants ISO strings.
        flight = flight.model_dump(mode="json")
    if isinstance(flight, dict):
        return Flight.model_validate(flight)
    return Flight.model_validate(flight, from_attributes=True)


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return _aware(parsed)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def model_info() -> ModelInfo:
    """Accuracy and hourly delay rates for the About page. Heuristic if untrained."""
    if not MODEL_META_PATH.exists():
        return ModelInfo(
            model=HEURISTIC_NAME,
            test_auc=None,
            base_rate=BASE_RATE,
            train_months=[],
            calibration_month=None,
            test_month=None,
            months=[],
            hourly_delay_rate=[],
        )
    return ModelInfo.model_validate(json.loads(MODEL_META_PATH.read_text(encoding="utf-8")))


def _model_probability(flight: Flight, departure: datetime) -> float | None:
    artifact = _model_artifact()
    if artifact is None:
        return None
    # BTS covers US domestic flights only. An international leg has an
    # unseen airport and a distance far outside training, so the heuristic
    # is the more honest answer there.
    if find_airport(flight.origin.iata.strip().upper()) is None or (
        find_airport(flight.destination.iata.strip().upper()) is None
    ):
        return None
    categories = artifact["categories"]
    features = [
        _category_code(categories["carrier"], flight.airline.iata.strip().upper(), allow_other=False),
        _category_code(categories["origin"], flight.origin.iata.strip().upper(), allow_other=True),
        _category_code(categories["dest"], flight.destination.iata.strip().upper(), allow_other=True),
        float(departure.month),
        float(departure.weekday()),
        float(departure.hour),
        _distance_miles(flight),
    ]
    try:
        raw = float(artifact["model"].predict_proba([features])[0, 1])
        calibrator = artifact.get("calibrator")
        if calibrator is not None:
            raw = float(calibrator.predict([raw])[0])
    except Exception:
        logger.exception("BTS model prediction failed for %s; using the heuristic", flight.number)
        return None
    if math.isnan(raw):
        return None
    return _clip_probability(raw)


def _history(flight: Flight, departure: datetime) -> tuple[_Contribution | None, dict | None]:
    """Route sentence plus the baseline used to scale expected minutes."""
    stats = _route_stats()
    if not stats:
        return None, None
    route = stats["routes"].get(f"{flight.origin.iata.upper()}-{flight.destination.iata.upper()}")
    hour_rows = stats.get("hours") or []
    hour = next((row for row in hour_rows if row.get("hour") == departure.hour), None)
    baseline = route or hour
    if not isinstance(baseline, dict) or not baseline.get("flights"):
        return None, None
    if route is None:
        return None, baseline
    percent = round(float(route["delay_rate"]) * 100)
    cause = CAUSE_PHRASE.get(str(route.get("dominant_cause") or ""))
    if cause:
        detail = (
            f"Historically {percent}% of {flight.origin.iata.upper()}→"
            f"{flight.destination.iata.upper()} flights arrive late, most often from {cause}"
        )
    else:
        detail = (
            f"Historically {percent}% of {flight.origin.iata.upper()}→"
            f"{flight.destination.iata.upper()} flights arrive late"
        )
    impact = "medium" if float(route["delay_rate"]) >= 0.35 else "low"
    reason = _Contribution("historical_route", detail, impact, 0.0, explain_only=True)
    return reason, baseline


def _hour_note(departure: datetime) -> _Contribution | None:
    """National BTS delay rate for this local departure hour, when it stands out."""
    stats = _route_stats()
    if not stats:
        return None
    row = next((item for item in stats.get("hours") or [] if item.get("hour") == departure.hour), None)
    if not isinstance(row, dict) or int(row.get("flights") or 0) < 1000:
        return None
    rate = float(row.get("delay_rate") or 0.0)
    percent = round(rate * 100)
    label = _hour_label(departure.hour)
    if rate >= 0.30:
        detail = (
            f"Flights leaving around {label} are among the latest of the day: "
            f"{percent}% arrive late nationally"
        )
    elif rate <= 0.12:
        detail = f"Early departures run on time more often: {percent}% of flights around {label} arrive late"
    else:
        return None
    return _Contribution("time_of_day", detail, "low", 0.0, explain_only=True)


def _hour_label(hour: int) -> str:
    if hour == 0:
        return "midnight"
    if hour == 12:
        return "noon"
    return f"{hour % 12} {'am' if hour < 12 else 'pm'}"


def _estimate_minutes(
    probability: float,
    contributions: list[_Contribution],
    baseline: dict | None,
    anchor_probability: float | None = None,
) -> int:
    """Expected minutes late.

    With route history, start from that route's real average lateness and
    move only halfway toward this departure's own rate. Fully scaling by
    probability / route rate was too jumpy: a 14% route with a 13 minute
    average became "expect about 19 minutes" on a slightly later hour.
    Live weather and FAA add about 50 minutes per extra point of risk,
    and a published FAA delay replaces the estimate when it is longer.
    """
    faa_delay = max(
        (item.delay_minutes for item in contributions if not item.explain_only),
        default=0,
    )
    estimate = probability * 45
    anchor = probability if anchor_probability is None else anchor_probability
    if baseline is not None:
        rate = baseline.get("delay_rate")
        mean = baseline.get("mean_delay_minutes")
        if isinstance(rate, (int, float)) and isinstance(mean, (int, float)) and float(rate) >= 0.05:
            ratio = anchor / float(rate)
            damped = 1 + 0.5 * (ratio - 1)
            damped = min(1.5, max(0.65, damped))
            estimate = float(mean) * damped
            estimate += max(0.0, probability - anchor) * 50
    if faa_delay > estimate:
        estimate = faa_delay
    return int(min(max(round(estimate), 0), 180))


def _distance_miles(flight: Flight) -> float:
    distance_km = getattr(flight, "distance_km", None)
    if isinstance(distance_km, (int, float)) and distance_km > 0:
        return float(distance_km) * 0.621371
    return _great_circle_miles(
        flight.origin.lat,
        flight.origin.lon,
        flight.destination.lat,
        flight.destination.lon,
    )


def _great_circle_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_miles = 3958.8
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lon / 2) ** 2
    return 2 * radius_miles * math.asin(min(1.0, math.sqrt(a)))


def _category_code(mapping: dict[str, int], value: str, *, allow_other: bool) -> float:
    code = mapping.get(value)
    if code is not None:
        return float(code)
    if allow_other and "OTHER" in mapping:
        return float(mapping["OTHER"])
    return float("nan")


def _clip_probability(probability: float) -> float:
    return min(0.93, max(0.02, probability))


def _logit(probability: float) -> float:
    return math.log(probability / (1.0 - probability))


@cache
def _model_artifact() -> dict | None:
    if not MODEL_PATH.exists():
        return None
    try:
        artifact = joblib.load(MODEL_PATH)
    except Exception:
        logger.exception("could not load %s; using the heuristic", MODEL_PATH)
        return None
    if not isinstance(artifact, dict) or "model" not in artifact or "categories" not in artifact:
        logger.warning("delay model file is missing its model or categories")
        return None
    logger.info("loaded BTS delay model from %s", MODEL_PATH.name)
    return artifact


@cache
def _route_stats() -> dict | None:
    if not ROUTE_STATS_PATH.exists():
        return None
    try:
        payload = json.loads(ROUTE_STATS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("could not read %s", ROUTE_STATS_PATH)
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _sigmoid(log_odds: float) -> float:
    if log_odds >= 0:
        return 1.0 / (1.0 + math.exp(-log_odds))
    return math.exp(log_odds) / (1.0 + math.exp(log_odds))


def _as_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None
