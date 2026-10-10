
import csv
import io
import json
from pathlib import Path
from urllib.request import urlopen

AIRPORTS_URL = (
    "https://raw.githubusercontent.com/"
    "davidmegginson/ourairports-data/main/airports.csv"
)

OUTPUT_FILE = Path(__file__).resolve().parent / "airports.json"

AIRPORT_TYPES = {"large_airport", "medium_airport"}


def generate_airports():
    print("Downloading OurAirports dataset...")

    with urlopen(AIRPORTS_URL, timeout=30) as response:
        content = response.read().decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(content))
    airports = []

    for row in reader:
        if row["iso_country"] != "US":
            continue

        if row["type"] not in AIRPORT_TYPES:
            continue

        iata = row["iata_code"].strip()

        if len(iata) != 3 or not iata.isalpha():
            continue

        try:
            lat = float(row["latitude_deg"])
            lon = float(row["longitude_deg"])
        except (TypeError, ValueError):
            continue

        airports.append({
            "iata": iata,
            "name": row["name"],
            "lat": lat,
            "lon": lon,
            "type": row["type"]
        })

    airports.sort(key=lambda airport: airport["iata"])

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(airports, file, indent=2, ensure_ascii=False)

    print(f"Saved {len(airports)} airports to {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_airports()
