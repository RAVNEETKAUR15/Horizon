import json

regions = ["CISO", "MISO", "NYIS", "PJM", "BPAT", "ERCO", "ISNE", "FPL"]

for region in regions:

    with open(f"data/raw/{region}_D.json") as f:
        demand = json.load(f)

    with open(f"data/raw/{region}_DF.json") as f:
        forecast = json.load(f)

    demand_periods = set(row["period"] for row in demand)
    forecast_periods = set(row["period"] for row in forecast)

    missing_forecast = demand_periods - forecast_periods
    missing_actual = forecast_periods - demand_periods

    print(f"\n{region}")
    print(f"Demand rows: {len(demand)}")
    print(f"Forecast rows: {len(forecast)}")
    print(f"Unique demand periods: {len(demand_periods)}")
    print(f"Unique forecast periods: {len(forecast_periods)}")
    print(f"Missing forecast: {len(missing_forecast)} hours")
    print(f"Missing actual: {len(missing_actual)} hours")

    if missing_forecast:
        print("First 20 missing forecast:")
        print(sorted(missing_forecast)[:20])

        print("First missing:", sorted(missing_forecast)[0])
        print("Last missing:", sorted(missing_forecast)[-1])