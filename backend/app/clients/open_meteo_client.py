"""Open-Meteo forecast client.

Thin wrapper: one request can cover several airports. Scoring lives in
`services/delay_predictor.py`. Cached about 45 minutes per rounded
coordinate and date range.
"""

import json
import logging
from datetime import date
from pathlib import Path

import httpx

from app.clients.memory_cache import MemoryCache
from app.services.settings import demo_mode, open_meteo_base_url

logger = logging.getLogger(__name__)

HOURLY_FIELDS = (
    "weather_code,precipitation,precipitation_probability,visibility,"
    "wind_speed_10m,wind_gusts_10m,cloud_cover,temperature_2m"
)
CACHE_TTL_SECONDS = 45 * 60
FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "fixtures" / "open_meteo_rdu_atl.json"
)
USER_AGENT = "FlightGuard/0.1 (HackNC educational project)"

_cache = MemoryCache()


def clear_cache() -> None:
    _cache.clear()


async def get_forecast(
    points: list[tuple[float, float]],
    start_date: date,
    end_date: date | None = None,
) -> list[dict | None]:
    """Hourly forecast for each (lat, lon), in the same order.

    A missing airport comes back as None. Raises httpx.HTTPError when the
    live call fails and demo mode is off.
    """
    if not points:
        return []
    end = end_date or start_date
    if demo_mode():
        return _from_fixture(points, start_date)

    keys = [
        f"{round(lat, 2):.2f},{round(lon, 2):.2f},{start_date.isoformat()},{end.isoformat()}"
        for lat, lon in points
    ]
    cached = [_cache.get(key) for key in keys]
    if all(item is not None for item in cached):
        return [item if isinstance(item, dict) else None for item in cached]

    params = {
        "latitude": ",".join(f"{lat:.4f}" for lat, _ in points),
        "longitude": ",".join(f"{lon:.4f}" for _, lon in points),
        "hourly": HOURLY_FIELDS,
        "wind_speed_unit": "kn",
        "timezone": "GMT",
        "start_date": start_date.isoformat(),
        "end_date": end.isoformat(),
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            open_meteo_base_url(),
            params=params,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        payload = response.json()

    rows = payload if isinstance(payload, list) else [payload]
    result: list[dict | None] = []
    for index in range(len(points)):
        row = rows[index] if index < len(rows) and isinstance(rows[index], dict) else None
        result.append(row)
        if row is not None:
            _cache.set(keys[index], row, CACHE_TTL_SECONDS)
    if len(rows) != len(points):
        logger.warning(
            "Open-Meteo returned %s location(s) for %s requested",
            len(rows),
            len(points),
        )
    return result


def _from_fixture(points: list[tuple[float, float]], day: date) -> list[dict | None]:
    entries = json.loads(FIXTURE_PATH.read_text())
    if isinstance(entries, dict):
        entries = [entries]
    located: list[tuple[float, float, dict]] = []
    for entry in entries:
        lat = entry.get("latitude")
        lon = entry.get("longitude")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            located.append((float(lat), float(lon), entry))

    matched: list[dict | None] = []
    for lat, lon in points:
        best: dict | None = None
        best_distance = 0.75
        for fixture_lat, fixture_lon, payload in located:
            distance = abs(fixture_lat - lat) + abs(fixture_lon - lon)
            if distance < best_distance:
                best_distance = distance
                best = payload
        matched.append(_shift_times(best, day) if best is not None else None)
    return matched


def _shift_times(payload: dict, day: date) -> dict:
    """Replay a recorded day against the date the caller asked for."""
    shifted = json.loads(json.dumps(payload))
    hourly = shifted.get("hourly")
    if not isinstance(hourly, dict):
        return shifted
    times = hourly.get("time")
    if not isinstance(times, list):
        return shifted
    hourly["time"] = [
        f"{day.isoformat()}T{str(stamp).split('T', 1)[1]}" if "T" in str(stamp) else stamp
        for stamp in times
    ]
    return shifted
