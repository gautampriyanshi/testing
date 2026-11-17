"""FastAPI backend: ingests weather + events, computes flight impact, serves the UI.

Run (from the backend folder):  python -m uvicorn main:app --port 8000
Then open http://localhost:8000
"""
import asyncio, logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

import db, engine
from data import LOCATIONS, EVENT_TYPES, WEATHER_PRESETS

log = logging.getLogger("airline")
logging.basicConfig(level=logging.INFO)
INGEST_EVERY = 300  # seconds
INDEX = Path(__file__).resolve().parent.parent / "index.html"


def fetch_weather() -> str:
    """Blocking call to Open-Meteo (free, no key). Returns a short status message."""
    codes = list(LOCATIONS)
    params = {
        "latitude": ",".join(str(LOCATIONS[c]["lat"]) for c in codes),
        "longitude": ",".join(str(LOCATIONS[c]["lon"]) for c in codes),
        "current": "temperature_2m,precipitation,snowfall,weather_code,wind_speed_10m,wind_gusts_10m,visibility",
        "wind_speed_unit": "kmh",
    }
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        data = data if isinstance(data, list) else [data]
        for code, d in zip(codes, data):
            c = d["current"]
            db.save_weather(code, {
                "temp": c["temperature_2m"], "precip": c["precipitation"], "snow": c["snowfall"],
                "code": c["weather_code"], "wind": c["wind_speed_10m"], "gust": c["wind_gusts_10m"],
                "vis": c["visibility"]}, live=True)
        msg = f"ingested live weather for {len(codes)} locations"
    except Exception as e:  # network down etc. -> keep previous data; engine falls back to calm
        msg = f"weather ingest failed: {e}"
        log.warning(msg)
    recompute()
    return msg


def snapshot() -> dict:
    overrides = {a: {**WEATHER_PRESETS[p]} for a, p in db.get_overrides().items()}
    events = db.get_events()
    weather = db.get_weather()
    result = engine.compute(weather, overrides, events)
    for a, r in result["locations"].items():
        r["live"] = bool(weather.get(a, {}).get("live")) and a not in overrides
        r["name"] = LOCATIONS[a]["name"]
        r["kind"] = LOCATIONS[a]["kind"]
        r["lat"], r["lon"] = LOCATIONS[a]["lat"], LOCATIONS[a]["lon"]
    result["events"] = events
    result["event_types"] = {k: v["label"] for k, v in EVENT_TYPES.items()}
    result["overrides"] = {a: o["label"] for a, o in overrides.items()}
    return result


def recompute():
    changed = db.log_changes([i for m in snapshot()["modes"].values() for i in m["items"]])
    if changed:
        log.info("flight changes: %s", ", ".join(changed))
    return changed


async def ingest_loop():
    while True:
        await asyncio.to_thread(fetch_weather)
        await asyncio.sleep(INGEST_EVERY)


@asynccontextmanager
async def lifespan(app):
    db.init()
    task = asyncio.create_task(ingest_loop())
    yield
    task.cancel()


app = FastAPI(title="Airline Disruption API", lifespan=lifespan)


class EventIn(BaseModel):
    airport: str
    type: str
    note: str = "Manually injected"


class SimIn(BaseModel):
    airport: str
    type: str  # weather preset OR event type


def _check_airport(code):
    if code not in LOCATIONS:
        raise HTTPException(422, f"unknown location {code}")


@app.get("/api/state")
def state():
    return snapshot()


@app.post("/api/events", status_code=201)
def add_event(e: EventIn):
    _check_airport(e.airport)
    if e.type not in EVENT_TYPES:
        raise HTTPException(422, f"type must be one of {list(EVENT_TYPES)}")
    db.add_event(e.airport, e.type, e.note)
    recompute()
    return snapshot()


@app.delete("/api/events/{event_id}")
def remove_event(event_id: int):
    if not db.delete_event(event_id):
        raise HTTPException(404, "event not found")
    recompute()
    return snapshot()


@app.post("/api/simulate")
def simulate(s: SimIn):
    """Used by the UI: weather preset -> airport override, otherwise an event."""
    _check_airport(s.airport)
    if s.type in WEATHER_PRESETS:
        db.set_override(s.airport, s.type)
    elif s.type in EVENT_TYPES:
        db.add_event(s.airport, s.type, "Manually injected")
    else:
        raise HTTPException(422, f"unknown type {s.type}")
    recompute()
    return snapshot()


@app.post("/api/clear")
def clear():
    db.clear_all()
    recompute()
    return snapshot()


@app.post("/api/refresh")
async def refresh():
    msg = await asyncio.to_thread(fetch_weather)
    return {"message": msg, **snapshot()}


@app.get("/api/changes")
def changes(limit: int = Query(50, le=500), flight: Optional[str] = None):
    return db.get_changes(limit, flight)


@app.get("/")
def index():
    return FileResponse(INDEX)
