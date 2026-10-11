"""Backend mirror of the FlightLookupResponse contract in AGENTS.md §8."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


FlightStatus = Literal[
    "scheduled", "delayed", "departed", "en_route", "landed", "cancelled", "unknown"
]
RiskLevel = Literal["low", "medium", "high"]
ImpactLevel = Literal["low", "medium", "high"]
EstimateTier = Literal["flight", "route", "distance", "fallback"]


class Airline(BaseModel):
    iata: str
    name: str


class Airport(BaseModel):
    iata: str
    name: str
    lat: float
    lon: float


class Flight(BaseModel):
    number: str
    airline: Airline
    date: date
    origin: Airport
    destination: Airport
    scheduled_departure: datetime
    scheduled_arrival: datetime
    estimated_departure: datetime | None
    actual_departure: datetime | None
    status: FlightStatus
    aircraft_type: str | None
    icao24: str | None


class DelayReason(BaseModel):
    factor: str
    detail: str
    impact: ImpactLevel


class DelayPrediction(BaseModel):
    risk: RiskLevel
    probability_delayed: float = Field(ge=0, le=1)
    estimated_delay_minutes: int
    reported_delay_minutes: int | None
    reasons: list[DelayReason]
    model: str


class CabinEmissions(BaseModel):
    economy: float
    premium_economy: float
    business: float
    first: float


class EcoComparison(BaseModel):
    label: str
    value: float


class Emissions(BaseModel):
    co2e_kg_per_passenger: CabinEmissions
    estimate_tier: EstimateTier
    source: str
    comparisons: list[EcoComparison]


class FlightLookupResponse(BaseModel):
    flight: Flight
    prediction: DelayPrediction | None
    emissions: Emissions | None


class LiveFlightDetails(BaseModel):
    flight_number: str | None
    origin: str | None
    destination: str | None


class HourlyDelayRate(BaseModel):
    hour: int = Field(ge=0, le=23)
    delay_rate: float
    flights: int
    mean_delay_minutes: float


class ModelInfo(BaseModel):
    """GET /api/predict/model. Accuracy for the About page, plus chart data."""

    model: str
    test_auc: float | None = None
    base_rate: float | None = None
    train_months: list[str]
    calibration_month: str | None = None
    test_month: str | None = None
    months: list[str]
    hourly_delay_rate: list[HourlyDelayRate]
