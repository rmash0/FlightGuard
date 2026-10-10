import httpx

OPENSKY_URL = "https://opensky-network.org/api/states/all"


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

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(OPENSKY_URL, params=params)
        response.raise_for_status()
        return response.json()
