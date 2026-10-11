"""GET /api/airports/{iata}

Role D owns the airport list (`GET /api/airports`). This route is the
single-airport status: weather, FAA programs, and delay risk.
"""

from fastapi import APIRouter, HTTPException

from app.services.delay_predictor import airport_status
from app.services.prediction_models import AirportStatus

router = APIRouter(prefix="/airports", tags=["airports"])


@router.get("/{iata}", response_model=AirportStatus)
async def get_airport_status(iata: str) -> AirportStatus:
    status = await airport_status(iata)
    if status is None:
        raise HTTPException(
            status_code=404,
            detail=f"No status for airport {iata.strip().upper()}",
        )
    return status
