from fastapi import APIRouter

router = APIRouter(prefix="/flights", tags=["flights"])


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
