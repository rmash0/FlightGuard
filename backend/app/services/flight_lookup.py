"""Normalize provider flights and compose the results-page response."""

import inspect
import logging
import os
from datetime import date, datetime, timezone
from importlib import import_module
from importlib.util import find_spec
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from fastapi import HTTPException

from app.clients.aerodatabox_client import AeroDataBoxNotConfigured, get_flights_by_number
from app.models.schemas import Airport, Airline, DelayPrediction, Emissions, Flight, FlightLookupResponse
from app.services.cache import TTLCache
from app.services.demo_fixtures import get_demo_lookup

logger = logging.getLogger(__name__)
LOOKUP_TTL_SECONDS = 600
_lookup_cache: TTLCache[FlightLookupResponse] = TTLCache()
_provider_cache: TTLCache[list[dict]] = TTLCache()

_STATUSES = {
    "expected": "scheduled",
    "checkin": "scheduled",
    "boarding": "scheduled",
    "gateclosed": "scheduled",
    "delayed": "delayed",
    "departed": "departed",
    "enroute": "en_route",
    "approaching": "en_route",
    "arrived": "landed",
    "canceled": "cancelled",
    "canceleduncertain": "unknown",
    "diverted": "unknown",
}


def _airport(movement: dict[str, Any]) -> Airport:
    provider_airport = movement["airport"]
    location = provider_airport["location"]
    if provider_airport.get("countryCode") != "US":
        raise ValueError("Flight is outside the US scope")
    return Airport(
        iata=provider_airport["iata"],
        name=provider_airport["name"],
        lat=location["lat"],
        lon=location["lon"],
    )


def _time(value: dict[str, str] | None, zone: str | None) -> datetime | None:
    if value is None:
        return None
    local = value.get("local")
    if local:
        parsed = datetime.fromisoformat(local.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            return parsed
        if zone:
            try:
                return parsed.replace(tzinfo=ZoneInfo(zone))
            except ZoneInfoNotFoundError:
                pass
    utc = value.get("utc")
    if utc:
        utc_time = datetime.fromisoformat(utc.replace("Z", "+00:00")).astimezone(timezone.utc)
        if local:
            offset = parsed - utc_time.replace(tzinfo=None)
            return parsed.replace(tzinfo=timezone(offset))
        return utc_time
    return None


def normalize_flight(raw: dict[str, Any], number: str, departure_date: date) -> Flight:
    departure = raw["departure"]
    arrival = raw["arrival"]
    origin = _airport(departure)
    destination = _airport(arrival)
    scheduled_departure = _time(departure.get("scheduledTime"), departure["airport"].get("timeZone"))
    scheduled_arrival = _time(arrival.get("scheduledTime"), arrival["airport"].get("timeZone"))
    if scheduled_departure is None or scheduled_arrival is None:
        raise ValueError("Flight has no complete schedule")
    if scheduled_departure.date() != departure_date:
        raise ValueError("Flight departs on a different date")

    airline = raw.get("airline") or {}
    revised_departure = _time(departure.get("revisedTime"), departure["airport"].get("timeZone"))
    provider_status = str(raw.get("status", "unknown")).lower()
    departed = provider_status in {"departed", "enroute", "approaching", "arrived"}
    aircraft = raw.get("aircraft") or {}
    return Flight(
        number=number,
        airline=Airline(iata=airline.get("iata") or number[:2], name=airline.get("name") or number[:2]),
        date=departure_date,
        origin=origin,
        destination=destination,
        scheduled_departure=scheduled_departure,
        scheduled_arrival=scheduled_arrival,
        estimated_departure=None if departed else revised_departure,
        actual_departure=revised_departure if departed else None,
        status=_STATUSES.get(provider_status, "unknown"),
        aircraft_type=aircraft.get("model"),
        icao24=aircraft.get("modeS"),
    )


async def _optional_service(module_name: str, function_name: str, flight: Flight, result_type: type):
    """C and D can add these functions without changing this owner's files."""
    if find_spec(module_name) is None:
        return None
    try:
        function = getattr(import_module(module_name), function_name)
        result = function(flight)
        if inspect.isawaitable(result):
            result = await result
        return result_type.model_validate(result) if result is not None else None
    except Exception:
        logger.exception("%s failed for %s", function_name, flight.number)
        return None


async def _live_lookup(number: str, departure_date: date) -> FlightLookupResponse:
    try:
        candidates = await _provider_cache.get_or_set(
            (number, departure_date),
            LOOKUP_TTL_SECONDS,
            lambda: get_flights_by_number(number, departure_date),
        )
    except AeroDataBoxNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        logger.warning("AeroDataBox status %s", exc.response.status_code)
        raise HTTPException(status_code=502, detail="Flight provider is unavailable") from exc
    except (httpx.RequestError, ValueError) as exc:
        logger.warning("AeroDataBox request failed: %s", exc)
        raise HTTPException(status_code=502, detail="Flight provider is unavailable") from exc

    if not candidates:
        raise HTTPException(status_code=404, detail="Flight not found")

    flight = None
    for candidate in candidates:
        try:
            flight = normalize_flight(candidate, number, departure_date)
            break
        except (AttributeError, KeyError, TypeError, ValueError):
            continue
    if flight is None:
        raise HTTPException(status_code=502, detail="Provider returned no complete US flight for that date")

    prediction = await _optional_service(
        "app.services.delay_predictor", "predict_delay", flight, DelayPrediction
    )
    emissions = await _optional_service("app.services.emissions", "get_emissions", flight, Emissions)
    return FlightLookupResponse(flight=flight, prediction=prediction, emissions=emissions)


async def lookup_flight(number: str, departure_date: date) -> FlightLookupResponse:
    number = "".join(number.upper().split())
    if os.getenv("DEMO_MODE", "false").lower() in {"true", "1", "yes"}:
        fixture = get_demo_lookup(number, departure_date)
        if fixture is None:
            raise HTTPException(status_code=404, detail="No demo fixture for that flight and date")
        return fixture
    return await _lookup_cache.get_or_set(
        (number, departure_date),
        LOOKUP_TTL_SECONDS,
        lambda: _live_lookup(number, departure_date),
    )
