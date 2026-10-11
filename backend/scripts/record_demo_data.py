"""Record real API responses into the frontend's demo data (frontend/src/mocks/demo/).

The hosted demo runs on these recordings, so it needs no backend or API keys.
This script makes real API calls with the keys in backend/.env:

- AeroDataBox: 2 airport-board calls for RDU, then one flight lookup per chosen
  flight (about 25-35 calls). Uses part of the monthly RapidAPI quota.
- Google TIM, Open-Meteo, FAA NAS: via the normal lookup and airport-status services.
- OpenSky: one US-wide snapshot of airborne aircraft.

It picks one flight from each major US city into RDU (or RDU to that city if
there's no arrival), plus a few RDU departures, spread across the day. It then adds
a few flights that are in the air right now, spread across the US, so map popups
link to full forecasts. Flights recorded earlier the same day are reused to save quota.

Outputs (all committed; the frontend imports them in demo mode):
flights.json, aircraft.json, live-details.json, airport-status.json, airports.json

Run from backend/:

    uv run python scripts/record_demo_data.py
"""

import asyncio
import json
import os
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
# Always record live data, whatever backend/.env says.
os.environ["DEMO_MODE"] = "false"

import httpx  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from app.clients.aerodatabox_client import BASE_URL, RAPIDAPI_HOST  # noqa: E402
from app.clients.opensky_client import get_aircraft_in_area  # noqa: E402
from app.services.delay_predictor import airport_status  # noqa: E402
from app.services.flight_lookup import lookup_flight  # noqa: E402
from app.services.live_flight_details import get_live_flight_details  # noqa: E402

OUT_DIR = BACKEND.parent / "frontend" / "src" / "mocks" / "demo"
HUB = "RDU"

# City -> airports. One flight from each city is recorded.
MAJOR_CITIES = {
    "New York": ["LGA", "JFK", "EWR"],
    "Los Angeles": ["LAX"],
    "Chicago": ["ORD", "MDW"],
    "Dallas": ["DFW", "DAL"],
    "Houston": ["IAH", "HOU"],
    "Atlanta": ["ATL"],
    "Denver": ["DEN"],
    "San Francisco": ["SFO"],
    "Seattle": ["SEA"],
    "Miami": ["MIA", "FLL"],
    "Boston": ["BOS"],
    "Phoenix": ["PHX"],
    "Las Vegas": ["LAS"],
    "Washington": ["DCA", "IAD", "BWI"],
    "Philadelphia": ["PHL"],
    "Charlotte": ["CLT"],
    "Orlando": ["MCO"],
    "Detroit": ["DTW"],
    "Minneapolis": ["MSP"],
}
RDU_DEPARTURES = 4
MAX_TRIES_PER_CITY = 3
# Spread picks across the day: some landed, some in the air, some upcoming.
TARGET_OFFSETS_HOURS = [-3, 0, 4]
# Keep the map snapshot small enough to bundle.
MAX_AIRCRAFT = 1500
# Extra demo flights taken from planes in the air, so map popups link to forecasts.
AIRBORNE_EXTRAS = 6
AIRBORNE_CARRIERS = {"DAL", "AAL", "UAL", "SWA", "JBU", "ASA"}
US_BOUNDS = (24.0, 50.0, -125.0, -66.0)


def _number(item: dict) -> str | None:
    raw = item.get("number")
    return "".join(raw.upper().split()) if isinstance(raw, str) else None


def _other_airport(item: dict, role: str) -> str | None:
    """IATA of the far end of a board entry. role: 'departure' for arrivals, 'arrival' for departures."""
    leg = item.get(role) or item.get("movement") or {}
    airport = leg.get("airport") or {}
    return airport.get("iata")


def _scheduled(item: dict, role: str) -> datetime | None:
    leg = item.get(role) or item.get("movement") or {}
    local = (leg.get("scheduledTime") or {}).get("local")
    if not local:
        return None
    try:
        return datetime.fromisoformat(local[:16])
    except ValueError:
        return None


async def fetch_board(day: date) -> dict:
    key = os.getenv("AERODATABOX_API_KEY")
    if not key:
        raise SystemExit("Set AERODATABOX_API_KEY in backend/.env first.")

    headers = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": RAPIDAPI_HOST}
    params = {
        "withLeg": "true",
        "direction": "Both",
        "withCancelled": "true",
        "withCodeshared": "false",
        "withCargo": "false",
        "withPrivate": "false",
        "withLocation": "false",
    }
    board = {"arrivals": [], "departures": []}
    # The board endpoint allows up to 12 hours per call.
    windows = [("00:00", "11:59"), ("12:00", "23:59")]
    async with httpx.AsyncClient(timeout=30.0) as client:
        for start, end in windows:
            url = f"{BASE_URL}/flights/airports/iata/{HUB}/{day}T{start}/{day}T{end}"
            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 204:
                continue
            response.raise_for_status()
            data = response.json()
            board["arrivals"] += data.get("arrivals", [])
            board["departures"] += data.get("departures", [])
    print(f"Board: {len(board['arrivals'])} arrivals, {len(board['departures'])} departures")
    return board


def pick_candidates(board: dict, now: datetime) -> list[tuple[str, list[str], set[str]]]:
    """Return (label, ordered flight numbers to try, acceptable far-end airports) per pick."""
    picks: list[tuple[str, list[str], set[str]]] = []

    def ranked(entries: list[tuple[str, datetime]], target: datetime) -> list[str]:
        entries = sorted(entries, key=lambda e: abs((e[1] - target).total_seconds()))
        seen, ordered = set(), []
        for number, _ in entries:
            if number not in seen:
                seen.add(number)
                ordered.append(number)
        return ordered

    for i, (city, airports) in enumerate(MAJOR_CITIES.items()):
        target = now + timedelta(hours=TARGET_OFFSETS_HOURS[i % len(TARGET_OFFSETS_HOURS)])
        arrivals = [
            (n, t)
            for item in board["arrivals"]
            if (n := _number(item)) and (t := _scheduled(item, "arrival"))
            and _other_airport(item, "departure") in airports
        ]
        departures = [
            (n, t)
            for item in board["departures"]
            if (n := _number(item)) and (t := _scheduled(item, "departure"))
            and _other_airport(item, "arrival") in airports
        ]
        options = ranked(arrivals, target) + ranked(departures, target)
        if options:
            picks.append((city, options, set(airports)))
        else:
            print(f"  no RDU flights for {city}; skipping")

    covered = {a for airports in MAJOR_CITIES.values() for a in airports}
    extra = [
        (n, t)
        for item in board["departures"]
        if (n := _number(item)) and (t := _scheduled(item, "departure"))
        and _other_airport(item, "arrival") not in covered
    ]
    for i in range(RDU_DEPARTURES):
        target = now + timedelta(hours=TARGET_OFFSETS_HOURS[i % len(TARGET_OFFSETS_HOURS)] + i)
        options = ranked(extra, target)
        if options:
            # Any far end is fine for these, as long as the leg touches RDU.
            picks.append((f"RDU departure {i + 1}", options, set()))
    return picks


def touches_hub(data: dict, far_ends: set[str]) -> bool:
    """Flight numbers can fly several legs a day; make sure we got the RDU leg."""
    origin = data["flight"]["origin"]["iata"]
    destination = data["flight"]["destination"]["iata"]
    if HUB not in (origin, destination):
        return False
    far = destination if origin == HUB else origin
    return not far_ends or far in far_ends


def load_previous() -> dict[str, dict]:
    """Reuse flights from an earlier run today to save API quota."""
    path = OUT_DIR / "flights.json"
    if not path.exists():
        return {}
    saved = json.loads(path.read_text(encoding="utf-8"))
    if saved.get("recorded_on") != date.today().isoformat():
        return {}
    return {f["flight"]["number"]: f for f in saved.get("flights", [])}


async def lookup_with_retry(number: str, day: date):
    """RapidAPI's basic plan allows about 1 request per second; back off on 502s from rate limits."""
    for attempt in range(3):
        await asyncio.sleep(1.5)
        try:
            return await lookup_flight(number, day)
        except HTTPException as exc:
            if exc.status_code != 502 or attempt == 2:
                raise
            await asyncio.sleep(5 * (attempt + 1))


async def record_flights(picks: list[tuple[str, list[str], set[str]]], day: date) -> list[dict]:
    previous = load_previous()
    flights: list[dict] = []
    used: set[str] = set()
    for label, options, far_ends in picks:
        reused = next(
            (previous[n] for n in options if n in previous and n not in used and touches_hub(previous[n], far_ends)),
            None,
        )
        if reused:
            used.add(reused["flight"]["number"])
            flights.append(reused)
            print(f"  {label}: {reused['flight']['number']} reused from earlier run")
            continue

        tries = 0
        for number in options:
            if number in used or tries >= MAX_TRIES_PER_CITY:
                continue
            tries += 1
            try:
                result = await lookup_with_retry(number, day)
            except HTTPException as exc:
                print(f"  {label}: {number} skipped ({exc.status_code} {exc.detail})")
                continue
            data = result.model_dump(mode="json")
            if not touches_hub(data, far_ends):
                route = f"{data['flight']['origin']['iata']}->{data['flight']['destination']['iata']}"
                print(f"  {label}: {number} skipped (lookup returned another leg, {route})")
                continue
            used.add(number)
            flight = data["flight"]
            print(
                f"  {label}: {number} {flight['origin']['iata']}->{flight['destination']['iata']} "
                f"{flight['status']} | risk {data['prediction'] and data['prediction']['risk']} "
                f"| co2 {'yes' if data['emissions'] else 'no'}"
            )
            flights.append(data)
            break
    return flights


def airborne_demo_flights(demo_flights: list[dict]) -> dict[str, dict]:
    """Demo flights in the air at recording time, keyed by lowercase Mode-S code.

    Only these get tied to a plane on the map: an aircraft that already landed
    may be flying a different flight number by the time of the snapshot.
    AeroDataBox reports Mode-S codes uppercase; OpenSky uses lowercase.
    """
    return {
        f["flight"]["icao24"].lower(): f
        for f in demo_flights
        if f["flight"].get("icao24") and f["flight"]["status"] in ("departed", "en_route")
    }


async def take_snapshot() -> tuple[int | None, list[dict]]:
    snapshot = await get_aircraft_in_area(*US_BOUNDS)
    airborne = [
        f for f in snapshot.get("flights", [])
        if f.get("latitude") is not None and f.get("longitude") is not None
        and (f.get("altitude") or 0) > 300
    ]
    return snapshot.get("updated_at"), airborne


async def record_airborne_extras(
    airborne: list[dict], flights: list[dict], day: date
) -> list[dict]:
    """Add a few demo flights that are in the air in this snapshot, spread across the US,
    so the map has planes whose popup links to a full forecast."""
    have = {f["flight"]["number"] for f in flights}
    candidates = [
        p for p in airborne
        if p.get("callsign", "").strip()[:3] in AIRBORNE_CARRIERS
        and (p.get("altitude") or 0) > 6000
    ]
    # Rotate through longitude bands (west, central, east...) so picks spread across the map.
    bands: dict[int, list[dict]] = {}
    for plane in candidates:
        bands.setdefault(int((plane["longitude"] + 125) // 10), []).append(plane)
    rng = random.Random(day.toordinal())
    for planes in bands.values():
        rng.shuffle(planes)
    ordered = []
    for round_index in range(3):
        for band in sorted(bands):
            if round_index < len(bands[band]):
                ordered.append(bands[band][round_index])

    extras: list[dict] = []
    for plane in ordered:
        if len(extras) >= AIRBORNE_EXTRAS:
            break
        await asyncio.sleep(1.5)
        details = await get_live_flight_details(plane["icao24"].lower(), plane["callsign"].strip())
        number = details.flight_number
        if not number or number in have:
            continue
        try:
            result = await lookup_with_retry(number, day)
        except HTTPException as exc:
            print(f"  in the air: {number} skipped ({exc.status_code} {exc.detail})")
            continue
        data = result.model_dump(mode="json")
        flight = data["flight"]
        if (flight.get("icao24") or "").lower() != plane["icao24"].lower() or flight["status"] not in ("departed", "en_route"):
            print(f"  in the air: {number} skipped (lookup returned a different leg or aircraft)")
            continue
        have.add(number)
        extras.append(data)
        print(
            f"  in the air: {number} {flight['origin']['iata']}->{flight['destination']['iata']} "
            f"| risk {data['prediction'] and data['prediction']['risk']}"
        )
    return extras


def build_aircraft(updated_at: int | None, airborne: list[dict], demo_flights: list[dict]) -> dict:
    demo_icao = set(airborne_demo_flights(demo_flights))
    keep = [f for f in airborne if f["icao24"].lower() in demo_icao]
    rest = [f for f in airborne if f["icao24"].lower() not in demo_icao]
    random.Random(2026).shuffle(rest)
    keep += rest[: max(0, MAX_AIRCRAFT - len(keep))]
    on_map = sorted(f["callsign"].strip() for f in keep if f["icao24"].lower() in demo_icao)
    print(f"Aircraft: {len(airborne)} airborne, kept {len(keep)}; demo flights on the map: {on_map or 'none'}")
    return {"updated_at": updated_at, "flights": keep}


def live_details(demo_flights: list[dict], aircraft: dict) -> dict:
    """Popup details for demo flights that are actually in the map snapshot."""
    details = {}
    airborne = airborne_demo_flights(demo_flights)
    on_map = {plane["icao24"].lower() for plane in aircraft["flights"]}
    for data in demo_flights:
        flight = data["flight"]
        code = (flight.get("icao24") or "").lower()
        if code in airborne and code in on_map:
            details[flight["icao24"].lower()] = {
                "flight_number": flight["number"],
                "origin": f"{flight['origin']['iata']} — {flight['origin']['name']}",
                "destination": f"{flight['destination']['iata']} — {flight['destination']['name']}",
            }
    return details


async def record_airport_status(demo_flights: list[dict]) -> dict:
    codes = sorted(
        {f["flight"]["origin"]["iata"] for f in demo_flights}
        | {f["flight"]["destination"]["iata"] for f in demo_flights}
    )
    statuses = {}
    for code in codes:
        status = await airport_status(code)
        if status is not None:
            statuses[code] = status.model_dump(mode="json")
    print(f"Airport status: {len(statuses)} airports")
    return statuses


def write(name: str, payload: object) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {path.relative_to(BACKEND.parent)} ({path.stat().st_size // 1024} KB)")


async def main() -> None:
    now = datetime.now()
    day = now.date()
    print(f"Recording demo data for {day}")

    board = await fetch_board(day)
    picks = pick_candidates(board, now)
    flights = await record_flights(picks, day)
    if not flights:
        raise SystemExit("No flights recorded; check the API key and quota.")

    updated_at, airborne = await take_snapshot()
    flights += await record_airborne_extras(airborne, flights, day)
    aircraft = build_aircraft(updated_at, airborne, flights)
    statuses = await record_airport_status(flights)
    airports = json.loads((BACKEND / "app" / "data" / "airports.json").read_text(encoding="utf-8"))

    write("flights.json", {"recorded_on": day.isoformat(), "flights": flights})
    write("aircraft.json", aircraft)
    write("live-details.json", live_details(flights, aircraft))
    write("airport-status.json", statuses)
    write("airports.json", airports)


if __name__ == "__main__":
    asyncio.run(main())
