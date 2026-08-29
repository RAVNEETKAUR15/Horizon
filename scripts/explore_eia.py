import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.environ["EIA_API_KEY"]
BASE="https://api.eia.gov/v2"

def show(route: str) -> dict:
    r = requests.get(f"{BASE}/{route}", params={"api_key": KEY}, timeout=30)
    r.raise_for_status()
    body = r.json()["response"]
    print(f"\n=== {route} ===")
    print(json.dumps(body, indent=2)[:2500])
    return body
show("electricity")
show("electricity/rto")
show("electricity/rto/region-data")
show("electricity/rto/region-data/facet/type")