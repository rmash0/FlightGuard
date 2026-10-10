
from datetime import date as Date

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import Emissions
from app.services.emissions import get_emissions

router = APIRouter(prefix="/eco", tags=["Eco"])


@router.get("/emissions", response_model=Emissions)
async def get_flight_co2_emissions(
    carrier: str = Query(..., min_length=2, max_length=3),
    number: int = Query(..., ge=1),
    origin: str = Query(..., min_length=3, max_length=3),
    destination: str = Query(..., min_length=3, max_length=3),
    date: Date = Query(...),
    origin_lat: float | None = Query(None, ge=-90, le=90),
    origin_lon: float | None = Query(None, ge=-180, le=180),
    destination_lat: float | None = Query(None, ge=-90, le=90),
    destination_lon: float | None = Query(None, ge=-180, le=180),
):
    result = await get_emissions(
        origin=origin,
        destination=destination,
        carrier=carrier,
        flight_number=number,
        departure_date=date,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        destination_lat=destination_lat,
        destination_lon=destination_lon,
    )

    if result is None:
        raise HTTPException(
            status_code=503,
            detail="Emissions data is currently unavailable for this flight",
        )

    return result
