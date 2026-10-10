from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import date
import os
import httpx
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_URL = (
    "https://travelimpactmodel.googleapis.com"
    "/v1/flights:computeFlightEmissions"
)

router = APIRouter(prefix="/eco", tags=["eco"])

class FlightRequest(BaseModel):
    origin: str
    destination: str
    operatingCarrierCode: str
    flightNumber: int
    departureDate: date

@router.post("/emissions")
async def get_co2_emissions(flight: FlightRequest):
    if not GOOGLE_API_KEY:
        raise HTTPException(
            status_code = 500, 
            detail = "Google API key is not set"
        )
    
    payload = {
        "flights" : [
            {
                "origin": flight.origin.upper(),
                "destination": flight.destination.upper(),
                "operatingCarrierCode": flight.operatingCarrierCode.upper(),
                "flightNumber": flight.flightNumber,
                "departureDate": {
                    "year": flight.departureDate.year, 
                    "month": flight.departureDate.month, 
                    "day": flight.departureDate.day
                }
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                GOOGLE_URL,
                params = {"key": GOOGLE_API_KEY},
                json=payload
            )

            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.text
        )
        
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail="Unable to reach Google Travel Impact Model API"
        )