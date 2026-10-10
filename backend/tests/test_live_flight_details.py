import unittest
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import live_flight_details
from app.services.cache import TTLCache


class LiveFlightDetailsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        live_flight_details._details_cache = TTLCache()

    async def test_popup_details_match_active_aircraft_and_callsign(self):
        other_leg = {
            "number": "DL999",
            "callSign": "DAL999",
            "status": "Arrived",
            "aircraft": {"modeS": "a1b2c3"},
            "departure": {"airport": {"iata": "JFK"}},
        }
        active_leg = {
            "number": "DL214",
            "callSign": "DAL214",
            "status": "EnRoute",
            "aircraft": {"modeS": "A1B2C3"},
            "departure": {"airport": {"iata": "ATL", "name": "Atlanta"}},
            "arrival": {"airport": {"iata": "FCO", "name": "Rome"}},
        }
        provider = AsyncMock(return_value=[other_leg, active_leg])
        with patch.object(live_flight_details, "get_flights_by_icao24", provider):
            first = await live_flight_details.get_live_flight_details("a1b2c3", "DAL214")
            second = await live_flight_details.get_live_flight_details("a1b2c3", "DAL214")

        self.assertEqual(first.flight_number, "DL214")
        self.assertEqual(first.origin, "ATL — Atlanta")
        self.assertEqual(second.destination, "FCO — Rome")
        provider.assert_awaited_once_with("a1b2c3")

    async def test_no_unconfirmed_route_is_shown(self):
        provider = AsyncMock(return_value=[{
            "number": "DL214",
            "callSign": "DAL214",
            "status": "Scheduled",
            "aircraft": {"modeS": "a1b2c3"},
            "departure": {"airport": {"iata": "ATL"}},
        }])
        with patch.object(live_flight_details, "get_flights_by_icao24", provider):
            result = await live_flight_details.get_live_flight_details("a1b2c3", "DAL214")
        self.assertIsNone(result.flight_number)
        self.assertIsNone(result.origin)
        self.assertIsNone(result.destination)

    async def test_endpoint_validates_identifier_and_returns_contract(self):
        provider = AsyncMock(return_value=[])
        with patch.object(live_flight_details, "get_flights_by_icao24", provider):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                invalid = await client.get("/api/flights/live/invalid/details?callsign=DAL214")
                valid = await client.get("/api/flights/live/a1b2c3/details?callsign=DAL214")
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(valid.json(), {
            "flight_number": None,
            "origin": None,
            "destination": None,
        })


if __name__ == "__main__":
    unittest.main()
