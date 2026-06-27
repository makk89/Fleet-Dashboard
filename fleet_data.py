"""
Fleet Monitoring Dashboard - Data Layer
=======================================

This module is the SINGLE SEAM where dummy data gets replaced by a live feed.

Two data sources are simulated here:

  1. LIVE AIS POSITIONS  -> get_positions()
     Mimics what a marine-traffic API (MarineTraffic, Spire, AISStream, etc.)
     returns for each vessel: MMSI/IMO, lat/lon, speed-over-ground (SOG),
     course-over-ground (COG), heading, navigational status, destination, ETA.
     Positions advance by dead-reckoning every time they are polled, so the
     map animates without any real network calls.

     >>> TO GO LIVE: replace the body of get_positions() with a call to your
         AIS provider and map their response onto the same dict keys. The rest
         of the application (API routes, frontend) needs no changes.

  2. MIS DATA  -> get_mis(vessel_id)
     The Management Information System payload for one vessel: technical
     defects, purchasing, planned maintenance, HSQE, budget, noon report,
     certificates, crew. Deterministically generated (seeded per vessel) so
     the numbers are stable across refreshes.

     >>> TO GO LIVE: replace get_mis() with queries against your fleet
         management database (e.g. ShipManager / TM Master / DNV).
"""

import math
import random
import time

# --------------------------------------------------------------------------- #
#  STATIC FLEET REGISTER
#  Real Scorpio-style product-tanker names, seeded with plausible ocean
#  positions, base course and speed. Lat/lon are starting points; they drift
#  from here as the simulation runs.
# --------------------------------------------------------------------------- #
#  (name, type, dwt, lat, lon, course_deg, speed_kts, status, destination)
_FLEET = [
    ("STI Pimlico",     "LR2",     109999, 56.8,  10.5,  185, 14.0, "Underway", "Rotterdam, NL"),
    ("STI Wembley",     "LR2",     109999, 55.2,   8.1,  200, 13.0, "Underway", "Hamburg, DE"),
    ("STI Rotherhithe", "MR",       49990, 53.0,   2.4,  210, 12.6, "Underway", "Antwerp, BE"),
    ("STI Hammersmith", "MR",       49990, 50.1,  -4.2,  245, 13.0, "Underway", "Le Havre, FR"),
    ("STI Magnetic",    "MR",       49990, 48.6,  -8.0,  260, 12.9, "Underway", "Lisbon, PT"),
    ("STI Dama",        "Handymax", 38734, 47.0, -12.0,  270,  9.0, "Underway", "New York, US"),
    ("STI Sanctity",    "MR",       49990, 44.0, -20.0,  255, 12.4, "Underway", "Houston, US"),
    ("STI Steadfast",   "MR",       49990, 42.5, -28.0,  250, 12.4, "Underway", "Charleston, US"),
    ("STI Jermyn",      "LR2",     109999, 40.0, -38.0,  248, 13.0, "Underway", "Galveston, US"),
    ("STI Lombard",     "MR",       49990, 38.0, -45.0,  255, 13.0, "Underway", "Pascagoula, US"),
    ("STI Soho",        "MR",       49990, 36.5, -52.0,  260, 13.0, "Underway", "Tampa, US"),
    ("STI Galata",      "MR",       49990, 35.0, -58.0,  265,  0.5, "At Anchor", "New Orleans, US"),
    ("STI Gauntlet",    "LR2",     109999, 33.0, -78.0,  150, 11.5, "Underway", "Savannah, US"),
    ("STI Grace",       "MR",       49990, 30.0, -82.0,  180,  3.2, "Maneuvering", "Jacksonville, US"),
    ("STI Duchessa",    "MR",       49990, 26.0, -90.0,  200,  0.5, "At Anchor", "Corpus Christi, US"),
    ("STI Meraux",      "Handymax", 38734, 25.0, -92.0,  210, 16.0, "Underway", "Veracruz, MX"),
    ("STI Sunny Liger", "MR",       49990, 22.0, -88.0,  160, 11.3, "Underway", "Cartagena, CO"),
    ("STI Leblon",      "MR",       49990, 18.0, -70.0,  140, 12.0, "Underway", "Santos, BR"),
    ("STI Battersea",   "MR",       49990, -8.0, -78.0,  170,  9.5, "Underway", "Callao, PE"),
    ("STI Jardins",     "MR",       49990, -2.0, -55.0,  120, 12.4, "Underway", "Rio de Janeiro, BR"),
    ("Mari Jone",       "VLCC",    300000,  2.0, -68.0,  200,  8.6, "Underway", "Panama Canal"),
    ("Malazgirt",       "Handymax", 38734,-12.0, -82.0,  190,  7.5, "Underway", "Valparaiso, CL"),
    ("PIS Kerinci",     "MR",       49990,-18.0, -78.0,  175, 14.0, "Underway", "San Antonio, CL"),
    ("Mari Kokako",     "VLCC",    300000,-22.0,-120.0,  270, 13.0, "Underway", "Singapore"),
    ("STI Symphony",    "MR",       49990, -6.0,  12.0,  150,  6.0, "Underway", "Cape Town, ZA"),
    ("STI Selatar",     "LR2",     109999,  4.0,   8.0,  120, 12.0, "Underway", "Lagos, NG"),
    ("STI Queens",      "MR",       49990,-15.0,  14.0,  180,  5.0, "Underway", "Walvis Bay, NA"),
    ("STI Gladiator",   "MR",       49990,-34.0,  17.0,   95, 10.3, "Underway", "Durban, ZA"),
    ("STI Supreme",     "LR2",     109999, 12.0,  44.0,   90,  1.1, "Maneuvering", "Fujairah, AE"),
    ("Solace",          "MR",       49990, 14.0,  55.0,   75,  1.6, "Maneuvering", "Jebel Ali, AE"),
    ("STI Stability",   "MR",       49990,  6.0,  68.0,  100,  9.7, "Underway", "Mumbai, IN"),
    ("STI Orchard",     "MR",       49990, 18.0,  60.0,   85, 12.0, "Underway", "Sikka, IN"),
    ("STI Memphis",     "LR2",     109999, 10.0,  92.0,   95, 12.4, "Underway", "Port Klang, MY"),
    ("Sunny Apatite",   "MR",       49990,  4.0, 100.0,  120, 13.0, "Underway", "Singapore"),
    ("STI Winnie",      "MR",       49990,  2.0, 104.0,   60, 13.5, "Underway", "Singapore"),
    ("STI Veneto",      "LR2",     109999, -2.0, 110.0,   80, 10.0, "Underway", "Jakarta, ID"),
    ("STI Virtus",      "MR",       49990, -6.0, 112.0,   90,  0.5, "At Anchor", "Surabaya, ID"),
    ("STI Magister",    "MR",       49990, -8.0, 115.0,  100,  9.0, "Underway", "Darwin, AU"),
    ("STI Marvel",      "MR",       49990,-28.0, 114.0,  170, 11.0, "Underway", "Fremantle, AU"),
    ("STI MAGIC",       "LR2",     109999,-32.0, 132.0,   95, 13.0, "Underway", "Adelaide, AU"),
    ("STI San Telmo",   "MR",       49990,-36.0, 150.0,   30,  0.5, "At Anchor", "Sydney, AU"),
    ("STI MOXIE",       "MR",       49990, 22.0, 122.0,   45, 10.8, "Underway", "Kaohsiung, TW"),
    ("STI Sydney",      "LR2",     109999, 26.0, 128.0,   40,  0.5, "At Anchor", "Okinawa, JP"),
    ("STI Guard",       "MR",       49990, 38.0, 150.0,   20, 11.9, "Underway", "Yokohama, JP"),
    ("STI Veneto II",   "MR",       49990, 34.0, 138.0,   60, 12.0, "Underway", "Ulsan, KR"),
]

# Vessel flags / build years pool for particulars
_FLAGS = ["Marshall Islands", "Liberia", "Malta", "Singapore", "Isle of Man"]
_CLASS = ["DNV", "Lloyd's Register", "ABS", "Bureau Veritas"]


def _build_register():
    vessels = {}
    for idx, row in enumerate(_FLEET):
        name, vtype, dwt, lat, lon, cog, sog, status, dest = row
        vid = idx + 1
        rng = random.Random(vid * 7919)  # stable per-vessel seed
        imo = 9_400_000 + vid * 137
        mmsi = 256_000_000 + vid * 911
        vessels[vid] = {
            "id": vid,
            "name": name,
            "type": vtype,
            "dwt": dwt,
            "imo": imo,
            "mmsi": mmsi,
            "flag": _FLAGS[rng.randrange(len(_FLAGS))],
            "class_society": _CLASS[rng.randrange(len(_CLASS))],
            "built": 2012 + rng.randrange(11),
            # dynamic AIS state (mutated by the simulation)
            "lat": lat,
            "lon": lon,
            "cog": cog,
            "heading": cog,
            "sog": sog,
            "status": status,
            "destination": dest,
            "_eta_offset_h": 12 + rng.randrange(120),
        }
    return vessels


_VESSELS = _build_register()
_LAST_TICK = time.time()


# --------------------------------------------------------------------------- #
#  LIVE POSITION FEED  (swap this for a real marine-traffic API)
# --------------------------------------------------------------------------- #
def _advance(v, dt_hours):
    """Dead-reckon one vessel forward along its course at its speed."""
    if v["sog"] < 0.3:
        # idle vessels at anchor only jitter heading slightly
        v["heading"] = (v["heading"] + random.uniform(-1.5, 1.5)) % 360
        return

    dist_nm = v["sog"] * dt_hours
    cog_rad = math.radians(v["cog"])
    dlat = dist_nm * math.cos(cog_rad) / 60.0
    lat_rad = math.radians(v["lat"])
    dlon = dist_nm * math.sin(cog_rad) / (60.0 * max(math.cos(lat_rad), 0.2))

    v["lat"] = max(-78.0, min(80.0, v["lat"] + dlat))
    v["lon"] = ((v["lon"] + dlon + 180) % 360) - 180  # wrap at the dateline

    # gentle, natural course changes so the fleet doesn't move in straight lines
    v["cog"] = (v["cog"] + random.uniform(-2.0, 2.0)) % 360
    v["heading"] = v["cog"]

    # bounce away from the poles
    if abs(v["lat"]) > 70:
        v["cog"] = (v["cog"] + 180) % 360


def get_positions():
    """
    Return the current AIS-style snapshot for every vessel.

    >>> LIVE INTEGRATION POINT <<<
    Replace everything below with a call to your provider, e.g.:

        resp = requests.get(MARINETRAFFIC_URL, params={...}, timeout=10)
        return [_map_provider_record(r) for r in resp.json()]

    keeping the same output keys so the frontend keeps working unchanged.
    """
    global _LAST_TICK
    now = time.time()
    dt_hours = (now - _LAST_TICK) / 3600.0
    # Time-compression: 1 real second == 6 simulated minutes, so movement is
    # visible during a demo. Remove this multiplier for real (real-time) data.
    dt_hours *= 360.0
    _LAST_TICK = now

    snapshot = []
    for v in _VESSELS.values():
        _advance(v, dt_hours)
        eta = time.gmtime(now + v["_eta_offset_h"] * 3600)
        snapshot.append({
            "id": v["id"],
            "name": v["name"],
            "type": v["type"],
            "imo": v["imo"],
            "mmsi": v["mmsi"],
            "lat": round(v["lat"], 4),
            "lon": round(v["lon"], 4),
            "sog": round(v["sog"], 1),
            "cog": round(v["cog"], 0),
            "heading": round(v["heading"], 0),
            "status": v["status"],
            "destination": v["destination"],
            "eta": time.strftime("%d %b %H:%M UTC", eta),
        })
    return snapshot


def list_vessels():
    """Lightweight register for filters / search."""
    return [
        {"id": v["id"], "name": v["name"], "type": v["type"]}
        for v in _VESSELS.values()
    ]


# --------------------------------------------------------------------------- #
#  MIS DATA  (swap this for your fleet-management database)
# --------------------------------------------------------------------------- #
def get_mis(vessel_id):
    """
    Build the full Management Information System payload for one vessel.

    >>> LIVE INTEGRATION POINT <<<
    Replace the seeded random numbers below with real queries against your
    PMS / procurement / HSQE / finance systems, keyed on vessel IMO.
    """
    v = _VESSELS.get(int(vessel_id))
    if not v:
        return None

    rng = random.Random(v["id"] * 104729)

    def r(a, b):
        return rng.randint(a, b)

    open_defects = r(2, 18)
    overdue_defects = r(0, 4)
    overdue_pms = r(0, 30)
    crew_total = r(20, 26)

    # 6-month noon-report fuel trend (MT/day)
    fuel_trend = [round(rng.uniform(18, 34), 1) for _ in range(14)]
    speed_trend = [round(rng.uniform(10.5, 14.5), 1) for _ in range(14)]

    budget = []
    for acct, annual in [
        ("Crew", 8_314_100), ("Insurance", 519_331), ("Lubricants", 412_000),
        ("Stores", 286_500), ("Spares", 731_200), ("Repairs", 658_900),
        ("Dry Dock", 1_250_000),
    ]:
        spent = int(annual * rng.uniform(0.18, 0.62))
        dev = round(rng.uniform(-46, 12))
        budget.append({
            "account": acct, "annual": annual, "spent": spent,
            "deviation": dev,
        })

    return {
        "id": v["id"],
        "name": v["name"],
        "particulars": {
            "Type": v["type"],
            "IMO": v["imo"],
            "MMSI": v["mmsi"],
            "DWT": f"{v['dwt']:,} t",
            "Flag": v["flag"],
            "Class": v["class_society"],
            "Built": v["built"],
        },
        "voyage": {
            "status": v["status"],
            "destination": v["destination"],
            "sog": round(v["sog"], 1),
            "cog": round(v["cog"], 0),
            "position": f"{abs(v['lat']):.3f}{'N' if v['lat']>=0 else 'S'}, "
                        f"{abs(v['lon']):.3f}{'E' if v['lon']>=0 else 'W'}",
        },
        "kpis": {
            "technical_defects": {
                "Open Defects": open_defects,
                "Overdue Defects": overdue_defects,
            },
            "purchasing": {
                "Critical Parts - Pending": r(0, 8),
                "Invoices Breach > 15 Days": r(5, 60),
                "RFQ Completed (not Evaluated)": r(10, 45),
                "POs Pending Approval": r(0, 10),
            },
            "planned_maintenance": {
                "Overdue Standard Jobs": overdue_pms,
                "Due Standard Jobs": r(40, 110),
                "Critical Overdue Jobs": r(0, 15),
            },
            "hsqe": {
                "Vettings (Last 12M)": r(6, 16),
                "CARs Overdue": r(0, 3),
                "Incidents - Open": r(0, 12),
                "Certificates Expiring 3M": r(2, 20),
            },
        },
        "alerts": _build_alerts(rng, overdue_defects, overdue_pms),
        "budget": budget,
        "fuel_trend": fuel_trend,
        "speed_trend": speed_trend,
        "crew": {
            "On Board": crew_total,
            "Nationalities": r(3, 7),
            "Avg Contract Days Left": r(20, 160),
            "Reliefs Due 30D": r(0, 6),
        },
        "lifeboat_lowering": r(2, 9),
    }


def _build_alerts(rng, overdue_defects, overdue_pms):
    alerts = []
    if overdue_defects > 2:
        alerts.append({"level": "high", "text": f"{overdue_defects} technical defects overdue"})
    if overdue_pms > 20:
        alerts.append({"level": "high", "text": f"{overdue_pms} planned-maintenance jobs overdue"})
    pool = [
        ("med", "ISM internal audit due within 30 days"),
        ("med", "Lifeboat on-load release service approaching"),
        ("low", "Annual class survey window opens next month"),
        ("med", "SIRE 2.0 inspection window open"),
        ("low", "Provisions stock below 14-day reserve"),
    ]
    for _ in range(rng.randint(1, 3)):
        lvl, txt = pool[rng.randrange(len(pool))]
        alerts.append({"level": lvl, "text": txt})
    return alerts
