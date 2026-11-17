"""Rules engine: weather + events -> location risk (per transport mode) -> trip status."""
from data import (EVENT_TYPES, FLIGHTS, BUSES, CARS, LOCATIONS, CALM,
                  GROUND_EVENT_SEV, SPEED_KMH)

SNOW_CODES = (71, 73, 75, 77, 85, 86)


def _combine(a, b):
    return min(100, round(max(a, b) + min(a, b) * 0.4))


# ---------------- air ----------------
def weather_risk(w: dict):
    score, why = 0, []
    gust = w.get("gust") or 0
    if gust >= 90:
        score += 70; why.append(f"gusts {int(gust)} km/h")
    elif gust >= 60:
        score += 35; why.append(f"gusts {int(gust)} km/h")
    if w.get("code") in (95, 96, 99):
        score += 75; why.append("thunderstorm")
    snow = w.get("snow") or 0
    if snow >= 1 or w.get("code") in SNOW_CODES:
        score += min(70, 30 + snow * 15); why.append("snow")
    vis = w.get("vis") if w.get("vis") is not None else 10000
    if vis < 1000:
        score += 60; why.append(f"visibility {int(vis)} m")
    elif vis < 3000 or w.get("code") in (45, 48):
        score += 30; why.append("low visibility")
    if (w.get("precip") or 0) >= 5:
        score += 25; why.append(f"heavy rain {w['precip']} mm")
    temp = w.get("temp") if w.get("temp") is not None else 20
    if temp <= -15:
        score += 25; why.append(f"extreme cold {temp}C")
    if temp >= 45:
        score += 20; why.append(f"extreme heat {temp}C")
    return min(100, int(score)), why


def event_risk(events):
    score, why = 0, []
    for e in events:
        sev = EVENT_TYPES[e["type"]]["sev"]
        score = max(score, sev) + (10 if score else 0)
        why.append(EVENT_TYPES[e["type"]]["label"].lower())
    return min(100, score), why


# ---------------- road (bus / car) ----------------
def ground_weather_risk(w: dict):
    score, why = 0, []
    precip = w.get("precip") or 0
    snow = w.get("snow") or 0
    vis = w.get("vis") if w.get("vis") is not None else 10000
    gust = w.get("gust") or 0
    temp = w.get("temp") if w.get("temp") is not None else 20
    if precip >= 10:
        score += 45; why.append(f"torrential rain {precip} mm")
    elif precip >= 5:
        score += 30; why.append(f"heavy rain {precip} mm")
    if snow >= 1 or w.get("code") in SNOW_CODES:
        score += min(80, 45 + snow * 10); why.append("snow on roads")
    if vis < 1000:
        score += 45; why.append("dense fog")
    elif vis < 3000 or w.get("code") in (45, 48):
        score += 20; why.append("reduced visibility")
    if w.get("code") in (95, 96, 99):
        score += 35; why.append("thunderstorm")
    if gust >= 90:
        score += 30; why.append(f"high winds {int(gust)} km/h")
    elif gust >= 60:
        score += 10; why.append(f"strong winds {int(gust)} km/h")
    if temp <= 0 and precip > 0:
        score += 35; why.append("icy roads")
    if temp <= -15:
        score += 20; why.append(f"extreme cold {temp}C")
    if temp >= 45:
        score += 15; why.append(f"extreme heat {temp}C")
    return min(100, int(score)), why


def ground_event_risk(events, mode):
    score, why = 0, []
    for e in events:
        sev = GROUND_EVENT_SEV[mode].get(e["type"], 0)
        if not sev:
            continue
        score = max(score, sev) + (10 if score else 0)
        why.append(EVENT_TYPES[e["type"]]["label"].lower())
    return min(100, score), why


def location_risk(w: dict, events: list) -> dict:
    ws, ww = weather_risk(w)
    es, ew = event_risk(events)
    gws, gww = ground_weather_risk(w)
    out = {"score": _combine(ws, es), "why": ww + ew, "weather": w}
    for mode in ("bus", "car"):
        es_g, ew_g = ground_event_risk(events, mode)
        out[mode] = _combine(gws, es_g)
        out[mode + "_why"] = gww + ew_g
    return out


# ---------------- trips ----------------
def _fmt(minutes):
    minutes %= 1440
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def trip_impact(t: dict, locs: dict) -> dict:
    mode = t["mode"]
    key, wkey = ("score", "why") if mode == "air" else (mode, mode + "_why")
    o, d = locs[t["frm"]], locs[t["to"]]
    score = max(o[key], d[key] * 0.9)
    reasons = [f"{t['frm']}: {r}" for r in o[wkey]] + [f"{t['to']}: {r}" for r in d[wkey]]
    cancel_at = 85 if mode in ("air", "car") else 80
    status, delay = "On time", 0
    dur = round(t["km"] / SPEED_KMH[mode] * 60) if t["km"] else None
    if score >= cancel_at:
        status = "Cancelled"
    elif score >= 20:
        # air: fixed formula; road: slowdown proportional to trip length
        raw = score * 2.2 if mode == "air" else dur * score / 100 * 0.9
        status, delay = "Delayed", max(5, int(round(raw / 5) * 5))
    out = {**t, "score": round(score), "status": status, "delay": delay, "reasons": reasons, "dur": dur}
    if dur:
        h, m = map(int, t["dep"].split(":"))
        out["eta"] = None if status == "Cancelled" else _fmt(h * 60 + m + dur + delay)
        out["eta_base"] = _fmt(h * 60 + m + dur)
    return out


def _kpis(items, n_events):
    delayed = [i["delay"] for i in items if i["delay"]]
    return {
        "total": len(items),
        "on_time": sum(i["status"] == "On time" for i in items),
        "delayed": sum(i["status"] == "Delayed" for i in items),
        "cancelled": sum(i["status"] == "Cancelled" for i in items),
        "avg_delay": round(sum(delayed) / len(delayed)) if delayed else 0,
        "active_events": n_events,
    }


def compute(weather: dict, overrides: dict, events: list) -> dict:
    """weather: {code: dict}; overrides: {code: dict}; events: list of event rows."""
    locs = {}
    for code in LOCATIONS:
        w = {**CALM, **weather.get(code, {})}
        w.update(overrides.get(code, {}))
        locs[code] = location_risk(w, [e for e in events if e["airport"] == code])
    modes = {}
    for mode, trips in (("air", FLIGHTS), ("bus", BUSES), ("car", CARS)):
        items = [trip_impact(t, locs) for t in trips]
        modes[mode] = {"items": items, "kpis": _kpis(items, len(events))}
    return {"locations": locs, "modes": modes}
