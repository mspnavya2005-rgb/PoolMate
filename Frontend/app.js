/* AI-Enhanced Car Pooling - frontend logic (plain JavaScript, talks to the Flask REST API) */
const API = (location.protocol.startsWith("http") && location.port === "5000") ? "" : "http://127.0.0.1:5000";
let token = localStorage.getItem("cp_token") || "";
let user = JSON.parse(localStorage.getItem("cp_user") || "null");
let lastSearch = null;

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (iso) => new Date(iso).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });

function toast(msg, type = "ok") {
  const t = $("toast"); t.textContent = msg; t.className = "toast " + type;
  setTimeout(() => t.classList.add("hidden"), 3500);
}

async function api(path, method = "GET", body) {
  const res = await fetch(API + path, {
    method, headers: { "Content-Type": "application/json", ...(token ? { Authorization: "Bearer " + token } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && token) { logout(); }
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}
const safe = (fn) => async (...a) => { try { await fn(...a); } catch (e) { toast(e.message, "err"); } };

/* ---------------- tabs ---------------- */
function bindTabs(attr, prefix) {
  document.querySelectorAll(`[data-${attr}]`).forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll(`[data-${attr}]`).forEach((x) => x.classList.toggle("active", x === b));
    document.querySelectorAll(`[id^="${prefix}-"]`).forEach((s) => s.classList.add("hidden"));
    $(`${prefix}-${b.dataset[attr]}`).classList.remove("hidden");
    ({ rides: loadDriverRides, dhistory: () => loadHistory("driverHistory"), bookings: loadBookings,
       phistory: () => loadHistory("passengerHistory") })[b.dataset[attr]]?.();
  }));
}
document.querySelectorAll("[data-auth]").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll("[data-auth]").forEach((x) => x.classList.toggle("active", x === b));
  $("loginForm").classList.toggle("hidden", b.dataset.auth !== "login");
  $("registerForm").classList.toggle("hidden", b.dataset.auth !== "register");
}));
bindTabs("dtab", "dtab"); bindTabs("ptab", "ptab");
$("regRole").addEventListener("change", () => $("regPrefs").classList.toggle("hidden", $("regRole").value !== "passenger"));

/* ---------------- auth ---------------- */
$("registerForm").addEventListener("submit", safe(async (e) => {
  e.preventDefault();
  await api("/api/register", "POST", { name: $("regName").value, email: $("regEmail").value, phone: $("regPhone").value,
    password: $("regPassword").value, role: $("regRole").value, pref_ac: $("regAC").checked,
    pref_no_smoking: $("regNoSmoke").checked, pref_music: $("regMusic").checked });
  toast("Registered! Please login.");
  $("loginEmail").value = $("regEmail").value;
  document.querySelector('[data-auth="login"]').click();
}));

$("loginForm").addEventListener("submit", safe(async (e) => {
  e.preventDefault();
  const d = await api("/api/login", "POST", { email: $("loginEmail").value, password: $("loginPassword").value });
  token = d.token; user = d.user;
  localStorage.setItem("cp_token", token); localStorage.setItem("cp_user", JSON.stringify(user));
  await showApp();
}));

function logout() {
  token = ""; user = null; localStorage.removeItem("cp_token"); localStorage.removeItem("cp_user");
  ["driverView", "passengerView", "userBox"].forEach((i) => $(i).classList.add("hidden"));
  $("authView").classList.remove("hidden");
}
$("logoutBtn").addEventListener("click", logout);

async function showApp() {
  const locs = await api("/api/locations");
  document.querySelectorAll("select.loc").forEach((s) => { s.innerHTML = locs.map((l) => `<option>${esc(l)}</option>`).join(""); });
  $("sDest").selectedIndex = Math.min(1, locs.length - 1);
  $("authView").classList.add("hidden");
  $("userBox").classList.remove("hidden");
  $("userName").textContent = user.name; $("roleBadge").textContent = user.role;
  $("driverView").classList.toggle("hidden", user.role !== "driver");
  $("passengerView").classList.toggle("hidden", user.role !== "passenger");
  if (user.role === "passenger") {
    $("sAC").checked = user.pref_ac; $("sNoSmoke").checked = user.pref_no_smoking; $("sMusic").checked = user.pref_music;
    const t = new Date(Date.now() + 864e5); $("sDate").value = t.toISOString().slice(0, 10);
  } else {
    const t = new Date(Date.now() + 864e5); t.setMinutes(0); $("rTime").value = new Date(t - t.getTimezoneOffset() * 6e4).toISOString().slice(0, 16);
  }
}

/* ---------------- driver ---------------- */
$("rideForm").addEventListener("submit", safe(async (e) => {
  e.preventDefault();
  await api("/api/rides", "POST", { pickup: $("rPickup").value, destination: $("rDest").value, depart_time: $("rTime").value,
    seats: $("rSeats").value, price_per_seat: $("rPrice").value, vehicle: $("rVehicle").value,
    has_ac: $("rAC").checked, smoking_allowed: $("rSmoke").checked, music: $("rMusic").checked });
  toast("Ride posted!");
  document.querySelector('[data-dtab="rides"]').click();
}));

const statusPill = (s) => `<span class="pill ${esc(s)}">${esc(s)}</span>`;
const matchClass = (l) => (l === "Best Match" ? "best" : l === "Suitable Match" ? "suit" : "low");

async function loadDriverRides() {
  const rides = await api("/api/rides/mine");
  const open = rides.filter((r) => r.status === "open").length;
  const booked = rides.reduce((n, r) => n + r.bookings.filter((b) => b.status === "confirmed").reduce((m, b) => m + b.seats, 0), 0);
  let html = `<div class="stats"><div class="stat"><b>${rides.length}</b><span>Total rides</span></div>
    <div class="stat"><b>${open}</b><span>Open rides</span></div>
    <div class="stat"><b>${booked}</b><span>Seats booked</span></div>
    <div class="stat"><b>${rides[0]?.driver_rating ?? "-"}</b><span>Avg rating</span></div></div>`;
  html += rides.length ? rides.map((r) => `
    <div class="card"><div class="ride"><div>
      <h3>${esc(r.pickup)} → ${esc(r.destination)} ${statusPill(r.status)}</h3>
      <div class="meta">🕒 ${fmt(r.depart_time)} • 💺 ${r.seats_available}/${r.seats_total} free • ₹${r.price_per_seat}/seat • ${esc(r.vehicle) || "vehicle n/a"}<br>
      ${r.has_ac ? "❄️ AC" : "No AC"} • ${r.smoking_allowed ? "🚬 Smoking ok" : "🚭 No smoking"} • ${r.music ? "🎵 Music" : "🔇 Quiet"}</div></div>
      <div class="actions">${r.status === "open" ? `<button class="btn small ok" onclick="driverAct(${r.id},'complete')">Mark completed</button>
        <button class="btn small danger" onclick="driverAct(${r.id},'cancel')">Cancel</button>` : ""}</div></div>
      ${r.bookings.length ? `<div class="sub"><b>Passengers:</b><br>${r.bookings.map((b) =>
        `👤 ${esc(b.passenger_name)} — ${b.seats} seat(s), pickup <b>${esc(b.pickup_point)}</b> → drop <b>${esc(b.drop_point)}</b>
         <span class="pill ${matchClass(b.match_label)}">${esc(b.match_label)}</span> ${statusPill(b.status)}`).join("<br>")}</div>` : ""}
    </div>`).join("") : `<div class="card empty">You have not posted any rides yet.</div>`;
  $("driverRides").innerHTML = html;
}
window.driverAct = safe(async (id, act) => {
  if (!confirm(`Are you sure you want to ${act} this ride?`)) return;
  await api(`/api/rides/${id}/${act}`, "POST"); toast("Ride " + act + "d"); loadDriverRides();
});

/* ---------------- passenger: search + ML + GenAI ---------------- */
$("searchForm").addEventListener("submit", safe(async (e) => {
  e.preventDefault();
  if ($("sPickup").value === $("sDest").value) throw new Error("Pickup and destination must differ");
  const prefs = { pref_ac: $("sAC").checked, pref_no_smoking: $("sNoSmoke").checked, pref_music: $("sMusic").checked };
  await api("/api/me/preferences", "PUT", prefs);
  Object.assign(user, prefs); localStorage.setItem("cp_user", JSON.stringify(user));
  lastSearch = { pickup: $("sPickup").value, destination: $("sDest").value, date: $("sDate").value,
    time: $("sTime").value, seats: $("sSeats").value, ...prefs };
  const data = await api("/api/rides/search", "POST", lastSearch);
  renderResults(data.results);
  const box = $("aiRecommend"); box.classList.remove("hidden"); box.innerHTML = "<b>🤖 AI recommendation</b><pre>Thinking…</pre>";
  try { const r = await api("/api/ai/recommendations", "POST", lastSearch); box.innerHTML = aiHtml("🤖 Smart ride recommendation", r); }
  catch (er) { box.innerHTML = `<small>${esc(er.message)}</small>`; }
}));

const aiHtml = (title, r) => `<b>${title}</b><pre>${esc(r.text)}</pre>
  <small>${r.source.startsWith("llm") ? "Generated by " + esc(r.source) : esc(r.note || "Basic summary")}</small>`;

function renderResults(list) {
  $("searchResults").innerHTML = list.length ? list.map((c) => { const r = c.ride; return `
    <div class="card" id="res-${r.id}"><div class="ride"><div>
      <h3>${esc(r.pickup)} → ${esc(r.destination)}
        <span class="pill ${matchClass(c.ml.label)}">${esc(c.ml.label)} • ${c.ml.match_score}/100</span></h3>
      <div class="meta">👤 ${esc(r.driver_name)} ⭐ ${c.driver_rating} • 🕒 ${fmt(r.depart_time)} • 💺 ${r.seats_available} free • ₹${r.price_per_seat}/seat<br>
      📍 Pickup ${c.ml.features.pickup_distance_km} km away • 🏁 Drop ${c.ml.features.destination_distance_km} km away •
      ⏱ ${Math.round(c.ml.features.time_diff_min)} min from your time • Preferences ${c.ml.features.preference_score}/3<br>
      ${r.has_ac ? "❄️ AC" : "No AC"} • ${r.smoking_allowed ? "🚬 Smoking ok" : "🚭 No smoking"} • ${r.music ? "🎵 Music" : "🔇 Quiet"}</div></div>
      <div class="actions"><button class="btn small outline" onclick="getInsight(${r.id},'res-${r.id}')">🤖 AI insight</button>
        <button class="btn small" onclick="openBook(${r.id})">Book</button></div></div>
      <div class="ai-slot"></div></div>`; }).join("") : `<div class="card empty">No matching open rides found. Try another date or time.</div>`;
}

window.getInsight = safe(async (rideId, cardId) => {
  const slot = document.querySelector(`#${cardId} .ai-slot`);
  slot.innerHTML = `<div class="sub ai"><pre>Generating insight…</pre></div>`;
  const body = { ride_id: rideId, ...(lastSearch ? { pickup: lastSearch.pickup, destination: lastSearch.destination, date: lastSearch.date, time: lastSearch.time } : {}) };
  const r = await api("/api/ai/insights", "POST", body);
  slot.innerHTML = `<div class="sub ai">${aiHtml("🤖 Trip insight", r)}</div>`;
});

window.openBook = safe(async (rideId) => {
  const seats = lastSearch?.seats || 1;
  const pick = lastSearch?.pickup, drop = lastSearch?.destination;
  if (!confirm(`Book ${seats} seat(s)?\nYour pickup: ${pick}\nYour drop: ${drop}`)) return;
  const b = await api("/api/bookings", "POST", { ride_id: rideId, seats: Number(seats), pickup_point: pick, drop_point: drop });
  toast(`Booked! ML match: ${b.match_label}`);
  const data = await api("/api/rides/search", "POST", lastSearch); renderResults(data.results);
});

/* ---------------- passenger: bookings / schedule ---------------- */
async function loadBookings() {
  const list = await api("/api/bookings/mine");
  const upcoming = list.filter((b) => b.status === "confirmed"), past = list.filter((b) => b.status !== "confirmed");
  const card = (b) => `<div class="card" id="bk-${b.id}"><div class="ride"><div>
      <h3>${esc(b.ride.pickup)} → ${esc(b.ride.destination)} ${statusPill(b.status)}
        <span class="pill ${matchClass(b.match_label)}">${esc(b.match_label)}</span></h3>
      <div class="meta">🕒 ${fmt(b.ride.depart_time)} • 👤 ${esc(b.ride.driver_name)} • 💺 ${b.seats} seat(s) • ₹${b.seats * b.ride.price_per_seat}<br>
      📍 My pickup: <b>${esc(b.pickup_point)}</b> • 🏁 My drop: <b>${esc(b.drop_point)}</b>${b.rating ? `<br>⭐ You rated ${b.rating}/5` : ""}</div></div>
      <div class="actions"><button class="btn small outline" onclick="getInsight(${b.ride.id},'bk-${b.id}')">🤖 AI insight</button>
      ${b.status === "confirmed" ? `<button class="btn small danger" onclick="cancelBooking(${b.id})">Cancel</button>` : ""}
      ${b.status === "completed" && !b.rating ? `<button class="btn small ok" onclick="rateBooking(${b.id})">Rate driver</button>` : ""}</div></div>
      <div class="ai-slot"></div></div>`;
  $("myBookings").innerHTML = `<h2>📅 Upcoming travel schedule</h2>${upcoming.map(card).join("") || '<div class="card empty">No upcoming rides.</div>'}
    <h2>Past bookings</h2>${past.map(card).join("") || '<div class="card empty">Nothing yet.</div>'}`;
}
window.cancelBooking = safe(async (id) => {
  if (!confirm("Cancel this booking?")) return;
  await api(`/api/bookings/${id}/cancel`, "POST"); toast("Booking cancelled"); loadBookings();
});
window.rateBooking = safe(async (id) => {
  const v = Number(prompt("Rate the driver (1-5):", "5"));
  if (!v) return;
  const review = prompt("Short review (optional):", "") || "";
  await api(`/api/bookings/${id}/rate`, "POST", { rating: v, review }); toast("Thanks for rating!"); loadBookings();
});

/* ---------------- ride history dashboard (both roles) ---------------- */
async function loadHistory(target) {
  const h = await api("/api/history");
  const s = h.stats;
  const stats = h.role === "passenger"
    ? [[s.completed, "Completed rides"], [s.cancelled, "Cancelled"], ["₹" + s.total_spent, "Total spent"]]
    : [[s.completed, "Completed rides"], [s.cancelled, "Cancelled"], ["₹" + s.total_earned, "Total earned"], [s.avg_rating ?? "-", "Avg rating"]];
  const rows = h.items.map((i) => h.role === "passenger"
    ? `<div class="card"><h3>${esc(i.ride.pickup)} → ${esc(i.ride.destination)} ${statusPill(i.status)}</h3>
       <div class="meta">${fmt(i.ride.depart_time)} • Driver ${esc(i.ride.driver_name)} • ${i.seats} seat(s) • ${esc(i.match_label)}${i.rating ? " • ⭐ " + i.rating : ""}</div></div>`
    : `<div class="card"><h3>${esc(i.pickup)} → ${esc(i.destination)} ${statusPill(i.status)}</h3>
       <div class="meta">${fmt(i.depart_time)} • ₹${i.price_per_seat}/seat • ${i.seats_total - i.seats_available}/${i.seats_total} seats were booked</div></div>`).join("");
  $(target).innerHTML = `<div class="stats">${stats.map(([v, l]) => `<div class="stat"><b>${v}</b><span>${l}</span></div>`).join("")}</div>${rows || '<div class="card empty">No ride history yet.</div>'}`;
}

/* ---------------- start ---------------- */
if (token && user) showApp().catch(logout);
