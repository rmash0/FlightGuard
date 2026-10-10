import logging
import math
import re

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.clients.opensky_client import get_aircraft_in_area
from app.models.schemas import LiveFlightDetails
from app.services.cache import TTLCache
from app.services.live_flight_details import get_live_flight_details

router = APIRouter(prefix="/flights", tags=["Live Map"])

logger = logging.getLogger(__name__)

CACHE_TTL = 60
ERROR_CACHE_TTL = 120
MAX_AREA = 100

aircraft_cache = TTLCache[dict]()


def normalize_bounds(
    lamin: float,
    lamax: float,
    lomin: float,
    lomax: float,
):
    if lamin >= lamax or lomin >= lomax:
        raise HTTPException(
            status_code=422,
            detail="Invalid bounding box",
        )

    bounds = (
        math.floor(lamin * 2) / 2,
        math.ceil(lamax * 2) / 2,
        math.floor(lomin * 2) / 2,
        math.ceil(lomax * 2) / 2,
    )

    area = (
        (bounds[1] - bounds[0])
        * (bounds[3] - bounds[2])
    )

    if area > MAX_AREA:
        raise HTTPException(
            status_code=422,
            detail="Zoom in to a smaller area to view live aircraft",
        )

    return bounds


@router.get("/live")
async def live_aircraft(
    lamin: float = Query(..., ge=-90, le=90),
    lamax: float = Query(..., ge=-90, le=90),
    lomin: float = Query(..., ge=-180, le=180),
    lomax: float = Query(..., ge=-180, le=180),
):
    bounds = normalize_bounds(lamin, lamax, lomin, lomax)

    async def fetch():
        try:
            return await get_aircraft_in_area(*bounds)

        except httpx.HTTPStatusError as e:
            status = e.response.status_code

            if status == 429:
                logger.warning("OpenSky rate limit reached")
                return {
                    "error": "rate_limit",
                    "detail": "OpenSky rate limit reached",
                }

            logger.warning("OpenSky returned HTTP %s", status)
            return {
                "error": "upstream",
                "detail": "OpenSky is currently unavailable",
            }

        except (httpx.RequestError, ValueError) as e:
            logger.warning("OpenSky request failed: %s", e)
            return {
                "error": "upstream",
                "detail": "Unable to retrieve live aircraft",
            }
        
    key = ("opensky", bounds)

    result = await aircraft_cache.get_or_set(
        key,
        CACHE_TTL,
        fetch,
    )

    if "error" in result:
        raise HTTPException(
            status_code=429 if result["error"] == "rate_limit" else 503,
            detail=result["detail"],
        )

    filtered_flights = [
        flight
        for flight in result["flights"]
        if lamin <= flight["latitude"] <= lamax
        and lomin <= flight["longitude"] <= lomax
    ]

    return {
        **result,
        "flights": filtered_flights,
    }


@router.get("/live/{icao24}/details", response_model=LiveFlightDetails)
async def live_aircraft_details(
    icao24: str,
    callsign: str = Query("", max_length=8),
) -> LiveFlightDetails:
    if not re.fullmatch(r"[0-9a-fA-F]{6}", icao24):
        raise HTTPException(status_code=422, detail="Invalid aircraft identifier")
    normalized_callsign = "".join(callsign.upper().split())
    if normalized_callsign and not re.fullmatch(r"[A-Z0-9]{1,8}", normalized_callsign):
        raise HTTPException(status_code=422, detail="Invalid callsign")
    return await get_live_flight_details(icao24.lower(), normalized_callsign)
