import asyncio
import unittest
from unittest.mock import patch

import httpx

from app.api import routes_live
from app.clients import opensky_client
from app.main import app
from app.services.cache import TTLCache


AIRCRAFT = {
    "time": 1234567890,
    "states": [[
        "a1b2c3", "DAL214 ", "United States", None, None,
        -78.8, 35.9, 1000, False, 200, 90, None, None, None, None, False, 0,
    ]],
}
REAL_ASYNC_CLIENT = httpx.AsyncClient


class OpenSkyClientTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        opensky_client._tokens = opensky_client._TokenManager()
        routes_live.aircraft_cache = TTLCache()
        self.env = patch.dict(
            opensky_client.os.environ,
            {"OPENSKY_CLIENT_ID": "test-client", "OPENSKY_CLIENT_SECRET": "test-secret"},
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    async def test_authenticated_requests_share_one_token(self):
        requests = []

        def handle(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url.path.endswith("/token"):
                self.assertIn(b"client_id=test-client", request.content)
                self.assertIn(b"client_secret=test-secret", request.content)
                return httpx.Response(200, json={"access_token": "token-one", "expires_in": 1800})
            self.assertEqual(request.headers.get("authorization"), "Bearer token-one")
            return httpx.Response(200, json=AIRCRAFT)

        with patch.object(
            opensky_client.httpx,
            "AsyncClient",
            side_effect=lambda **kwargs: REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handle)),
        ):
            first, second = await asyncio.gather(
                opensky_client.get_aircraft_in_area(35, 36, -79, -78),
                opensky_client.get_aircraft_in_area(35, 36, -79, -78),
            )

        self.assertEqual(first, second)
        self.assertEqual(first["flights"][0]["callsign"], "DAL214")
        self.assertEqual(sum(request.url.path.endswith("/token") for request in requests), 1)

    async def test_unauthorized_state_request_refreshes_token_once(self):
        issued = []
        used = []

        def handle(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/token"):
                token = f"token-{len(issued) + 1}"
                issued.append(token)
                return httpx.Response(200, json={"access_token": token, "expires_in": 1800})
            used.append(request.headers.get("authorization"))
            if len(used) == 1:
                return httpx.Response(401)
            return httpx.Response(200, json=AIRCRAFT)

        with patch.object(
            opensky_client.httpx,
            "AsyncClient",
            side_effect=lambda **kwargs: REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handle)),
        ):
            result = await opensky_client.get_aircraft_in_area(35, 36, -79, -78)

        self.assertEqual(len(result["flights"]), 1)
        self.assertEqual(issued, ["token-1", "token-2"])
        self.assertEqual(used, ["Bearer token-1", "Bearer token-2"])

    async def test_token_rejection_returns_service_error_from_map_endpoint(self):
        def handle(request: httpx.Request) -> httpx.Response:
            self.assertTrue(request.url.path.endswith("/token"))
            return httpx.Response(401, json={"error": "unauthorized_client"})

        with patch.object(
            opensky_client.httpx,
            "AsyncClient",
            side_effect=lambda **kwargs: REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handle)),
        ):
            async with REAL_ASYNC_CLIENT(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/flights/live?lamin=35&lamax=36&lomin=-79&lomax=-78"
                )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"], "OpenSky API client authentication failed"
        )


if __name__ == "__main__":
    unittest.main()
