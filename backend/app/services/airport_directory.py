
import json
from functools import lru_cache
from pathlib import Path

AIRPORTS_FILE = Path(__file__).resolve().parents[1] / "data" / "airports.json"


@lru_cache(maxsize=1)
def list_airports() -> tuple[dict, ...]:
    # OurAirports names include non-ASCII characters, so always read as UTF-8.
    with AIRPORTS_FILE.open(encoding="utf-8") as file:
        return tuple(json.load(file))


@lru_cache(maxsize=1)
def _airport_index() -> dict[str, dict]:
    return {airport["iata"]: airport for airport in list_airports()}


def find_airport(iata: str) -> dict | None:
    return _airport_index().get(iata.strip().upper())
