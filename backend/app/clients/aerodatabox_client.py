"""Thin AeroDataBox RapidAPI flight-status client."""

import os
from datetime import date
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

BASE_URL = "https://aerodatabox.p.rapidapi.com"
RAPIDAPI_HOST = "aerodatabox.p.rapidapi.com"


class AeroDataBoxNotConfigured(Exception):
    pass


async def get_flights_by_number(number: str, departure_date: date) -> list[dict]:
    key = os.getenv("AERODATABOX_API_KEY")
    if not key:
        raise AeroDataBoxNotConfigured("Set AERODATABOX_API_KEY in backend/.env")

    # Departure role prevents an overnight arrival from matching the wrong day.
    url = f"{BASE_URL}/flights/number/{number}/{departure_date.isoformat()}"
    headers = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": RAPIDAPI_HOST}
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            url,
            headers=headers,
            params={"dateLocalRole": "Departure", "withAircraftImage": "false"},
        )
        if response.status_code == 204:
            return []
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise ValueError("Unexpected AeroDataBox flight-status response")
        return data
