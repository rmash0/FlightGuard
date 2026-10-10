
import os
import logging
from pathlib import Path
from datetime import date

import httpx
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("GOOGLE_TIM_API_KEY")

BASE_URL = "https://travelimpactmodel.googleapis.com/v1"

logger = logging.getLogger(__name__)


async def get_flight_emissions(
    origin: str,
    destination: str,
    carrier: str,
    flight_number: int,
    departure_date: date
):
    if not API_KEY:
        logger.error("GOOGLE_TIM_API_KEY is not set")
        return None

    url = f"{BASE_URL}/flights:computeFlightEmissions"

    payload = {
        "flights": [
            {
                "origin": origin.upper(),
                "destination": destination.upper(),
                "operatingCarrierCode": carrier.upper(),
                "flightNumber": flight_number,
                "departureDate": {
                    "year": departure_date.year,
                    "month": departure_date.month,
                    "day": departure_date.day
                }
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                url,
                params={"key": API_KEY},
                json=payload
            )

            response.raise_for_status()

            data = response.json()
            emissions = data.get("flightEmissions", [])

            if not emissions:
                return None

            return emissions[0]

    except httpx.HTTPStatusError as e:
        logger.warning(
            "Google TIM API returned status %s",
            e.response.status_code
        )
        return None

    except (httpx.RequestError, ValueError) as e:
        logger.warning("Google TIM request failed: %s", e)
        return None


async def get_typical_emissions(
    origin: str,
    destination: str
):
    if not API_KEY:
        logger.error("GOOGLE_TIM_API_KEY is not set")
        return None

    url = f"{BASE_URL}/flights:computeTypicalFlightEmissions"

    payload = {
        "markets": [
            {
                "origin": origin.upper(),
                "destination": destination.upper()
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                url,
                params={"key": API_KEY},
                json=payload
            )

            response.raise_for_status()

            data = response.json()
            emissions = data.get("typicalFlightEmissions", [])

            if not emissions:
                return None

            return emissions[0]

    except httpx.HTTPStatusError as e:
        logger.warning(
            "Google TIM typical emissions returned status %s",
            e.response.status_code
        )
        return None

    except (httpx.RequestError, ValueError) as e:
        logger.warning("Google TIM typical emissions failed: %s", e)
        return None