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
         AIS provider and map their response onto the same dict keys.

  2. MIS DATA  -> get_mis(vessel_id)
     The Management Information System payload for one vessel, including
     DRILL-DOWN detail records behind every headline KPI (open defects,
     overdue jobs, breached invoices, incidents, expiring certs, ...).

     >>> TO GO LIVE: replace get_mis() with queries against your fleet
         management database (PMS / procurement / HSQE / finance).
"""

import math
import random
import time

# --------------------------------------------------------------------------- #
#  STATIC FLEET REGISTER  (random, non-"STI" vessel names)
# --------------------------------------------------------------------------- #
#  (name, type, dwt, lat, lon, course_deg, speed_kts, status, destination)
_FLEET = [
    ("Aurora Spirit",    "LR2",     109999, 56.8,  10.5,  185, 14.0, "Underway", "Rotterdam, NL"),
    ("Northern Crown",   "LR2",     109999, 55.2,   8.1,  200, 13.0, "Underway", "Hamburg, DE"),
    ("Blue Horizon",     "MR",       49990, 53.0,   2.4,  210, 12.6, "Underway", "Antwerp, BE"),
    ("Sea Falcon",       "MR",       49990, 50.1,  -4.2,  245, 13.0, "Underway", "Le Havre, FR"),
    ("Pacific Pearl",    "MR",       49990, 48.6,  -8.0,  260, 12.9, "Underway", "Lisbon, PT"),
    ("Atlantic Pioneer", "Handymax", 38734, 47.0, -12.0,  270,  9.0, "Underway", "New York, US"),
    ("Coral Voyager",    "MR",       49990, 44.0, -20.0,  255, 12.4, "Underway", "Houston, US"),
    ("Silver Marlin",    "MR",       49990, 42.5, -28.0,  250, 12.4, "Underway", "Charleston, US"),
    ("Ocean Sentinel",   "LR2",     109999, 40.0, -38.0,  248, 13.0, "Underway", "Galveston, US"),
    ("Crystal Dawn",     "MR",       49990, 38.0, -45.0,  255, 13.0, "Underway", "Pascagoula, US"),
    ("Golden Horizon",   "MR",       49990, 36.5, -52.0,  260, 13.0, "Underway", "Tampa, US"),
    ("Nordic Star",      "MR",       49990, 35.0, -58.0,  265,  0.5, "At Anchor", "New Orleans, US"),
    ("Emerald Wave",     "LR2",     109999, 33.0, -78.0,  150, 11.5, "Underway", "Savannah, US"),
    ("Crimson Tide",     "MR",       49990, 30.0, -82.0,  180,  3.2, "Maneuvering", "Jacksonville, US"),
    ("Azure Mariner",    "MR",       49990, 26.0, -90.0,  200,  0.5, "At Anchor", "Corpus Christi, US"),
    ("Polar Quest",      "Handymax", 38734, 25.0, -92.0,  210, 16.0, "Underway", "Veracruz, MX"),
    ("Sapphire Sky",     "MR",       49990, 22.0, -88.0,  160, 11.3, "Underway", "Cartagena, CO"),
    ("Iron Duke",        "MR",       49990, 18.0, -70.0,  140, 12.0, "Underway", "Santos, BR"),
    ("Storm Petrel",     "MR",       49990, -8.0, -78.0,  170,  9.5, "Underway", "Callao, PE"),
    ("Velvet Dawn",      "MR",       49990, -2.0, -55.0,  120, 12.4, "Underway", "Rio de Janeiro, BR"),
    ("Maple Crest",      "VLCC",    300000,  2.0, -68.0,  200,  8.6, "Underway", "Panama Canal"),
    ("Cobalt Sea",       "Handymax", 38734,-12.0, -82.0,  190,  7.5, "Underway", "Valparaiso, CL"),
    ("Lunar Crest",      "MR",       49990,-18.0, -78.0,  175, 14.0, "Underway", "San Antonio, CL"),
    ("Solar Wind",       "VLCC",    300000,-22.0,-120.0,  270, 13.0, "Underway", "Singapore"),
    ("Granite Bay",      "MR",       49990, -6.0,  12.0,  150,  6.0, "Underway", "Cape Town, ZA"),
    ("Amber Coast",      "LR2",     109999,  4.0,   8.0,  120, 12.0, "Underway", "Lagos, NG"),
    ("Falcon Ridge",     "MR",       49990,-15.0,  14.0,  180,  5.0, "Underway", "Walvis Bay, NA"),
    ("Tidal Force",      "MR",       49990,-34.0,  17.0,   95, 10.3, "Underway", "Durban, ZA"),
    ("Marble Arch",      "LR2",     109999, 12.0,  44.0,   90,  1.1, "Maneuvering", "Fujairah, AE"),
    ("Onyx Trader",      "MR",       49990, 14.0,  55.0,   75,  1.6, "Maneuvering", "Jebel Ali, AE"),
    ("Zephyr Gale",      "MR",       49990,  6.0,  68.0,  100,  9.7, "Underway", "Mumbai, IN"),
    ("Ivory Gull",       "MR",       49990, 18.0,  60.0,   85, 12.0, "Underway", "Sikka, IN"),
    ("Vermillion",       "LR2",     109999, 10.0,  92.0,   95, 12.4, "Underway", "Port Klang, MY"),
    ("Aegean Star",      "MR",       49990,  4.0, 100.0,  120, 13.0, "Underway", "Singapore"),
    ("Bering Glory",     "MR",       49990,  2.0, 104.0,   60, 13.5, "Underway", "Singapore"),
    ("Caspian Pride",    "LR2",     109999, -2.0, 110.0,   80, 10.0, "Underway", "Jakarta, ID"),
    ("Delta Runner",     "MR",       49990, -6.0, 112.0,   90,  0.5, "At Anchor", "Surabaya, ID"),
    ("Echo Valley",      "MR",       49990, -8.0, 115.0,  100,  9.0, "Underway", "Darwin, AU"),
    ("Frontier Belle",   "MR",       49990,-28.0, 114.0,  170, 11.0, "Underway", "Fremantle, AU"),
    ("Glacier Bay",      "LR2",     109999,-32.0, 132.0,   95, 13.0, "Underway", "Adelaide, AU"),
    ("Halcyon",          "MR",       49990,-36.0, 150.0,   30,  0.5, "At Anchor", "Sydney, AU"),
    ("Indigo Reef",      "MR",       49990, 22.0, 122.0,   45, 10.8, "Underway", "Kaohsiung, TW"),
    ("Juno Star",        "LR2",     109999, 26.0, 128.0,   40,  0.5, "At Anchor", "Okinawa, JP"),
    ("Kestrel",          "MR",       49990, 38.0, 150.0,   20, 11.9, "Underway", "Yokohama, JP"),
    ("Meridian",         "MR",       49990, 34.0, 138.0,   60, 12.0, "Underway", "Ulsan, KR"),
]

_FLAGS = ["Marshall Islands", "Liberia", "Malta", "Singapore", "Isle of Man"]
_CLASS = ["DNV", "Lloyd's Register", "ABS", "Bureau Veritas"]


def _build_register():
    vessels = {}
    for idx, row in enumerate(_FLEET):
        name, vtype, dwt, lat, lon, cog, sog, status, dest = row
        vid = idx + 1
        rng = random.Random(vid * 7919)
        vessels[vid] = {
            "id": vid, "name": name, "type": vtype, "dwt": dwt,
            "imo": 9_400_000 + vid * 137,
            "mmsi": 256_000_000 + vid * 911,
            "flag": _FLAGS[rng.randrange(len(_FLAGS))],
            "class_society": _CLASS[rng.randrange(len(_CLASS))],
            "built": 2012 + rng.randrange(11),
            "lat": lat, "lon": lon, "cog": cog, "heading": cog, "sog": sog,
            "status": status, "destination": dest,
            "_eta_offset_h": 12 + rng.randrange(120),
        }
    return vessels


_VESSELS = _build_register()
_LAST_TICK = time.time()


# --------------------------------------------------------------------------- #
#  LIVE POSITION FEED  (swap this for a real marine-traffic API)
# --------------------------------------------------------------------------- #
def _advance(v, dt_hours):
    if v["sog"] < 0.3:
        v["heading"] = (v["heading"] + random.uniform(-1.5, 1.5)) % 360
        return
    dist_nm = v["sog"] * dt_hours
    cog_rad = math.radians(v["cog"])
    dlat = dist_nm * math.cos(cog_rad) / 60.0
    lat_rad = math.radians(v["lat"])
    dlon = dist_nm * math.sin(cog_rad) / (60.0 * max(math.cos(lat_rad), 0.2))
    v["lat"] = max(-78.0, min(80.0, v["lat"] + dlat))
    v["lon"] = ((v["lon"] + dlon + 180) % 360) - 180
    v["cog"] = (v["cog"] + random.uniform(-2.0, 2.0)) % 360
    v["heading"] = v["cog"]
    if abs(v["lat"]) > 70:
        v["cog"] = (v["cog"] + 180) % 360


def get_positions():
    """
    Return the current AIS-style snapshot for every vessel.

    >>> LIVE INTEGRATION POINT <<< replace with a real provider call,
    keeping the same output keys so the frontend keeps working unchanged.
    """
    global _LAST_TICK
    now = time.time()
    dt_hours = (now - _LAST_TICK) / 3600.0
    dt_hours *= 360.0  # demo time-compression; remove for real-time data
    _LAST_TICK = now

    snapshot = []
    for v in _VESSELS.values():
        _advance(v, dt_hours)
        eta = time.gmtime(now + v["_eta_offset_h"] * 3600)
        snapshot.append({
            "id": v["id"], "name": v["name"], "type": v["type"],
            "imo": v["imo"], "mmsi": v["mmsi"],
            "lat": round(v["lat"], 4), "lon": round(v["lon"], 4),
            "sog": round(v["sog"], 1), "cog": round(v["cog"], 0),
            "heading": round(v["heading"], 0),
            "status": v["status"], "destination": v["destination"],
            "eta": time.strftime("%d %b %H:%M UTC", eta),
        })
    return snapshot


def list_vessels():
    return [{"id": v["id"], "name": v["name"], "type": v["type"]}
            for v in _VESSELS.values()]


# --------------------------------------------------------------------------- #
#  DRILL-DOWN RECORD BUILDERS  (the detail behind each headline KPI)
# --------------------------------------------------------------------------- #
_EQUIP = [
    "Main Engine", "Aux Engine #2", "Aux Engine #3", "Purifier #1",
    "Aux Boiler", "Cargo Pump #2", "Cargo Pump #4", "IG System",
    "Deck Crane #1", "Steering Gear", "Fresh Water Generator",
    "Air Compressor #1", "Bow Thruster", "Oily Water Separator", "Incinerator",
]
_SUPPLIERS = ["Wilhelmsen", "Drew Marine", "Alfa Laval", "MAN PrimeServ",
              "Survitec", "Kongsberg", "V.Group Supply", "Marine Care"]


def _defect_row(rng, i):
    return {"Ref": f"DEF-{2200 + rng.randrange(7700)}",
            "Equipment": rng.choice(_EQUIP),
            "Severity": rng.choice(["Critical", "Major", "Minor"]),
            "Reported": f"{rng.randint(2, 180)} d ago",
            "Status": rng.choice(["Open", "In Progress", "Awaiting Spares"])}


def _job_row(rng, i):
    return {"Job No": f"PMS-{10000 + rng.randrange(89999)}",
            "Equipment": rng.choice(_EQUIP),
            "Interval": rng.choice(["250h", "500h", "1000h", "Monthly", "Quarterly", "Annual"]),
            "Overdue": f"{rng.randint(1, 60)} d",
            "Resp": rng.choice(["C/E", "2/E", "3/E", "Bosun", "ETO"])}


def _invoice_row(rng, i):
    return {"PO": f"PO-{rng.randrange(100000, 999999)}",
            "Supplier": rng.choice(_SUPPLIERS),
            "Amount": f"${rng.randrange(2, 90) * 1000:,}",
            "Age": f"{rng.randint(16, 75)} d",
            "Status": rng.choice(["Awaiting Approval", "Disputed", "Pending GRN"])}


def _po_row(rng, i):
    return {"PO": f"PO-{rng.randrange(100000, 999999)}",
            "Category": rng.choice(["Spares", "Stores", "Lubricants", "Provisions", "Chemicals"]),
            "Value": f"${rng.randrange(1, 60) * 1000:,}",
            "Raised": f"{rng.randint(1, 20)} d ago",
            "Approver": rng.choice(["Tech Supt", "Fleet Manager", "Purchasing"])}


def _incident_row(rng, i):
    return {"Ref": f"INC-{rng.randrange(1000, 9999)}",
            "Type": rng.choice(["Near Miss", "Personal Injury", "Equipment Failure",
                                 "Minor Spill", "Non-Conformity"]),
            "Severity": rng.choice(["Low", "Medium", "High"]),
            "Date": f"{rng.randint(1, 120)} d ago",
            "Status": rng.choice(["Under Investigation", "CAR Raised", "Pending Review"])}


def _cert_row(rng, i):
    return {"Certificate": rng.choice(["Safety Equipment", "Safety Construction", "IOPP",
                                       "Load Line", "ISSC", "MLC", "IAPP", "Class Annual"]),
            "Authority": rng.choice(["DNV", "Lloyd's", "ABS", "Flag State", "BV"]),
            "Expires": f"in {rng.randint(5, 90)} d",
            "Action": rng.choice(["Survey Booked", "Pending", "Surveyor Attending"])}


def _drill(rng, total, builder, cap=20):
    """Build a drill-down table. Caps rendered rows but keeps the true total."""
    rows = [builder(rng, i) for i in range(min(total, cap))]
    return {"total": total, "rows": rows}


# --------------------------------------------------------------------------- #
#  MIS DATA  (swap this for your fleet-management database)
# --------------------------------------------------------------------------- #
def get_mis(vessel_id):
    """
    Build the full MIS payload for one vessel, including drill-down detail.

    >>> LIVE INTEGRATION POINT <<< replace the seeded numbers and the drill
    record builders above with real queries keyed on vessel IMO.
    """
    v = _VESSELS.get(int(vessel_id))
    if not v:
        return None

    rng = random.Random(v["id"] * 104729)
    r = lambda a, b: rng.randint(a, b)

    # headline KPI values
    open_defects   = r(2, 18)
    overdue_def    = r(0, 4)
    overdue_jobs   = r(0, 30)
    due_jobs       = r(40, 110)
    crit_jobs      = r(0, 15)
    crit_parts     = r(0, 8)
    inv_breach     = r(5, 60)
    rfq_open       = r(10, 45)
    pos_pending    = r(0, 10)
    vettings       = r(6, 16)
    cars_overdue   = r(0, 3)
    incidents_open = r(0, 12)
    certs_expiring = r(2, 20)
    crew_total     = r(20, 26)

    fuel_trend  = [round(rng.uniform(18, 34), 1) for _ in range(14)]
    speed_trend = [round(rng.uniform(10.5, 14.5), 1) for _ in range(14)]

    budget = []
    for acct, annual in [("Crew", 8_314_100), ("Insurance", 519_331),
                         ("Lubricants", 412_000), ("Stores", 286_500),
                         ("Spares", 731_200), ("Repairs", 658_900),
                         ("Dry Dock", 1_250_000)]:
        budget.append({"account": acct, "annual": annual,
                       "spent": int(annual * rng.uniform(0.18, 0.62)),
                       "deviation": round(rng.uniform(-46, 12))})

    return {
        "id": v["id"], "name": v["name"],
        "particulars": {
            "Type": v["type"], "IMO": v["imo"], "MMSI": v["mmsi"],
            "DWT": f"{v['dwt']:,} t", "Flag": v["flag"],
            "Class": v["class_society"], "Built": v["built"],
        },
        "voyage": {
            "status": v["status"], "destination": v["destination"],
            "sog": round(v["sog"], 1), "cog": round(v["cog"], 0),
            "position": f"{abs(v['lat']):.3f}{'N' if v['lat'] >= 0 else 'S'}, "
                        f"{abs(v['lon']):.3f}{'E' if v['lon'] >= 0 else 'W'}",
        },
        "kpis": {
            "technical_defects": {
                "Open Defects": open_defects, "Overdue Defects": overdue_def},
            "purchasing": {
                "Critical Parts - Pending": crit_parts,
                "Invoices Breach > 15 Days": inv_breach,
                "RFQ Completed (not Evaluated)": rfq_open,
                "POs Pending Approval": pos_pending},
            "planned_maintenance": {
                "Overdue Standard Jobs": overdue_jobs,
                "Due Standard Jobs": due_jobs,
                "Critical Overdue Jobs": crit_jobs},
            "hsqe": {
                "Vettings (Last 12M)": vettings, "CARs Overdue": cars_overdue,
                "Incidents - Open": incidents_open,
                "Certificates Expiring 3M": certs_expiring},
        },
        # >>> DRILL-DOWN: the records behind each clickable KPI <<<
        "drill": {
            "open_defects":         _drill(rng, open_defects, _defect_row),
            "overdue_defects":      _drill(rng, overdue_def, _defect_row),
            "overdue_jobs":         _drill(rng, overdue_jobs, _job_row),
            "critical_overdue_jobs":_drill(rng, crit_jobs, _job_row),
            "invoices_breach":      _drill(rng, inv_breach, _invoice_row),
            "pos_pending":          _drill(rng, pos_pending, _po_row),
            "incidents_open":       _drill(rng, incidents_open, _incident_row),
            "certs_expiring":       _drill(rng, certs_expiring, _cert_row),
        },
        "alerts": _build_alerts(rng, overdue_def, overdue_jobs),
        "budget": budget,
        "fuel_trend": fuel_trend, "speed_trend": speed_trend,
        "crew": {
            "On Board": crew_total, "Nationalities": r(3, 7),
            "Avg Contract Days Left": r(20, 160), "Reliefs Due 30D": r(0, 6)},
        "lifeboat_lowering": r(2, 9),
    }


def _build_alerts(rng, overdue_def, overdue_jobs):
    alerts = []
    if overdue_def > 2:
        alerts.append({"level": "high", "text": f"{overdue_def} technical defects overdue"})
    if overdue_jobs > 20:
        alerts.append({"level": "high", "text": f"{overdue_jobs} planned-maintenance jobs overdue"})
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
