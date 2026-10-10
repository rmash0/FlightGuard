"""Checked-in, synthetic lookup fixtures for offline demos."""

import json
from datetime import date
from pathlib import Path

from app.models.schemas import FlightLookupResponse

FIXTURES = Path(__file__).resolve().parent.parent / "data" / "fixtures"


def get_demo_lookup(number: str, departure_date: date) -> FlightLookupResponse | None:
    path = FIXTURES / f"{number}_{departure_date.isoformat()}.json"
    if not path.is_file():
        return None
    return FlightLookupResponse.model_validate(json.loads(path.read_text(encoding="utf-8")))
