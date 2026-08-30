"""Fetch hourly electricity data from the EIA API."""

import time
import requests


def fetch_series(api_key, respondent, series_type, start, end):
    """Fetch every row for one region and one series, paging through the API.

    api_key     -- your EIA key
    respondent  -- region code, e.g. "CISO"
    series_type -- "D" for actual demand, "DF" for the day-ahead forecast
    start, end  -- "YYYY-MM-DDTHH" strings

    Returns a list of row dictionaries.
    """
    all_rows = []
    offset = 0
    page_size = 5000
    page_count = 0
    max_pages = 500

    while True:
        response = requests.get(
            "https://api.eia.gov/v2/electricity/rto/region-data/data/",
            params={
                "api_key": api_key,
                "frequency": "hourly",
                "data[0]": "value",
                "facets[respondent][]": respondent,   # <-- now a parameter
                "facets[type][]": series_type,        # <-- now a parameter
                "start": start,
                "end": end,
                "sort[0][column]": "period",
                "sort[0][direction]": "asc",
                "offset": offset,
                "length": page_size,
            },
            timeout=30,
        )
        response.raise_for_status()

        page_rows = response.json()["response"]["data"]
        all_rows = all_rows + page_rows

        print(f"  {respondent} {series_type}: {len(all_rows)} rows so far")

        page_count = page_count + 1
        if page_count >= max_pages:
            print("  Hit the page limit — stopping.")
            break

        if len(page_rows) < page_size:
            break

        offset = offset + page_size
        time.sleep(0.5)
   # EIA suspends temporrily API keys that make requests too fast. The gap can help prevent that

    return all_rows
if __name__ == "__main__":
    import json
    import os
    from dotenv import load_dotenv

    load_dotenv()
    key = os.environ["EIA_API_KEY"]

    REGIONS = ["CISO", "ERCO", "PJM", "MISO", "ISNE", "NYIS", "BPAT", "FPL"]
    SERIES = ["D", "DF"]          # actual demand, day-ahead forecast
    START = "2019-01-01T00"
    END = "2026-08-01T00"

    os.makedirs("data/raw", exist_ok=True)

    for region in REGIONS:
        for series in SERIES:
            print(f"Fetching {region} {series}...")
            rows = fetch_series(key, region, series, START, END)

            path = f"data/raw/{region}_{series}.json"
            with open(path, "w") as f:
                json.dump(rows, f)

            print(f"  saved {len(rows)} rows to {path}\n")