
from typing import Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel

from app.services.airport_directory import list_airports

router = APIRouter(prefix="/airports", tags=["Live Map"])

# The list is static data from OurAirports, so browsers can keep it for a day.
CACHE_SECONDS = 86400


class MapAirport(BaseModel):
    iata: str
    name: str
    lat: float
    lon: float
    type: Literal["large_airport", "medium_airport"]


@router.get("", response_model=list[MapAirport])
async def get_airports(response: Response):
    response.headers["Cache-Control"] = f"public, max-age={CACHE_SECONDS}"
    return list_airports()
