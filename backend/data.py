AIRPORTS = {
    "DEL": {"name": "Delhi", "lat": 28.56, "lon": 77.10},
    "BOM": {"name": "Mumbai", "lat": 19.09, "lon": 72.87},
    "DXB": {"name": "Dubai", "lat": 25.25, "lon": 55.36},
    "LHR": {"name": "London Heathrow", "lat": 51.47, "lon": -0.45},
    "JFK": {"name": "New York JFK", "lat": 40.64, "lon": -73.78},
    "ORD": {"name": "Chicago O'Hare", "lat": 41.98, "lon": -87.90},
    "SFO": {"name": "San Francisco", "lat": 37.62, "lon": -122.38},
    "SIN": {"name": "Singapore", "lat": 1.36, "lon": 103.99},
}

# Extra road-network cities (weather is ingested for these too)
CITIES = {
    "JAI": {"name": "Jaipur", "lat": 26.91, "lon": 75.79},
    "AGR": {"name": "Agra", "lat": 27.18, "lon": 78.02},
    "PNQ": {"name": "Pune", "lat": 18.52, "lon": 73.86},
    "MAN": {"name": "Manchester", "lat": 53.48, "lon": -2.24},
    "BOS": {"name": "Boston", "lat": 42.36, "lon": -71.06},
    "PHL": {"name": "Philadelphia", "lat": 39.95, "lon": -75.17},
    "LAX": {"name": "Los Angeles", "lat": 34.05, "lon": -118.24},
    "AUH": {"name": "Abu Dhabi", "lat": 24.45, "lon": 54.38},
    "KUL": {"name": "Kuala Lumpur", "lat": 3.14, "lon": 101.69},
}

# Every place we ingest weather for / accept events at
LOCATIONS = {
    **{k: {**v, "kind": "airport"} for k, v in AIRPORTS.items()},
    **{k: {**v, "kind": "city"} for k, v in CITIES.items()},
}

_FLIGHTS = [
    ("AI101", "DEL", "LHR", "06:30"), ("AI131", "BOM", "JFK", "02:15"),
    ("EK510", "DXB", "DEL", "09:05"), ("BA142", "LHR", "JFK", "10:45"),
    ("UA901", "ORD", "LHR", "18:20"), ("UA837", "SFO", "SIN", "23:55"),
    ("SQ026", "SIN", "SFO", "08:40"), ("AA100", "JFK", "LHR", "19:00"),
    ("6E205", "BOM", "DEL", "07:50"), ("EK203", "DXB", "JFK", "08:30"),
    ("AI144", "DEL", "SFO", "14:10"), ("BA256", "LHR", "SIN", "21:15"),
    ("UA2", "SFO", "ORD", "12:00"), ("AI687", "DEL", "DXB", "04:20"),
    ("SQ317", "SIN", "LHR", "11:25"),
]
FLIGHTS = [dict(no=n, frm=f, to=t, dep=d, mode="air", region=None, km=None) for n, f, t, d in _FLIGHTS]

# (id, from, to, departure, km, region)
_BUSES = [
    ("BUS-101", "DEL", "JAI", "06:00", 280, "North India"), ("BUS-102", "DEL", "AGR", "07:30", 230, "North India"),
    ("BUS-103", "BOM", "PNQ", "08:00", 150, "West India"), ("BUS-104", "JAI", "AGR", "09:00", 240, "North India"),
    ("BUS-201", "LHR", "MAN", "07:00", 300, "UK"), ("BUS-202", "MAN", "LHR", "15:00", 300, "UK"),
    ("BUS-301", "JFK", "BOS", "09:00", 350, "US East"), ("BUS-302", "JFK", "PHL", "10:30", 150, "US East"),
    ("BUS-303", "BOS", "JFK", "17:00", 350, "US East"),
    ("BUS-401", "SFO", "LAX", "08:15", 600, "US West"), ("BUS-402", "LAX", "SFO", "18:00", 600, "US West"),
    ("BUS-501", "DXB", "AUH", "07:15", 140, "UAE"), ("BUS-502", "AUH", "DXB", "16:30", 140, "UAE"),
    ("BUS-601", "SIN", "KUL", "08:00", 350, "SE Asia"), ("BUS-602", "KUL", "SIN", "14:00", 350, "SE Asia"),
]
_CARS = [
    ("CAR-101", "DEL", "AGR", "05:30", 230, "North India"), ("CAR-102", "DEL", "JAI", "06:30", 280, "North India"),
    ("CAR-103", "BOM", "PNQ", "07:00", 150, "West India"),
    ("CAR-201", "LHR", "MAN", "08:00", 300, "UK"), ("CAR-202", "MAN", "LHR", "17:00", 300, "UK"),
    ("CAR-301", "JFK", "BOS", "07:30", 350, "US East"), ("CAR-302", "JFK", "PHL", "08:00", 150, "US East"),
    ("CAR-303", "BOS", "JFK", "18:30", 350, "US East"),
    ("CAR-401", "SFO", "LAX", "06:00", 600, "US West"),
    ("CAR-501", "DXB", "AUH", "07:00", 140, "UAE"),
    ("CAR-601", "SIN", "KUL", "09:00", 350, "SE Asia"),
]
SPEED_KMH = {"bus": 55, "car": 75}
BUSES = [dict(no=n, frm=f, to=t, dep=d, km=km, region=r, mode="bus") for n, f, t, d, km, r in _BUSES]
CARS = [dict(no=n, frm=f, to=t, dep=d, km=km, region=r, mode="car") for n, f, t, d, km, r in _CARS]

EVENT_TYPES = {
    "strike": {"label": "Strike", "sev": 60},
    "atc": {"label": "ATC outage", "sev": 75},
    "security": {"label": "Security incident", "sev": 80},
    "ash": {"label": "Volcanic ash", "sev": 95},
    "festival": {"label": "Mass event", "sev": 25},
}

# How strongly each event hits road transport (0 = no effect, e.g. ATC outage doesn't stop a bus)
GROUND_EVENT_SEV = {
    "bus": {"strike": 70, "atc": 0, "security": 30, "ash": 10, "festival": 35},
    "car": {"strike": 25, "atc": 0, "security": 30, "ash": 10, "festival": 45},
}

# Simulated weather presets (override live data for a location)
WEATHER_PRESETS = {
    "storm": {"code": 95, "gust": 95, "precip": 12, "vis": 2500, "label": "thunderstorm"},
    "snow": {"code": 75, "snow": 4, "gust": 55, "vis": 800, "temp": -8, "label": "heavy snow"},
    "fog": {"code": 45, "vis": 300, "label": "dense fog"},
}

CALM = {"temp": 20, "precip": 0, "snow": 0, "code": 1, "wind": 12, "gust": 20, "vis": 10000}
