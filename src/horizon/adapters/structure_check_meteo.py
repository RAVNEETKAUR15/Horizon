import json

with open("data/raw/CISO_weather.json") as f:
    body = json.load(f)

print(body.keys())
print(body["hourly"].keys())
print(body["hourly_units"])
print()
print("First 3 times:", body["hourly"]["time"][:3])

print("First 3 temperatures:", body["hourly"]["temperature_2m"][:3])