"""GET /api/predict?number=&date=

Resolves the flight through Role B's `lookup_flight`, then scores it with
`predict_delay` (cached per flight, so lookup's own call is reused). When
lookup has no data (no API key, or no demo fixture for that date), DL1234
still resolves from a small sample catalog.
"""

from datetime import date as Date

from fastapi import APIRouter, HTTPException, Query

from app.services.delay_predictor import predict_delay
from app.services.flight_lookup import lookup_flight
from app.services.prediction_models import Airline, Airport, DelayPrediction, Flight

router = APIRouter(tags=["predict"])

# Clock times stay on the sample offset. Live lookup will supply the real ones.
_DEMO_FLIGHTS = {
    "DL1234": {
        "airline": ("DL", "Delta Air Lines"),
        "origin": ("RDU", "Raleigh-Durham Intl", 35.88, -78.79),
        "destination": ("ATL", "Hartsfield-Jackson Atlanta Intl", 33.64, -84.43),
        "departure": "14:05:00-04:00",
        "arrival": "15:40:00-04:00",
        "aircraft_type": "B739",
    }
}


@router.get("/predict", response_model=DelayPrediction)
async def predict(
    number: str = Query(description="Flight number, such as DL1234"),
    flight_date: Date = Query(alias="date", description="Departure date"),
) -> DelayPrediction:
    try:
        flight = (await lookup_flight(number, flight_date)).flight
    except HTTPException as exc:
        flight = demo_flight(number, flight_date)
        if flight is None or exc.status_code not in (404, 503):
            raise
    prediction = await predict_delay(flight)
    if prediction is None:
        raise HTTPException(status_code=503, detail="Delay prediction is unavailable right now")
    return prediction


def demo_flight(number: str, flight_date: Date) -> Flight | None:
    template = _DEMO_FLIGHTS.get(_normalize(number))
    if template is None:
        return None
    origin = template["origin"]
    destination = template["destination"]
    airline = template["airline"]
    day = flight_date.isoformat()
    return Flight(
        number=_normalize(number),
        airline=Airline(iata=airline[0], name=airline[1]),
        date=day,
        origin=Airport(iata=origin[0], name=origin[1], lat=origin[2], lon=origin[3]),
        destination=Airport(
            iata=destination[0],
            name=destination[1],
            lat=destination[2],
            lon=destination[3],
        ),
        scheduled_departure=f"{day}T{template['departure']}",
        scheduled_arrival=f"{day}T{template['arrival']}",
        status="scheduled",
        aircraft_type=str(template["aircraft_type"]),
    )


def _normalize(number: str) -> str:
    return "".join(number.split()).upper()
