/* Fleet Monitoring Dashboard — frontend
 * Polls /api/vessels for live AIS positions and animates the fleet.
 * Clicking a vessel fetches /api/vessels/<id>/mis and opens the MIS panel.
 */

const POLL_MS = 4000;          // how often we refresh positions
const markers = {};            // id -> Leaflet marker
let selectedId = null;
let fuelChart = null, budgetChart = null;

/* ---------------- MAP ---------------- */
const map = L.map("map", {
  worldCopyJump: true,
  minZoom: 2,
  maxBounds: [[-85, -200], [85, 200]],
  maxBoundsViscosity: 0.6,
}).setView([25, 10], 3);

L.tileLayer(
  "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
  {
    attribution: "&copy; OpenStreetMap &copy; CARTO",
    subdomains: "abcd",
    maxZoom: 12,
  }
).addTo(map);

/* Ship-shaped SVG icon, rotated to heading */
function vesselDivIcon(heading, selected) {
  const cls = "vessel-icon" + (selected ? " sel" : "");
  return L.divIcon({
    className: cls,
    html: `<div style="transform:rotate(${heading}deg)">
      <svg width="20" height="20" viewBox="0 0 24 24">
        <path d="M12 1 L17 9 L17 20 L7 20 L7 9 Z"
              fill="#ff8c1a" stroke="#06121d" stroke-width="1"/>
      </svg></div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });
}

/* ---------------- POLLING ---------------- */
async function poll() {
  try {
    const res = await fetch("/api/vessels");
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    updateFleet(data.vessels);
    setLive(true, data.count);
  } catch (e) {
    setLive(false);
  }
}

function updateFleet(vessels) {
  const counts = { Underway: 0, "At Anchor": 0, Maneuvering: 0 };
  let speedSum = 0;

  vessels.forEach((v) => {
    counts[v.status] = (counts[v.status] || 0) + 1;
    speedSum += v.sog;

    if (markers[v.id]) {
      const m = markers[v.id];
      m.setLatLng([v.lat, v.lon]);
      m.setIcon(vesselDivIcon(v.heading, v.id === selectedId));
      m._vessel = v;
      m.setTooltipContent(`${v.name} — ${v.sog.toFixed(1)} Kts`);
    } else {
      const m = L.marker([v.lat, v.lon], {
        icon: vesselDivIcon(v.heading, false),
      }).addTo(map);
      m._vessel = v;
      m.bindTooltip(`${v.name} — ${v.sog.toFixed(1)} Kts`, {
        permanent: false, direction: "top", className: "vessel-label",
      });
      m.on("click", () => openMIS(v.id, v.name));
      markers[v.id] = m;
    }
  });

  // stat strip
  document.getElementById("statTotal").textContent = vessels.length;
  document.getElementById("statUnderway").textContent = counts["Underway"] || 0;
  document.getElementById("statAnchor").textContent = counts["At Anchor"] || 0;
  document.getElementById("statManeuver").textContent = counts["Maneuvering"] || 0;
  document.getElementById("statAvgSpeed").textContent =
    (speedSum / vessels.length).toFixed(1);
}

function setLive(ok, count) {
  const pill = document.getElementById("livePill");
  const meta = document.getElementById("liveMeta");
  const now = new Date().toLocaleTimeString();
  if (ok) {
    pill.classList.remove("stale");
    meta.textContent = `${count} vessels · ${now}`;
  } else {
    pill.classList.add("stale");
    meta.textContent = "feed unavailable";
  }
}

/* ---------------- MIS PANEL ---------------- */
const panel = document.getElementById("misPanel");
const scrim = document.getElementById("scrim");

async function openMIS(id, name) {
  selectedId = id;
  // refresh selection styling on markers
  Object.values(markers).forEach((m) =>
    m.setIcon(vesselDivIcon(m._vessel.heading, m._vessel.id === id))
  );
  if (markers[id]) map.panTo(markers[id].getLatLng(), { animate: true });

  panel.classList.add("open");
  scrim.classList.add("show");
  panel.setAttribute("aria-hidden", "false");
  document.getElementById("misContent").hidden = true;
  document.getElementById("misLoading").style.display = "block";

  try {
    const res = await fetch(`/api/vessels/${id}/mis`);
    const mis = await res.json();
    renderMIS(mis);
  } catch (e) {
    document.getElementById("misLoading").textContent = "Failed to load vessel data.";
  }
}

function closeMIS() {
  panel.classList.remove("open");
  scrim.classList.remove("show");
  panel.setAttribute("aria-hidden", "true");
  selectedId = null;
  Object.values(markers).forEach((m) =>
    m.setIcon(vesselDivIcon(m._vessel.heading, false))
  );
}
document.getElementById("misClose").addEventListener("click", closeMIS);
scrim.addEventListener("click", closeMIS);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeMIS(); });

function statusBadge(status) {
  const cls = { "Underway": "underway", "At Anchor": "anchor", "Maneuvering": "maneuver" }[status] || "underway";
  return `<span class="badge ${cls}">${status}</span>`;
}

function kpiRow(label, val, bad) {
  const cls = bad ? "v bad" : "v";
  return `<div class="kpi-row"><span>${label}</span><span class="${cls}">${val}</span></div>`;
}

function renderMIS(m) {
  document.getElementById("misLoading").style.display = "none";
  document.getElementById("misContent").hidden = false;

  document.getElementById("misName").textContent = m.name;
  document.getElementById("misSub").textContent =
    `IMO ${m.particulars.IMO} · ${m.particulars.Type} · ${m.particulars.Flag}`;

  // voyage
  const vy = m.voyage;
  document.getElementById("misVoyage").innerHTML = `
    <div class="vcell"><div class="vlbl">Status</div><div class="vval">${statusBadge(vy.status)}</div></div>
    <div class="vcell"><div class="vlbl">Speed / Course</div><div class="vval">${vy.sog} kts · ${vy.cog}°</div></div>
    <div class="vcell"><div class="vlbl">Destination</div><div class="vval">${vy.destination}</div></div>
    <div class="vcell" style="grid-column:1/-1"><div class="vlbl">Position</div><div class="vval">${vy.position}</div></div>
  `;

  // alerts
  document.getElementById("misAlerts").innerHTML = (m.alerts || []).map((a) => {
    const ic = a.level === "high" ? "⚠️" : a.level === "med" ? "🔶" : "ℹ️";
    return `<div class="alert ${a.level}"><span class="ic">${ic}</span>${a.text}</div>`;
  }).join("");

  // KPI cards
  const k = m.kpis;
  document.getElementById("misKpis").innerHTML = `
    <div class="mis-card"><h3>Technical Defects</h3>
      ${kpiRow("Open Defects", k.technical_defects["Open Defects"])}
      ${kpiRow("Overdue Defects", k.technical_defects["Overdue Defects"], k.technical_defects["Overdue Defects"] > 0)}
    </div>
    <div class="mis-card"><h3>Planned Maintenance</h3>
      ${kpiRow("Overdue Jobs", k.planned_maintenance["Overdue Standard Jobs"], k.planned_maintenance["Overdue Standard Jobs"] > 15)}
      ${kpiRow("Due Jobs", k.planned_maintenance["Due Standard Jobs"])}
      ${kpiRow("Critical Overdue", k.planned_maintenance["Critical Overdue Jobs"], k.planned_maintenance["Critical Overdue Jobs"] > 0)}
    </div>
    <div class="mis-card"><h3>Purchasing</h3>
      ${kpiRow("Critical Parts Pending", k.purchasing["Critical Parts - Pending"])}
      ${kpiRow("Invoices Breach >15d", k.purchasing["Invoices Breach > 15 Days"], k.purchasing["Invoices Breach > 15 Days"] > 30)}
      ${kpiRow("RFQ (not Evaluated)", k.purchasing["RFQ Completed (not Evaluated)"])}
      ${kpiRow("POs Pending Approval", k.purchasing["POs Pending Approval"], k.purchasing["POs Pending Approval"] > 5)}
    </div>
    <div class="mis-card"><h3>HSQE</h3>
      ${kpiRow("Vettings (12M)", k.hsqe["Vettings (Last 12M)"])}
      ${kpiRow("CARs Overdue", k.hsqe["CARs Overdue"], k.hsqe["CARs Overdue"] > 0)}
      ${kpiRow("Incidents Open", k.hsqe["Incidents - Open"])}
      ${kpiRow("Certs Expiring 3M", k.hsqe["Certificates Expiring 3M"])}
    </div>
  `;

  // particulars + crew tables
  document.getElementById("misParticulars").innerHTML =
    Object.entries(m.particulars).map(([kk, vv]) => `<tr><td>${kk}</td><td>${vv}</td></tr>`).join("");
  document.getElementById("misCrew").innerHTML =
    Object.entries(m.crew).map(([kk, vv]) => `<tr><td>${kk}</td><td>${vv}</td></tr>`).join("") +
    `<tr><td>Lifeboat Lowerings</td><td>${m.lifeboat_lowering}</td></tr>`;

  drawCharts(m);
}

function drawCharts(m) {
  const labels = m.fuel_trend.map((_, i) => `D${i + 1}`);
  const gridColor = "rgba(143,169,192,.15)";
  const tickColor = "#8fa9c0";

  if (fuelChart) fuelChart.destroy();
  fuelChart = new Chart(document.getElementById("fuelChart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "Fuel (MT/day)", data: m.fuel_trend, borderColor: "#ff8c1a",
          backgroundColor: "rgba(255,140,26,.15)", fill: true, tension: .35, pointRadius: 0 },
        { label: "Speed (kts)", data: m.speed_trend, borderColor: "#2ea6ff",
          fill: false, tension: .35, pointRadius: 0, yAxisID: "y1" },
      ],
    },
    options: {
      plugins: { legend: { labels: { color: tickColor, boxWidth: 12, font: { size: 10 } } } },
      scales: {
        x: { ticks: { color: tickColor, font: { size: 9 } }, grid: { color: gridColor } },
        y: { ticks: { color: tickColor, font: { size: 9 } }, grid: { color: gridColor } },
        y1: { position: "right", ticks: { color: tickColor, font: { size: 9 } }, grid: { display: false } },
      },
    },
  });

  if (budgetChart) budgetChart.destroy();
  budgetChart = new Chart(document.getElementById("budgetChart"), {
    type: "bar",
    data: {
      labels: m.budget.map((b) => b.account),
      datasets: [
        { label: "Annual", data: m.budget.map((b) => b.annual),
          backgroundColor: "rgba(46,166,255,.35)" },
        { label: "Spent", data: m.budget.map((b) => b.spent),
          backgroundColor: "#ff8c1a" },
      ],
    },
    options: {
      plugins: { legend: { labels: { color: tickColor, boxWidth: 12, font: { size: 10 } } } },
      scales: {
        x: { ticks: { color: tickColor, font: { size: 9 } }, grid: { display: false } },
        y: { ticks: { color: tickColor, font: { size: 9 }, callback: (v) => (v / 1e6).toFixed(1) + "M" },
             grid: { color: gridColor } },
      },
    },
  });
}

/* ---------------- SEARCH ---------------- */
document.getElementById("searchBox").addEventListener("input", (e) => {
  const q = e.target.value.trim().toLowerCase();
  if (!q) return;
  const hit = Object.values(markers).find((m) =>
    m._vessel.name.toLowerCase().includes(q));
  if (hit) {
    map.flyTo(hit.getLatLng(), 5, { duration: .8 });
    hit.openTooltip();
  }
});

/* ---------------- GO ---------------- */
poll();
setInterval(poll, POLL_MS);
