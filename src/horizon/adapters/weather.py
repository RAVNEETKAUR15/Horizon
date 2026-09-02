import json
import os
import time

import requests

REGIONS = {
    "CISO": {"lat": 34.05, "lon": -118.24, "city": "Los Angeles"},
    "ERCO": {"lat": 29.76, "lon": -95.37, "city": "Houston"},
    "PJM":  {"lat": 39.95, "lon": -75.17, "city": "Philadelphia"},
    "MISO": {"lat": 41.88, "lon": -87.63, "city": "Chicago"},
    "ISNE": {"lat": 42.36, "lon": -71.06, "city": "Boston"},
    "NYIS": {"lat": 40.71, "lon": -74.01, "city": "New York"},
    "BPAT": {"lat": 45.52, "lon": -122.68, "city": "Portland"},
    "FPL":  {"lat": 25.76, "lon": -80.19, "city": "Miami"},
}

VARIABLES = {
    "temperature_2m",
    "dewpoint_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "cloud_cover",
    "shortwave_radiation",
}

def fetch_weather(lat, lon, start_date, end_date):
    """Fetch hourly weather for one location. Resturn the parsed JSON body."""

    response = requests.get("https://archive-api.open-meteo.com/v1/archive",
    params = {
        "latitude": lat, 
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(VARIABLES),
        "timezone": "UTC",
    },
    timeout=60,
    )
    response.raise_for_status()
    return response.json()

if __name__ =="__main__":
    START = "2019-01-01"
    END = "2026-07-31"

    os.makedirs("data/raw", exist_ok=True)

    for region, info in REGIONS.items():
        print(f"Fetching weather for {region} ({info['city']})...")
        body = fetch_weather(info["lat"], info['lon'], START, END)
        path = f"data/raw/{region}_weather.json"
        with open(path, "w") as f:
            json.dump(body, f)

        n_hours = len(body["hourly"]["time"])
        print(f" saved {n_hours:,} hours to {path}\n")
        time.sleep(2)