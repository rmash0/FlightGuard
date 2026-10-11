"""Pydantic models for delay prediction.

These match AGENTS.md §8 and the AirportStatus shape. Role B owns
`models/schemas.py`. `DelayReason` and `DelayPrediction` subclass B's
models so lookup's `schemas.DelayPrediction.model_validate` accepts them
while this service still checks the `factor` enum. `Flight` keeps times
as ISO strings; `extra="ignore"` lets B pass additional flight fields
(distance_km, estimated_arrival) without this service rejecting them.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models import schemas


class Airline(BaseModel):
    model_config = ConfigDict(extra="ignore")

    iata: str
    name: str


class Airport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    iata: str
    name: str
    lat: float
    lon: float


class Flight(BaseModel):
    model_config = ConfigDict(extra="ignore")

    number: str
    airline: Airline
    date: str
    origin: Airport
    destination: Airport
    scheduled_departure: str
    scheduled_arrival: str
    estimated_departure: str | None = None
    actual_departure: str | None = None
    status: Literal[
        "scheduled",
        "delayed",
        "departed",
        "en_route",
        "landed",
        "cancelled",
        "unknown",
    ] = "unknown"
    aircraft_type: str | None = None
    icao24: str | None = None
    # Not on the shared flight contract yet. Used when lookup starts sending
    # AeroDataBox greatCircleDistance; otherwise the predictor computes it.
    distance_km: float | None = None


class DelayReason(schemas.DelayReason):
    factor: Literal[  # type: ignore[assignment]
        "weather_origin",
        "weather_destination",
        "faa_origin",
        "faa_destination",
        "time_of_day",
        "day_of_week",
        "season",
        "historical_route",
        "reported_delay",
    ]


class DelayPrediction(schemas.DelayPrediction):
    reported_delay_minutes: int | None = None
    reasons: list[DelayReason]  # type: ignore[assignment]


class FaaEventModel(BaseModel):
    type: Literal["ground_stop", "ground_delay", "general_delay", "closure"]
    reason: str
    avg_minutes: int | None = None
    max_minutes: int | None = None
    end_time: str | None = None


class AirportWeather(BaseModel):
    time: str | None = None
    weather_code: int | None = None
    description: str
    wind_gusts_kt: float | None = None
    visibility_m: float | None = None
    precipitation_mm: float | None = None


class AirportStatus(BaseModel):
    iata: str
    name: str
    weather: AirportWeather | None = None
    faa_events: list[FaaEventModel]
    risk: Literal["low", "medium", "high"]
    reasons: list[DelayReason]
