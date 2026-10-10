"""AeroDataBox lookup for a map aircraft, requested only when its popup opens."""

import os

import httpx

from app.clients.aerodatabox_client import (
    AeroDataBoxNotConfigured,
    BASE_URL,
    RAPIDAPI_HOST,
)


async def get_flights_by_icao24(icao24: str) -> list[dict]:
    key = os.getenv("AERODATABOX_API_KEY")
    if not key:
        raise AeroDataBoxNotConfigured("Set AERODATABOX_API_KEY in backend/.env")

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{BASE_URL}/flights/icao24/{icao24}",
            headers={"X-RapidAPI-Key": key, "X-RapidAPI-Host": RAPIDAPI_HOST},
            params={"withAircraftImage": "false"},
        )
        if response.status_code == 204:
            return []
        response.raise_for_status()
        flights = response.json()
        if not isinstance(flights, list):
            raise ValueError("Unexpected AeroDataBox flight-status response")
        return flights
