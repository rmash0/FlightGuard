import asyncio
import logging
import os
from pathlib import Path
from time import monotonic

import httpx
from dotenv import load_dotenv

OPENSKY_URL = "https://opensky-network.org/api/states/all"
OPENSKY_TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network/"
    "protocol/openid-connect/token"
)

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logger = logging.getLogger(__name__)


class _TokenManager:
    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at = 0.0
        self._credentials: tuple[str, str] | None = None
        self._lock = asyncio.Lock()

    async def get_token(
        self,
        client: httpx.AsyncClient,
        credentials: tuple[str, str],
        rejected_token: str | None = None,
    ) -> str:
        async with self._lock:
            if (
                self._credentials == credentials
                and self._token
                and self._expires_at > monotonic()
                and self._token != rejected_token
            ):
                return self._token

            response = await client.post(
                OPENSKY_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": credentials[0],
                    "client_secret": credentials[1],
                },
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("OpenSky token response has an invalid shape")
            token = payload.get("access_token")
            if not isinstance(token, str) or not token:
                raise ValueError("OpenSky token response is missing an access token")

            expires_in = float(payload.get("expires_in", 1800))
            self._token = token
            self._credentials = credentials
            self._expires_at = monotonic() + max(0.0, expires_in - 30.0)
            return token


_tokens = _TokenManager()


async def get_aircraft_in_area(
    lamin: float,
    lamax: float,
    lomin: float,
    lomax: float,
) -> dict:
    params = {
        "lamin": lamin,
        "lamax": lamax,
        "lomin": lomin,
        "lomax": lomax,
    }

    client_id = os.getenv("OPENSKY_CLIENT_ID", "").strip()
    client_secret = os.getenv("OPENSKY_CLIENT_SECRET", "").strip()
    if bool(client_id) != bool(client_secret):
        raise ValueError("OpenSky client ID and secret must both be configured")

    async with httpx.AsyncClient(timeout=15.0) as client:
        credentials = (client_id, client_secret)
        token = await _tokens.get_token(client, credentials) if client_id else None
        headers = {"Authorization": f"Bearer {token}"} if token else None
        response = await client.get(OPENSKY_URL, params=params, headers=headers)

        if response.status_code == 401 and token:
            token = await _tokens.get_token(client, credentials, rejected_token=token)
            response = await client.get(
                OPENSKY_URL,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )

        response.raise_for_status()
        data = response.json()

    flights = []

    for state in data.get("states") or []:
        if not isinstance(state, list) or len(state) < 17:
            continue

        longitude = state[5]
        latitude = state[6]

        if longitude is None or latitude is None:
            continue

        if state[8]:
            continue

        flights.append({
            "icao24": state[0],
            "callsign": (state[1] or "").strip(),
            "latitude": latitude,
            "longitude": longitude,
            "altitude": state[7],
            "velocity": state[9],
            "heading": state[10],
            "origin_country": state[2],
        })

    logger.info("OpenSky returned %s airborne aircraft", len(flights))

    return {
        "updated_at": data.get("time"),
        "flights": flights,
    }
