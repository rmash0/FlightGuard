
import logging

import httpx

OPENSKY_URL = "https://opensky-network.org/api/states/all"

logger = logging.getLogger(__name__)


async def get_aircraft_in_area(
    lamin: float,
    lamax: float,
    lomin: float,
    lomax: float,
) -> dict:
    params = {
        "lamin": lamin,
        "lamax": lamax,
        "lomin": lomin,
        "lomax": lomax,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            OPENSKY_URL,
            params=params,
        )

        response.raise_for_status()
        data = response.json()

    flights = []

    for state in data.get("states") or []:
        if not isinstance(state, list) or len(state) < 17:
            continue

        longitude = state[5]
        latitude = state[6]

        if longitude is None or latitude is None:
            continue

        if state[8]:
            continue

        flights.append({
            "icao24": state[0],
            "callsign": (state[1] or "").strip(),
            "latitude": latitude,
            "longitude": longitude,
            "altitude": state[7],
            "velocity": state[9],
            "heading": state[10],
            "origin_country": state[2],
        })

    logger.info("OpenSky returned %s airborne aircraft", len(flights))

    return {
        "updated_at": data.get("time"),
        "flights": flights,
    }
