# Fleet Monitoring Dashboard

A working **concept prototype** (Python / Flask) for an API-integrated fleet
monitoring system:

- A **live world map** of the fleet — vessels move in real time (orange AIS
  icons rotated to heading, with name + speed labels).
- A live **stat strip** (total / underway / at anchor / maneuvering / avg speed).
- **Click any vessel** → a slide-over **MIS dashboard** for that ship:
  voyage & position, alerts, KPI cards (Technical Defects, Planned Maintenance,
  Purchasing, HSQE), noon-report fuel/speed chart, committed-cost budget chart,
  vessel particulars and crew.

All data is **simulated** so the prototype runs with zero external accounts.
It is structured so a developer can swap the dummy feed for real APIs in one
file without touching the frontend.

---

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py            # serves on http://127.0.0.1:5050
```

> On macOS, port 5000 is taken by AirPlay; this app defaults to **5050**.
> Override with `PORT=8080 python app.py`.

For a sturdier local run, use the bundled gunicorn (localhost only):

```bash
gunicorn -w 2 -b 127.0.0.1:5060 app:app
```

---

## How it's wired

```
app.py            Flask app — page route + JSON API
fleet_data.py     >>> THE DATA SEAM <<< all dummy data lives here
templates/        dashboard.html  (the single page)
static/css/       dashboard.css   (dark ops-centre theme)
static/js/        dashboard.js    (map, polling, MIS panel, charts)
```

### API (the shape a real backend must match)

| Endpoint | Returns |
|---|---|
| `GET /api/vessels` | Live AIS snapshot for the whole fleet — polled by the map every 4 s |
| `GET /api/vessels/<id>/mis` | Full MIS payload for one vessel |
| `GET /api/health` | Health check |

The frontend only knows about these three endpoints. As long as a real backend
returns the **same JSON keys**, the map and MIS panel keep working unchanged.

---

## Going live (for the developer)

Everything to replace is in **`fleet_data.py`**, marked
`>>> LIVE INTEGRATION POINT <<<`:

1. **`get_positions()`** — replace the dead-reckoning simulation with a call to
   your AIS provider (MarineTraffic, Spire, AISStream, Kpler, …). Map their
   response onto these keys: `id, name, lat, lon, sog, cog, heading, status,
   destination, eta`.

2. **`get_mis(vessel_id)`** — replace the seeded random numbers with real
   queries against your fleet-management systems (PMS / procurement / HSQE /
   finance), keyed on vessel IMO. Keep the same payload shape.

No frontend changes are required for either swap.

> **Note:** positions are time-compressed (1 real second ≈ 6 simulated minutes)
> so movement is visible during a demo. Remove the multiplier in
> `get_positions()` for real-time data.

---

## What this is / isn't

This is a **high-level concept demo** to align on scope and UX before building
the production system — not the production system itself. The original
single-vessel MIS card layout (`index.html`, GitHub Pages) is preserved and was
the design reference for the per-vessel panel here.
