
import asyncio
import logging
import math
import time
from datetime import date

from app.clients.google_tim_client import (
    get_flight_emissions,
    get_typical_emissions,
)
from app.models.schemas import Emissions, CabinEmissions, EcoComparison
from app.data.eco_constants import (
    GRAMS_PER_KG,
    EARTH_RADIUS_KM,
    CO2_KG_PER_PASSENGER_KM,
    CAR_CO2_KG_PER_KM,
    TREE_CO2_KG_PER_YEAR,
    PERSON_CO2_KG_PER_DAY,
    SMARTPHONE_CHARGE_CO2_KG,
    CABIN_MULTIPLIERS,
)

logger = logging.getLogger(__name__)

CACHE_TTL = 3600
_cache = {}
_inflight = {}
_cache_lock = asyncio.Lock()


def calculate_distance(lat1, lon1, lat2, lon2):
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    a = min(1.0, max(0.0, a))
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def convert_emissions(emissions_grams):
    if not isinstance(emissions_grams, dict):
        return None

    fields = {
        "economy": "economy",
        "premium_economy": "premiumEconomy",
        "business": "business",
        "first": "first",
    }

    result = {}

    for cabin, google_field in fields.items():
        value = emissions_grams.get(google_field)

        if value is None:
            return None

        try:
            value = float(value)
        except (ValueError, TypeError):
            return None

        if not math.isfinite(value) or value < 0:
            return None

        result[cabin] = round(value / GRAMS_PER_KG, 2)

    return result


def calculate_distance_emissions(distance_km):
    economy = distance_km * CO2_KG_PER_PASSENGER_KM

    return {
        cabin: round(economy * multiplier, 2)
        for cabin, multiplier in CABIN_MULTIPLIERS.items()
    }


def calculate_comparisons(co2_kg):
    return [
        EcoComparison(
            label="km in an average gas car",
            value=round(co2_kg / CAR_CO2_KG_PER_KM, 1),
        ),
        EcoComparison(
            label="days of an average American's emissions",
            value=round(co2_kg / PERSON_CO2_KG_PER_DAY, 2),
        ),
        EcoComparison(
            label="urban tree seedlings absorbing CO2 (annualized over 10 years)",
            value=round(co2_kg / TREE_CO2_KG_PER_YEAR, 1),
        ),
        EcoComparison(
            label="smartphones fully charged",
            value=round(co2_kg / SMARTPHONE_CHARGE_CO2_KG),
        ),
    ]


def build_emissions(emissions, tier, source):
    return Emissions(
        co2e_kg_per_passenger=CabinEmissions(**emissions),
        estimate_tier=tier,
        source=source,
        comparisons=calculate_comparisons(emissions["economy"]),
    )


async def _fetch_emissions(
    origin,
    destination,
    carrier,
    flight_number,
    departure_date,
    origin_lat,
    origin_lon,
    destination_lat,
    destination_lon,
):
    flight_data = await get_flight_emissions(
        origin=origin,
        destination=destination,
        carrier=carrier,
        flight_number=flight_number,
        departure_date=departure_date,
    )

    if flight_data:
        emissions = convert_emissions(
            flight_data.get("emissionsGramsPerPax")
        )

        if emissions is not None:
            return build_emissions(
                emissions,
                "flight",
                "google_tim",
            )

    logger.info("Flight emissions unavailable, trying route estimate")

    route_data = await get_typical_emissions(
        origin=origin,
        destination=destination,
    )

    if route_data:
        emissions = convert_emissions(
            route_data.get("emissionsGramsPerPax")
        )

        if emissions is not None:
            return build_emissions(
                emissions,
                "route",
                "google_tim",
            )

    logger.info("Google TIM unavailable, trying distance fallback")

    coordinates = (
        origin_lat,
        origin_lon,
        destination_lat,
        destination_lon,
    )

    if any(value is None for value in coordinates):
        logger.warning("Missing coordinates for distance fallback")
        return None

    if not all(math.isfinite(float(v)) for v in coordinates):
        return None

    distance_km = calculate_distance(*coordinates)

    if distance_km <= 0:
        return None

    emissions = calculate_distance_emissions(distance_km)

    return build_emissions(
        emissions,
        "distance",
        "distance_heuristic",
    )


async def get_emissions(
    origin: str,
    destination: str,
    carrier: str,
    flight_number: int,
    departure_date: date,
    origin_lat: float | None = None,
    origin_lon: float | None = None,
    destination_lat: float | None = None,
    destination_lon: float | None = None,
) -> Emissions | None:
    origin = origin.upper()
    destination = destination.upper()
    carrier = carrier.upper()

    cache_key = (
        origin,
        destination,
        carrier,
        flight_number,
        departure_date.isoformat(),
        origin_lat,
        origin_lon,
        destination_lat,
        destination_lon,
    )

    now = time.monotonic()

    async with _cache_lock:
        cached = _cache.get(cache_key)

        if cached and now - cached[0] < CACHE_TTL:
            return cached[1]

        task = _inflight.get(cache_key)

        if task is None:
            task = asyncio.create_task(
                _fetch_emissions(
                    origin,
                    destination,
                    carrier,
                    flight_number,
                    departure_date,
                    origin_lat,
                    origin_lon,
                    destination_lat,
                    destination_lon,
                )
            )
            _inflight[cache_key] = task

    try:
        result = await task

        async with _cache_lock:
            if result is not None:
                _cache[cache_key] = (
                    time.monotonic(),
                    result,
                )

        return result

    except Exception:
        logger.exception("Failed to calculate flight emissions")
        return None

    finally:
        async with _cache_lock:
            if _inflight.get(cache_key) is task:
                del _inflight[cache_key]

async def get_emissions_for_flight(flight):
    # Flight numbers are a 2-character carrier code plus digits (checked in routes_flights).
    # Take the carrier from the number, not flight.airline: on regional flights such as
    # 9E381 the marketing airline (DL) differs from the operating carrier in the number (9E).
    carrier = flight.number[:2].upper()
    flight_number = flight.number[2:]

    return await get_emissions(
        origin=flight.origin.iata,
        destination=flight.destination.iata,
        carrier=carrier,
        flight_number=int(flight_number),
        departure_date=flight.date,
        origin_lat=flight.origin.lat,
        origin_lon=flight.origin.lon,
        destination_lat=flight.destination.lat,
        destination_lon=flight.destination.lon,
    )