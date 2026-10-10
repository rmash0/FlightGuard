"""Match an OpenSky aircraft to its active AeroDataBox flight on demand."""

import logging

import httpx

from app.clients.aerodatabox_client import AeroDataBoxNotConfigured
from app.clients.live_flight_client import get_flights_by_icao24
from app.models.schemas import LiveFlightDetails
from app.services.cache import TTLCache

logger = logging.getLogger(__name__)
DETAILS_TTL_SECONDS = 600
_details_cache: TTLCache[LiveFlightDetails] = TTLCache()


def _airport_label(movement: object) -> str | None:
    if not isinstance(movement, dict):
        return None
    airport = movement.get("airport")
    if not isinstance(airport, dict):
        return None
    code = airport.get("iata") or airport.get("icao")
    name = airport.get("name")
    if code and name:
        return f"{code} — {name}"
    return code or name


def _matching_flight(flights: list[dict], icao24: str, callsign: str) -> LiveFlightDetails:
    for flight in flights:
        if not isinstance(flight, dict):
            continue
        # An aircraft can fly several legs a day. Do not show another leg's route.
        if str(flight.get("callSign") or "").replace(" ", "").upper() != callsign:
            continue
        aircraft = flight.get("aircraft")
        if not isinstance(aircraft, dict):
            aircraft = {}
        if aircraft.get("modeS") and str(aircraft["modeS"]).lower() != icao24:
            continue
        if str(flight.get("status") or "").lower() not in {"departed", "enroute", "approaching"}:
            continue
        number = str(flight.get("number") or "").replace(" ", "").upper() or None
        return LiveFlightDetails(
            flight_number=number,
            origin=_airport_label(flight.get("departure")),
            destination=_airport_label(flight.get("arrival")),
        )
    return LiveFlightDetails(flight_number=None, origin=None, destination=None)


async def get_live_flight_details(icao24: str, callsign: str) -> LiveFlightDetails:
    if not callsign:
        return LiveFlightDetails(flight_number=None, origin=None, destination=None)

    async def fetch() -> LiveFlightDetails:
        try:
            flights = await get_flights_by_icao24(icao24)
        except (AeroDataBoxNotConfigured, httpx.HTTPError, ValueError) as exc:
            logger.warning("Map flight details unavailable for %s: %s", icao24, exc)
            return LiveFlightDetails(flight_number=None, origin=None, destination=None)
        return _matching_flight(flights, icao24, callsign)

    return await _details_cache.get_or_set(
        (icao24, callsign), DETAILS_TTL_SECONDS, fetch
    )
