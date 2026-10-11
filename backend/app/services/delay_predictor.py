"""Heuristic delay prediction (v1).

Scores in log-odds so weather, FAA programs, and schedule effects add up
and the probability stays between 0 and 1. A later BTS model can replace
the base rate; the live weather and FAA adjustments stay here.

`predict_delay` is what Role B's flight lookup should call. It returns
None only when the flight itself is missing or unusable. A failed weather
or FAA fetch still produces a prediction.
"""

import json
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ValidationError

from app.clients.faa_status_client import get_airport_events
from app.clients.memory_cache import MemoryCache
from app.clients.open_meteo_client import get_forecast
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
BASE_LOG_ODDS = math.log(0.20 / 0.80)
PREDICTION_TTL_SECONDS = 5 * 60
AIRPORT_TTL_SECONDS = 3 * 60
FAA_WINDOW = timedelta(hours=6)
FORECAST_LIMIT = timedelta(days=16)

AIRPORTS_FILE = Path(__file__).resolve().parents[1] / "data" / "airports.json"

# Hubs with checked time zones. Role D's airports.json (no `tz` field) covers
# every other US airport; its zone is estimated from coordinates.
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

_prediction_cache = MemoryCache()
_airport_cache = MemoryCache()


@dataclass
class _Contribution:
    factor: str
    detail: str
    impact: str
    delta: float
    delay_minutes: int = 0


def clear_caches() -> None:
    _prediction_cache.clear()
    _airport_cache.clear()


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
) -> DelayPrediction:
    """Turn already-fetched signals into a DelayPrediction. No I/O."""
    departure = _aware(departure)
    now = _aware(now)
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

    contributions.extend(_schedule_contributions(departure))

    probability = _sigmoid(BASE_LOG_ODDS + sum(item.delta for item in contributions))
    shown = round(probability, 2)
    if shown < 0.25:
        risk = "low"
    elif shown < 0.50:
        risk = "medium"
    else:
        risk = "high"

    faa_delay = max((item.delay_minutes for item in contributions), default=0)
    estimate = round(probability * 45)
    if faa_delay > estimate:
        estimate = faa_delay

    return DelayPrediction(
        risk=risk,
        probability_delayed=shown,
        estimated_delay_minutes=estimate,
        reported_delay_minutes=reported_delay_minutes,
        reasons=_reasons(
            contributions,
            weather_unknown=weather_unknown,
            weather_out_of_range=weather_out_of_range,
            faa_unknown=faa_unknown,
        ),
        model="heuristic-v1",
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

    cache_key = f"{parsed.number}|{parsed.date}"
    cached = _prediction_cache.get(cache_key)
    if isinstance(cached, DelayPrediction):
        return cached

    try:
        prediction = await _predict_uncached(parsed)
    except Exception:
        logger.exception("delay prediction failed for %s", parsed.number)
        return None
    _prediction_cache.set(cache_key, prediction, PREDICTION_TTL_SECONDS)
    return prediction


async def airport_status(iata: str) -> AirportStatus | None:
    """Current weather, FAA programs, and delay risk for one US airport."""
    code = iata.strip().upper()
    airport = find_airport(code)
    if airport is None:
        return None

    cached = _airport_cache.get(code)
    if isinstance(cached, AirportStatus):
        return cached

    try:
        status = await _airport_status_uncached(code, airport)
    except Exception:
        logger.exception("airport status failed for %s", code)
        return None
    _airport_cache.set(code, status, AIRPORT_TTL_SECONDS)
    return status


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
        )
    if kind == "closure":
        # The feed's "closures" are often GA-only restrictions, which don't
        # hold airline flights. Those stay on the airport payload and are
        # left out of the score.
        if not _closure_affects_airlines(reason):
            return None
        return _Contribution(factor, f"Airport closure at {iata}", "high", 2.5)
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
    if 17 <= hour <= 21:
        found.append(
            _Contribution(
                "time_of_day",
                "Evening departures (5–10 pm local) run later on average",
                "low",
                0.5,
            )
        )
    elif hour < 9:
        found.append(
            _Contribution(
                "time_of_day",
                "Early morning departures are delayed less often",
                "low",
                -0.4,
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
        found.append(_Contribution(factor, detail, "low", 0.2))
    return found


def _reasons(
    contributions: list[_Contribution],
    *,
    weather_unknown: bool,
    weather_out_of_range: bool,
    faa_unknown: bool,
) -> list[DelayReason]:
    ranked = sorted(contributions, key=lambda item: abs(item.delta), reverse=True)
    selected = [
        DelayReason(factor=item.factor, detail=item.detail, impact=item.impact)
        for item in ranked
        if item.delta != 0
    ][:3]

    if selected:
        reasons = list(selected)
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
    return [DelayReason(factor=factor, detail=detail, impact="low")]


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


def _sigmoid(log_odds: float) -> float:
    if log_odds >= 0:
        return 1.0 / (1.0 + math.exp(-log_odds))
    return math.exp(log_odds) / (1.0 + math.exp(log_odds))


def _as_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None
