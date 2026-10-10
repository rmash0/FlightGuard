import re
from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import FlightLookupResponse
from app.services.flight_lookup import lookup_flight

router = APIRouter(prefix="/flights", tags=["flights"])


@router.get("/lookup", response_model=FlightLookupResponse)
async def lookup(number: str = Query(...), date: date = Query(...)) -> FlightLookupResponse:
    normalized = "".join(number.upper().split())
    if not re.fullmatch(r"[A-Z0-9]{2}[0-9]{1,4}", normalized):
        raise HTTPException(status_code=422, detail="Use an IATA flight number such as DL1234")
    return await lookup_flight(normalized, date)


@router.get("/demo")
def demo_flights():
    return {
        "updated_at": "demo",
        "flights": [
            {
                "icao24": "demo123",
                "callsign": "DEMO123",
                "latitude": 35.88,
                "longitude": -78.78,
                "altitude": 10000,
                "velocity": 220,
                "heading": 90,
                "origin_country": "United States",
            }
        ],
    }
