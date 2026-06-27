/* Fleet Monitoring Dashboard — frontend
 * Hybrid satellite map of live AIS positions; click a vessel for its MIS
 * dashboard with drill-down detail behind every KPI.
 */

const POLL_MS = 4000;
const markers = {};
let selectedId = null;
let fuelChart = null, budgetChart = null;
let currentMIS = null;          // full MIS payload of the open vessel (for drill-down)

/* ---------------- MAP (hybrid satellite) ---------------- */
const map = L.map("map", {
  worldCopyJump: true, minZoom: 2,
  maxBounds: [[-85, -200], [85, 200]], maxBoundsViscosity: 0.6,
}).setView([25, 10], 3);

// Base: Esri world imagery (satellite)
L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  { attribution: "Imagery &copy; Esri", maxZoom: 18 }
).addTo(map);

// Overlay: place names / boundaries -> makes it a HYBRID view
L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
  { maxZoom: 18, opacity: 0.9 }
).addTo(map);

/* Modern custom vessel marker (sleek hull), rotated to heading */
function vesselDivIcon(heading, selected) {
  const fill = selected ? "#00d2ff" : "#ff6a00";
  return L.divIcon({
    className: "vessel-icon",
    html: `<div style="transform:rotate(${heading}deg)">
      <svg width="26" height="28" viewBox="0 0 28 30">
        <path d="M14 1 C18 7 21 13 21 21 L21 26 L14 23 L7 26 L7 21 C7 13 10 7 14 1 Z"
              fill="${fill}" stroke="#ffffff" stroke-width="2" stroke-linejoin="round"/>
        <circle cx="14" cy="14.5" r="2.4" fill="#ffffff"/>
      </svg></div>`,
    iconSize: [26, 28], iconAnchor: [13, 14],
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
  } catch (e) { setLive(false); }
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
      const m = L.marker([v.lat, v.lon], { icon: vesselDivIcon(v.heading, false) }).addTo(map);
      m._vessel = v;
      m.bindTooltip(`${v.name} — ${v.sog.toFixed(1)} Kts`, {
        permanent: false, direction: "top", className: "vessel-label" });
      m.on("click", () => openMIS(v.id));
      markers[v.id] = m;
    }
  });
  document.getElementById("statTotal").textContent = vessels.length;
  document.getElementById("statUnderway").textContent = counts["Underway"] || 0;
  document.getElementById("statAnchor").textContent = counts["At Anchor"] || 0;
  document.getElementById("statManeuver").textContent = counts["Maneuvering"] || 0;
  document.getElementById("statAvgSpeed").textContent = (speedSum / vessels.length).toFixed(1);
}

function setLive(ok, count) {
  const pill = document.getElementById("livePill");
  const meta = document.getElementById("liveMeta");
  const now = new Date().toLocaleTimeString();
  if (ok) { pill.classList.remove("stale"); meta.textContent = `${count} vessels · ${now}`; }
  else { pill.classList.add("stale"); meta.textContent = "feed unavailable"; }
}

/* ---------------- MIS PANEL ---------------- */
const panel = document.getElementById("misPanel");
const scrim = document.getElementById("scrim");

async function openMIS(id) {
  selectedId = id;
  Object.values(markers).forEach((m) =>
    m.setIcon(vesselDivIcon(m._vessel.heading, m._vessel.id === id)));
  if (markers[id]) map.panTo(markers[id].getLatLng(), { animate: true });

  panel.classList.add("open"); scrim.classList.add("show");
  panel.setAttribute("aria-hidden", "false");
  document.getElementById("misContent").hidden = true;
  document.getElementById("misLoading").style.display = "block";

  try {
    const res = await fetch(`/api/vessels/${id}/mis`);
    currentMIS = await res.json();
    renderMIS(currentMIS);
  } catch (e) {
    document.getElementById("misLoading").textContent = "Failed to load vessel data.";
  }
}

function closeMIS() {
  panel.classList.remove("open"); scrim.classList.remove("show");
  panel.setAttribute("aria-hidden", "true");
  selectedId = null; currentMIS = null;
  Object.values(markers).forEach((m) => m.setIcon(vesselDivIcon(m._vessel.heading, false)));
}
document.getElementById("misClose").addEventListener("click", closeMIS);
scrim.addEventListener("click", closeMIS);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeMIS(); });

function statusBadge(status) {
  const cls = { "Underway": "underway", "At Anchor": "anchor", "Maneuvering": "maneuver" }[status] || "underway";
  return `<span class="badge ${cls}">${status}</span>`;
}

/* a KPI row; pass drillKey to make it expandable */
function kpiRow(label, val, drillKey, bad) {
  const drillAttrs = drillKey ? ` drillable" data-drill="${drillKey}` : "";
  const chev = drillKey ? `<i data-lucide="chevron-right" class="chev"></i>` : "";
  return `<div class="kpi-row${drillAttrs}">
    <span>${label}</span>
    <span class="v ${bad ? "bad" : ""}">${val}${chev}</span></div>`;
}

function renderMIS(m) {
  document.getElementById("misLoading").style.display = "none";
  document.getElementById("misContent").hidden = false;

  document.getElementById("misName").textContent = m.name;
  document.getElementById("misSub").textContent =
    `IMO ${m.particulars.IMO} · ${m.particulars.Type} · ${m.particulars.Flag}`;

  const vy = m.voyage;
  document.getElementById("misVoyage").innerHTML = `
    <div class="vcell"><div class="vlbl">Status</div><div class="vval">${statusBadge(vy.status)}</div></div>
    <div class="vcell"><div class="vlbl">Speed / Course</div><div class="vval">${vy.sog} kts · ${vy.cog}°</div></div>
    <div class="vcell"><div class="vlbl">Destination</div><div class="vval">${vy.destination}</div></div>
    <div class="vcell" style="grid-column:1/-1"><div class="vlbl">Position</div><div class="vval">${vy.position}</div></div>`;

  document.getElementById("misAlerts").innerHTML = (m.alerts || []).map((a) => {
    const ic = a.level === "high" ? "alert-triangle" : a.level === "med" ? "alert-circle" : "info";
    return `<div class="alert ${a.level}"><i data-lucide="${ic}"></i>${a.text}</div>`;
  }).join("");

  const k = m.kpis;
  document.getElementById("misKpis").innerHTML = `
    <div class="mis-card"><h3><i data-lucide="wrench"></i>Technical Defects</h3>
      ${kpiRow("Open Defects", k.technical_defects["Open Defects"], "open_defects")}
      ${kpiRow("Overdue Defects", k.technical_defects["Overdue Defects"], "overdue_defects", k.technical_defects["Overdue Defects"] > 0)}
    </div>
    <div class="mis-card"><h3><i data-lucide="calendar-clock"></i>Planned Maintenance</h3>
      ${kpiRow("Overdue Jobs", k.planned_maintenance["Overdue Standard Jobs"], "overdue_jobs", k.planned_maintenance["Overdue Standard Jobs"] > 15)}
      ${kpiRow("Due Jobs", k.planned_maintenance["Due Standard Jobs"])}
      ${kpiRow("Critical Overdue", k.planned_maintenance["Critical Overdue Jobs"], "critical_overdue_jobs", k.planned_maintenance["Critical Overdue Jobs"] > 0)}
    </div>
    <div class="mis-card"><h3><i data-lucide="shopping-cart"></i>Purchasing</h3>
      ${kpiRow("Critical Parts Pending", k.purchasing["Critical Parts - Pending"])}
      ${kpiRow("Invoices Breach >15d", k.purchasing["Invoices Breach > 15 Days"], "invoices_breach", k.purchasing["Invoices Breach > 15 Days"] > 30)}
      ${kpiRow("RFQ (not Evaluated)", k.purchasing["RFQ Completed (not Evaluated)"])}
      ${kpiRow("POs Pending Approval", k.purchasing["POs Pending Approval"], "pos_pending", k.purchasing["POs Pending Approval"] > 5)}
    </div>
    <div class="mis-card"><h3><i data-lucide="shield-check"></i>HSQE</h3>
      ${kpiRow("Vettings (12M)", k.hsqe["Vettings (Last 12M)"])}
      ${kpiRow("CARs Overdue", k.hsqe["CARs Overdue"], null, k.hsqe["CARs Overdue"] > 0)}
      ${kpiRow("Incidents Open", k.hsqe["Incidents - Open"], "incidents_open")}
      ${kpiRow("Certs Expiring 3M", k.hsqe["Certificates Expiring 3M"], "certs_expiring")}
    </div>`;

  document.getElementById("misParticulars").innerHTML =
    Object.entries(m.particulars).map(([kk, vv]) => `<tr><td>${kk}</td><td>${vv}</td></tr>`).join("");
  document.getElementById("misCrew").innerHTML =
    Object.entries(m.crew).map(([kk, vv]) => `<tr><td>${kk}</td><td>${vv}</td></tr>`).join("") +
    `<tr><td>Lifeboat Lowerings</td><td>${m.lifeboat_lowering}</td></tr>`;

  drawCharts(m);
  lucide.createIcons();
}

/* ---------------- DRILL-DOWN ---------------- */
document.getElementById("misKpis").addEventListener("click", (e) => {
  const row = e.target.closest(".kpi-row.drillable");
  if (!row || !currentMIS) return;
  const key = row.dataset.drill;

  const next = row.nextElementSibling;
  if (next && next.classList.contains("drill-detail")) {
    next.remove(); row.classList.remove("open");
    lucide.createIcons(); return;
  }
  row.classList.add("open");
  const detail = document.createElement("div");
  detail.className = "drill-detail";
  detail.innerHTML = buildDrillTable(currentMIS.drill[key]);
  row.after(detail);
  lucide.createIcons();
});

function buildDrillTable(d) {
  if (!d || d.total === 0 || d.rows.length === 0)
    return `<div class="drill-empty">No records — nothing to action. ✔</div>`;
  const cols = Object.keys(d.rows[0]);
  const head = cols.map((c) => `<th>${c}</th>`).join("");
  const body = d.rows.map((r) =>
    `<tr>${cols.map((c) => {
      const sevCol = (c === "Severity");
      const cell = sevCol ? `<span class="sev-${r[c]}">${r[c]}</span>` : r[c];
      return `<td>${cell}</td>`;
    }).join("")}</tr>`).join("");
  const foot = d.rows.length < d.total
    ? `<div class="drill-foot">Showing ${d.rows.length} of ${d.total} records</div>` : "";
  return `<div class="scroll"><table class="drill-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>${foot}`;
}

/* ---------------- CHARTS (light theme) ---------------- */
function drawCharts(m) {
  const labels = m.fuel_trend.map((_, i) => `D${i + 1}`);
  const grid = "rgba(24,41,60,.08)";
  const tick = "#687a8d";

  if (fuelChart) fuelChart.destroy();
  fuelChart = new Chart(document.getElementById("fuelChart"), {
    type: "line",
    data: { labels, datasets: [
      { label: "Fuel (MT/day)", data: m.fuel_trend, borderColor: "#ff6a00",
        backgroundColor: "rgba(255,106,0,.12)", fill: true, tension: .35, pointRadius: 0 },
      { label: "Speed (kts)", data: m.speed_trend, borderColor: "#0b63d6",
        fill: false, tension: .35, pointRadius: 0, yAxisID: "y1" } ] },
    options: { plugins: { legend: { labels: { color: tick, boxWidth: 12, font: { size: 10 } } } },
      scales: {
        x: { ticks: { color: tick, font: { size: 9 } }, grid: { color: grid } },
        y: { ticks: { color: tick, font: { size: 9 } }, grid: { color: grid } },
        y1: { position: "right", ticks: { color: tick, font: { size: 9 } }, grid: { display: false } } } },
  });

  if (budgetChart) budgetChart.destroy();
  budgetChart = new Chart(document.getElementById("budgetChart"), {
    type: "bar",
    data: { labels: m.budget.map((b) => b.account), datasets: [
      { label: "Annual", data: m.budget.map((b) => b.annual), backgroundColor: "rgba(11,99,214,.35)" },
      { label: "Spent", data: m.budget.map((b) => b.spent), backgroundColor: "#ff6a00" } ] },
    options: { plugins: { legend: { labels: { color: tick, boxWidth: 12, font: { size: 10 } } } },
      scales: {
        x: { ticks: { color: tick, font: { size: 9 } }, grid: { display: false } },
        y: { ticks: { color: tick, font: { size: 9 }, callback: (v) => (v / 1e6).toFixed(1) + "M" }, grid: { color: grid } } } },
  });
}

/* ---------------- SEARCH ---------------- */
document.getElementById("searchBox").addEventListener("input", (e) => {
  const q = e.target.value.trim().toLowerCase();
  if (!q) return;
  const hit = Object.values(markers).find((m) => m._vessel.name.toLowerCase().includes(q));
  if (hit) { map.flyTo(hit.getLatLng(), 5, { duration: .8 }); hit.openTooltip(); }
});

/* ---------------- GO ---------------- */
lucide.createIcons();   // brand + stat-strip icons
poll();
setInterval(poll, POLL_MS);
