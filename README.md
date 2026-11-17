# Transport Disruption Monitor

A small app that ingests **weather** and **events** and shows how they affect **flights, buses and cars**. A Python (FastAPI) backend pulls live weather, applies a rules engine, stores history in SQLite, and serves a single-page UI that updates flight/bus/car status in real time.

## Features

- **Live weather ingest** from [Open-Meteo](https://open-meteo.com/) (free, no API key) for 8 airports and 9 road-network cities, refreshed every 5 minutes.
- **Event ingest**: strikes, ATC outages, security incidents, volcanic ash and mass events, attached to a location.
- **Rules engine** turns weather + events into a 0-100 risk score per location, then into a status for every trip:
  - Flights: on time / delayed / cancelled.
  - Buses: on time / delayed / cancelled.
  - Cars: clear / slow / avoid.
- **Mode-specific rules**: ATC outages only affect flights, strikes hit buses harder than cars, mass events slow cars more, and rain, snow, ice and fog matter most on the road.
- **UI**: mode selector, route map, KPI cards, on-time donut, region filter for road routes, sortable/searchable table with expandable rows, change history, toast alerts, light (default) and dark themes.
- **Simulation**: inject a storm, snow, fog or any event at any location to watch trips change.
- **History**: every status change is stored in SQLite and available from the API.

## Quick start

Requires Python 3.9+.

```bash
pip install -r requirements.txt
cd backend
python -m uvicorn main:app --port 8000
```

Open <http://localhost:8000>. API docs are at <http://localhost:8000/docs>.

If the weather API is unreachable the app keeps working with the last stored data (or calm defaults) and logs a warning.

## Project structure

```
index.html          Single-page UI (talks to the API; served by the backend)
requirements.txt
backend/
  main.py           FastAPI app, background weather ingest, API routes
  engine.py         Rules engine: weather + events -> risk -> trip status
  db.py             SQLite storage (created as backend/airline.db on first run)
  data.py           Airports, cities, routes, event types, weather presets
```

## API

| Method | Path | Description |
|---|---|---|
| GET | `/api/state` | Locations, risk scores, all trips by mode, KPIs, events |
| POST | `/api/simulate` | Body `{"airport": "JFK", "type": "storm"}`. Weather preset (`storm`, `snow`, `fog`) sets an override; an event type (`strike`, `atc`, `security`, `ash`, `festival`) adds an event |
| POST | `/api/events` | Add an event: `{"airport", "type", "note"}` |
| DELETE | `/api/events/{id}` | Remove an event |
| POST | `/api/clear` | Remove all events and weather overrides |
| POST | `/api/refresh` | Force a weather pull now |
| GET | `/api/changes?limit=50&flight=AI101` | Status-change history, optionally for one trip |

Example:

```bash
curl -X POST localhost:8000/api/simulate \
  -H "Content-Type: application/json" \
  -d '{"airport":"JFK","type":"storm"}'
```

## Customising

Everything lives in `backend/data.py` and `backend/engine.py`:

- Add airports, cities and routes in `data.py` (flights, buses, cars, and each bus/car region).
- Tune thresholds and scoring in `engine.py`: delayed at risk 20 and up, cancelled/avoid at 80-85 and up.
- Change event severity per mode in `data.py` (`EVENT_TYPES`, `GROUND_EVENT_SEV`).

## Notes

- Flight, bus and car schedules are **sample data**, not a real feed. Plugging in a real flights API (for example OpenSky or AviationStack) means replacing the lists in `data.py`.
- Risk thresholds and severities are illustrative starting values, not calibrated against real operations.
- `airline.db` is created locally and is git-ignored.
