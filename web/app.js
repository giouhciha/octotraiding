// OctoTrading — lógica de la PWA (sin frameworks, para que sea simple y rápida).

const $ = (id) => document.getElementById(id);

// --- Utilidades ---
const fmtMoney = (v) => {
  const n = Number(v);
  if (!isFinite(n)) return "—";
  const dec = n >= 1000 ? 0 : 2;
  return "$" + n.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
};
const fmtPct = (v) => (v >= 0 ? "+" : "") + (Number(v) * 100).toFixed(1) + "%";
const signalClass = (s) => (s.includes("COMPRA") ? "buy" : s.includes("VENTA") ? "sell" : "hold");
const shortTime = (iso) => {
  try { return new Date(iso).toLocaleString("es", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }); }
  catch { return iso; }
};

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error((await r.text()).slice(0, 200));
  return r.json();
}

function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove("show"), 2600);
}

// --- Render ---
let CURRENT = null;

function actionClass(a) {
  if (a === "COMPRAR") return "buy";
  if (a === "VENDER") return "sell";
  return "hold";
}

function render(state) {
  CURRENT = state;
  const latest = state.latest;
  const settings = state.settings;
  const holding = !!state.holding;

  // Insignia = ACCIÓN (depende de si el usuario tiene compra o no)
  const badge = $("hero-badge");
  badge.textContent = state.action || "—";
  badge.className = "badge " + actionClass(state.action);

  // Banner de acción + botón
  $("action-hint").textContent = state.action_hint || "";
  const btn = $("btn-position");
  if (holding) {
    btn.textContent = state.exit_signaled ? "Ya vendí ✔" : "Ya vendí";
    btn.classList.toggle("danger", !!state.exit_signaled);
    btn.dataset.mode = "sell";
  } else {
    btn.textContent = "Compré";
    btn.classList.remove("danger");
    btn.dataset.mode = "buy";
  }

  if (!latest) {
    $("hero-narrative").textContent = "Aún no hay análisis. Espera el primer ciclo.";
    return;
  }

  $("hero-symbol").textContent = latest.symbol;
  $("hero-name").textContent = "";
  $("hero-price").textContent = fmtMoney(latest.price);

  $("hero-score").textContent = (latest.score >= 0 ? "+" : "") + Number(latest.score).toFixed(2);
  const pct = ((Number(latest.score) + 10) / 20) * 100;
  $("score-fill").style.width = Math.max(2, Math.min(100, pct)) + "%";
  $("hero-narrative").textContent = latest.narrative || "";

  // Chips de contexto (señal cruda + contexto)
  const chips = [];
  chips.push("Señal: " + latest.signal);
  if (latest.regime) chips.push("Régimen: " + latest.regime);
  if (latest.daily_trend) chips.push("Tendencia diaria: " + latest.daily_trend);
  chips.push("Actualizado: " + shortTime(latest.ts));
  $("hero-chips").innerHTML = chips.map((c) => `<span class="chip">${c}</span>`).join("");

  // Niveles: si hay posición, los de TU posición; si no, los sugeridos por la señal.
  let entry, stop, target, rr;
  if (state.position) {
    const p = state.position;
    entry = p.entry; stop = p.stop; target = p.target;
    rr = (target - entry) / (entry - stop);
  } else {
    entry = latest.entry; stop = latest.stop; target = latest.target; rr = latest.rr;
  }
  const showLevels = holding || latest.signal.includes("COMPRA");
  $("levels-card").style.display = showLevels ? "" : "none";
  $("lv-entry").textContent = fmtMoney(entry);
  $("lv-stop").textContent = fmtMoney(stop);
  $("lv-target").textContent = fmtMoney(target);
  $("lv-rr").textContent = "1 : " + Number(rr).toFixed(2);

  const capital = Number(settings.capital) || 0;
  if (state.position) {
    const p = state.position;
    $("lv-position").innerHTML =
      `Tienes posición desde <b>${fmtMoney(p.entry)}</b> · stop actual <b>${fmtMoney(p.stop)}</b>.`;
  } else if (capital > 0 && latest.signal.includes("COMPRA")) {
    const amount = capital * Number(latest.position_pct);
    $("lv-position").innerHTML =
      `Con ${fmtMoney(capital)} y riesgo ${(settings.risk_pct * 100).toFixed(1)}% → compra sugerida de <b>${fmtMoney(amount)}</b>.`;
  } else {
    $("lv-position").textContent = "Sin posición abierta.";
  }
}

// --- Carga de datos ---
async function loadAll() {
  try {
    const state = await api("/api/state");
    render(state);
    const [hist, evs] = await Promise.all([api("/api/reports?limit=24"), api("/api/events?limit=30")]);
    renderHistory(hist.reports);
    renderEvents(evs.events);
  } catch (e) {
    toast("No se pudo conectar con el servidor");
  }
}

function renderHistory(reports) {
  const ul = $("history");
  if (!reports.length) { ul.innerHTML = '<li class="muted">Sin historial.</li>'; return; }
  ul.innerHTML = reports.map((r) => `
    <li>
      <div>
        <div>${r.signal} <span class="time">· ${shortTime(r.ts)}</span></div>
        <div class="time">${fmtMoney(r.price)}</div>
      </div>
      <span class="badge ${signalClass(r.signal)}">${Number(r.score) >= 0 ? "+" : ""}${Number(r.score).toFixed(1)}</span>
    </li>`).join("");
}

function renderEvents(events) {
  const ul = $("events");
  if (!events.length) { ul.innerHTML = '<li class="muted">Sin alertas todavía.</li>'; return; }
  const icon = { OPEN: "🟢", CLOSE: "🔴", TRAIL_STOP_SUBIO: "🔒" };
  ul.innerHTML = events.map((e) => `
    <li>
      <div>
        <div>${icon[e.type] || "🔔"} ${e.message}</div>
        <div class="time">${shortTime(e.ts)}</div>
      </div>
    </li>`).join("");
}

// --- Cambiar activo ---
async function openChange() {
  const data = await api("/api/assets");
  renderAssetList(data.assets);
  $("set-interval"); // no-op
  $("dlg-change").showModal();
  $("search").value = "";
  $("search").focus();
}

function renderAssetList(assets) {
  $("asset-list").innerHTML = assets.map((a) =>
    `<li data-symbol="${a.symbol}"><span>${a.name}</span><span class="muted mono">${a.symbol}</span></li>`
  ).join("");
}

async function track(symbol) {
  toast("Cambiando a " + symbol + "…");
  await api("/api/track", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol }),
  });
  $("dlg-change").close();
  await loadAll();
  toast("Ahora sigues " + symbol);
}

// --- Ajustes ---
function openSettings() {
  const s = CURRENT.settings;
  $("set-capital").value = s.capital;
  $("set-risk").value = (s.risk_pct * 100).toFixed(1);
  $("set-qstart").value = s.quiet_start;
  $("set-qend").value = s.quiet_end;
  const sel = $("set-interval");
  sel.innerHTML = Object.entries(CURRENT.intervals || { "1h": "Cada hora" })
    .map(([k, v]) => `<option value="${k}">${v}</option>`).join("");
  sel.value = s.interval;
  $("dlg-settings").showModal();
}

async function togglePosition() {
  const btn = $("btn-position");
  const mode = btn.dataset.mode;
  btn.disabled = true;
  try {
    if (mode === "sell") {
      await api("/api/position/sell", { method: "POST" });
      toast("Venta registrada. Estás fuera del mercado.");
    } else {
      await api("/api/position/buy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      toast("Compra registrada. La app vigilará tu salida.");
    }
    await loadAll();
  } catch (_) {
    toast("No se pudo registrar la operación");
  }
  btn.disabled = false;
}

async function saveSettings() {
  await api("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      capital: Number($("set-capital").value),
      risk_pct: Number($("set-risk").value) / 100,
      quiet_start: Number($("set-qstart").value),
      quiet_end: Number($("set-qend").value),
      interval: $("set-interval").value,
    }),
  });
  $("dlg-settings").close();
  await loadAll();
  toast("Ajustes guardados");
}

// --- Notificaciones push ---
function urlBase64ToUint8Array(base64) {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const b64 = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(b64);
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

async function enableNotifications() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    toast("Tu navegador no soporta avisos. Usa Chrome en Android.");
    return;
  }
  const perm = await Notification.requestPermission();
  if (perm !== "granted") { toast("Permiso de notificaciones denegado"); return; }
  const reg = await navigator.serviceWorker.ready;
  const { publicKey } = await api("/api/push/public-key");
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(publicKey),
  });
  const j = sub.toJSON();
  await api("/api/push/subscribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ endpoint: j.endpoint, keys: j.keys }),
  });
  $("btn-notify").classList.add("active");
  toast("Notificaciones activadas ✅");
}

// --- Eventos de UI ---
function bind() {
  $("btn-change").addEventListener("click", openChange);
  $("btn-settings").addEventListener("click", openSettings);
  $("btn-position").addEventListener("click", togglePosition);
  $("btn-save-settings").addEventListener("click", saveSettings);
  $("btn-notify").addEventListener("click", enableNotifications);
  $("btn-test-push").addEventListener("click", async () => {
    const r = await api("/api/push/test", { method: "POST" });
    toast(r.sent ? "Prueba enviada" : "No hay dispositivos suscritos");
  });
  $("search").addEventListener("input", (e) => {
    api("/api/assets?q=" + encodeURIComponent(e.target.value)).then((d) => renderAssetList(d.assets));
  });
  $("asset-list").addEventListener("click", (e) => {
    const li = e.target.closest("li[data-symbol]");
    if (li) track(li.dataset.symbol);
  });
  document.querySelectorAll("[data-close]").forEach((b) =>
    b.addEventListener("click", () => b.closest("dialog").close())
  );
}

// --- Arranque ---
async function main() {
  bind();
  if ("serviceWorker" in navigator) {
    try { await navigator.serviceWorker.register("/sw.js"); } catch (_) {}
  }
  await loadAll();
  setInterval(loadAll, 60_000);
}

main();
