"""FAA NAS Status client.

Fetches one XML document for the whole US and parses it into events keyed
by airport code. No scoring. The feed only lists airports with an active
program; everyone else is operating normally.

Verified against the live document on 2026-10-10: ground-delay, general
arrival/departure delay, and airport-closure blocks. Ground stops were
absent that hour, so `faa_nas_stormy.xml` covers that branch.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

from app.services.cache import TTLCache
from app.services.settings import demo_mode, faa_nas_url

CACHE_TTL_SECONDS = 3 * 60
FIXTURES = Path(__file__).resolve().parents[1] / "data" / "fixtures"
STORMY_FIXTURE = FIXTURES / "faa_nas_stormy.xml"
USER_AGENT = "FlightGuard/0.1 (HackNC educational project)"

_cache: TTLCache[dict] = TTLCache()
_HOUR = re.compile(r"(\d+)\s*hours?", re.IGNORECASE)
_MINUTE = re.compile(r"(\d+)\s*minutes?", re.IGNORECASE)


def clear_cache() -> None:
    global _cache
    _cache = TTLCache()


async def get_airport_events() -> dict[str, list[dict]]:
    """Active NAS events keyed by airport code. Values may be empty."""
    if demo_mode():
        return parse_faa_xml(STORMY_FIXTURE.read_text())
    return await _cache.get_or_set("nas", CACHE_TTL_SECONDS, _fetch_events)


async def _fetch_events() -> dict[str, list[dict]]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            faa_nas_url(),
            headers={"User-Agent": USER_AGENT, "Accept": "application/xml"},
        )
        response.raise_for_status()
        return parse_faa_xml(response.text)


def parse_duration_minutes(text: str | None) -> int | None:
    """Turn '1 hour and 12 minutes' into 72. Returns None if it isn't a duration."""
    if not text:
        return None
    hours = _HOUR.search(text)
    minutes = _MINUTE.search(text)
    if hours is None and minutes is None:
        return None
    total = 0
    if hours is not None:
        total += int(hours.group(1)) * 60
    if minutes is not None:
        total += int(minutes.group(1))
    return total


def parse_faa_xml(xml_text: str) -> dict[str, list[dict]]:
    """Parse NAS Status XML into `{IATA: [event, ...]}`."""
    root = ET.fromstring(xml_text)
    events: dict[str, list[dict]] = {}
    for node in root.iter():
        name = _local(node.tag)
        if name == "Ground_Stop_List":
            for program in _descendants(node, "Program"):
                _add(events, _event_from_program(program))
        elif name == "Ground_Delay_List":
            for delay in _descendants(node, "Ground_Delay"):
                _add(events, _event_from_ground_delay(delay))
        elif name == "Arrival_Departure_Delay_List":
            for delay in _descendants(node, "Delay"):
                _add(events, _event_from_general_delay(delay))
        elif name == "Airport_Closure_List":
            for closure in _descendants(node, "Airport"):
                _add(events, _event_from_closure(closure))
    return events


def _event_from_program(node: ET.Element) -> dict | None:
    iata = _text(node, "ARPT")
    if not iata:
        return None
    return {
        "iata": iata,
        "type": "ground_stop",
        "reason": _text(node, "Reason") or "unspecified",
        "avg_minutes": None,
        "max_minutes": None,
        "end_time": _text(node, "End_Time"),
    }


def _event_from_ground_delay(node: ET.Element) -> dict | None:
    iata = _text(node, "ARPT")
    if not iata:
        return None
    return {
        "iata": iata,
        "type": "ground_delay",
        "reason": _text(node, "Reason") or "unspecified",
        "avg_minutes": parse_duration_minutes(_text(node, "Avg")),
        "max_minutes": parse_duration_minutes(_text(node, "Max")),
        "end_time": None,
    }


def _event_from_general_delay(node: ET.Element) -> dict | None:
    iata = _text(node, "ARPT")
    if not iata:
        return None
    # A delay can list arrival and departure. Keep the worse minimum.
    lowest: int | None = None
    highest: int | None = None
    for window in _children(node, "Arrival_Departure"):
        parsed_min = parse_duration_minutes(_text(window, "Min"))
        parsed_max = parse_duration_minutes(_text(window, "Max"))
        if parsed_min is not None and (lowest is None or parsed_min > lowest):
            lowest = parsed_min
            highest = parsed_max
    return {
        "iata": iata,
        "type": "general_delay",
        "reason": _text(node, "Reason") or "unspecified",
        "avg_minutes": lowest,
        "max_minutes": highest,
        "end_time": None,
    }


def _event_from_closure(node: ET.Element) -> dict | None:
    iata = _text(node, "ARPT")
    if not iata:
        return None
    return {
        "iata": iata,
        "type": "closure",
        "reason": _text(node, "Reason") or "unspecified",
        "avg_minutes": None,
        "max_minutes": None,
        "end_time": _text(node, "Reopen"),
    }


def _add(events: dict[str, list[dict]], event: dict | None) -> None:
    if event is None:
        return
    iata = str(event.pop("iata")).strip().upper()
    if not iata:
        return
    events.setdefault(iata, []).append(event)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(node: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(node) if _local(child.tag) == name]


def _descendants(node: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in node.iter() if _local(child.tag) == name]


def _text(node: ET.Element, name: str) -> str | None:
    for child in list(node):
        if _local(child.tag) == name and child.text:
            cleaned = " ".join(child.text.split())
            if cleaned:
                return cleaned
    return None
