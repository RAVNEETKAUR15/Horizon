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
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "data[0]": "value", # which column to return
        "facets[respondent][]": "CISO",   # California ISO
        "facets[type][]": "D",            # D = actual demand
        "start": "2026-08-01T00",
        "end": "2026-08-08T00",
        "length": 200,
        
    },
    timeout=30, # Give up if the serve doesn't answer in 30 s
)

response.raise_for_status()            # raises an error on 4xx/5xx instead of failing silently

rows = response.json()["response"]["data"]
by_day = {}

by_day = {}

for row in rows:
    date_part, hour_part = row["period"].split("T")
    by_day.setdefault(date_part, []).append((int(hour_part), float(row["value"])))

print(f"\n{'date':<12} {'peak hour':>10} {'peak MW':>10} {'min hour':>10}")
for date_part in sorted(by_day):
    hours = by_day[date_part]
    if len(hours) < 24:
        continue                     # skip partial days at the edges
    peak_hour, peak_value = max(hours, key=lambda p: p[1])
    min_hour, _ = min(hours, key=lambda p: p[1])
    print(f"{date_part:<12} {peak_hour:>10} {peak_value:>10.0f} {min_hour:>10}")
        