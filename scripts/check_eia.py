import os
import requests
from dotenv import load_dotenv

load_dotenv()                          # reads .env into the environment
api_key = os.environ["EIA_API_KEY"]    # crashes loudly if it's missing — good

response = requests.get(
    "https://api.eia.gov/v2/electricity/rto/region-data/data/",
    params={
        "api_key": api_key,
        "frequency": "hourly",
        "data[0]": "value",
        "facets[respondent][]": "CISO",   # California ISO
        "facets[type][]": "D",            # D = actual demand
        "start": "2026-08-01T00",
        "end": "2026-08-02T00",
        "length": 24,
    },
    timeout=30,
)

response.raise_for_status()            # raises an error on 4xx/5xx instead of failing silently

rows = response.json()["response"]["data"]
print(f"Got {len(rows)} rows")
for row in rows[:3]:
    print(row)