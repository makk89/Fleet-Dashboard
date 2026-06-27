"""
Fleet Monitoring Dashboard
==========================
A high-fidelity prototype showing the concept for an API-integrated fleet
monitoring system:

  * a live world map of the fleet (vessels move in real time)
  * click any vessel  -> its full MIS (Management Information System) dashboard

The data is simulated in fleet_data.py, which is the single place a developer
swaps the dummy feed for a real marine-traffic / fleet-management API.

Run:
    python app.py
Then open http://127.0.0.1:5000
"""

import os

from flask import Flask, jsonify, render_template, abort

import fleet_data

app = Flask(__name__)


# --------------------------------------------------------------------------- #
#  PAGE
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    return render_template("dashboard.html")


# --------------------------------------------------------------------------- #
#  API  (mirrors the shape of a real marine-traffic + fleet-mgmt backend)
# --------------------------------------------------------------------------- #
@app.route("/api/vessels")
def api_vessels():
    """Live AIS-style position snapshot for the whole fleet (polled by the map)."""
    vessels = fleet_data.get_positions()
    return jsonify({
        "count": len(vessels),
        "vessels": vessels,
    })


@app.route("/api/vessels/<int:vessel_id>/mis")
def api_vessel_mis(vessel_id):
    """Full Management Information System payload for one vessel."""
    mis = fleet_data.get_mis(vessel_id)
    if mis is None:
        abort(404, description="Vessel not found")
    return jsonify(mis)


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok", "service": "fleet-monitoring-dashboard"})


if __name__ == "__main__":
    # Honour the PORT env var (macOS reserves 5000 for AirPlay); default 5050.
    port = int(os.environ.get("PORT", 5050))
    app.run(debug=True, host="127.0.0.1", port=port)
