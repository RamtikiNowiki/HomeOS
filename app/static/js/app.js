/* ========================================================
   Home OS & Fitness Hub — shared client behaviors
   ======================================================== */

/** ── Theme toggle ──────────────────────────────────────
 *  Works for both the mobile header and the desktop sidebar.
 *  All theme-toggle buttons carry data-action="toggle-theme".
 */
document.addEventListener("click", (event) => {
  const btn = event.target.closest("[data-action='toggle-theme']");
  if (!btn) return;
  const dark = document.documentElement.classList.toggle("dark");
  localStorage.setItem("theme", dark ? "dark" : "light");
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", dark ? "#0b0d16" : "#f4f6fb");
});

/** ── Form confirm dialogs ──────────────────────────────
 *  <form data-confirm="Are you sure?"> intercepts submit.
 */
document.addEventListener("submit", (event) => {
  const form = event.target.closest("form[data-confirm]");
  if (!form) return;
  if (!confirm(form.dataset.confirm)) event.preventDefault();
});

/** ── PWA service worker (root scope — required for Install app) ── */
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {});
  });
}

/** ── JSON POST helper ────────────────────────────────── */
async function postJSON(url) {
  const res = await fetch(url, {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json();
}

/** ── Workout set completed toggle ──────────────────────
 *  <button data-set-toggle data-url="..." data-completed="1|0">
 */
document.addEventListener("click", async (event) => {
  const toggle = event.target.closest("[data-set-toggle]");
  if (!toggle) return;
  toggle.disabled = true;
  try {
    const data = await postJSON(toggle.dataset.url);
    toggle.dataset.completed = data.completed ? "1" : "0";
    const row = toggle.closest("[data-set-row]");
    if (row) row.dataset.completed = toggle.dataset.completed;
  } catch (err) {
    console.error(err);
  } finally {
    toggle.disabled = false;
  }
});

/** ── Smart home light toggles ──────────────────────────
 *  <button data-light-toggle data-url="..." data-state="on|off">
 */
document.addEventListener("click", async (event) => {
  const toggle = event.target.closest("[data-light-toggle]");
  if (!toggle) return;
  toggle.disabled = true;
  try {
    const data = await postJSON(toggle.dataset.url);
    const card = toggle.closest("[data-light-card]");
    if (card) {
      card.dataset.state = data.state;
      card.classList.toggle("light-card-live", data.state === "on");
    }
    toggle.dataset.state = data.state;
    toggle.setAttribute("aria-checked", data.state === "on" ? "true" : "false");
  } catch (err) {
    console.error(err);
  } finally {
    toggle.disabled = false;
  }
});

/** ── User prefs from server (sync localStorage on load) ─ */
document.addEventListener("DOMContentLoaded", () => {
  const rest = document.body.dataset.defaultRest;
  if (rest && !localStorage.getItem("fitness-rest-seconds")) {
    localStorage.setItem("fitness-rest-seconds", rest);
  }
});

/** ── 3D printer panel — live status + controls ───────── */
const printerPanel = document.querySelector("[data-printer-panel]");
if (printerPanel) {
  const statusUrl = printerPanel.dataset.statusUrl;

  function applyPrinterStatus(s) {
    const bar = printerPanel.querySelector("[data-printer-bar]");
    const pct = printerPanel.querySelector("[data-printer-pct]");
    const eta = printerPanel.querySelector("[data-printer-eta]");
    const elapsed = printerPanel.querySelector("[data-printer-elapsed]");
    const nozzle = printerPanel.querySelector("[data-printer-nozzle]");
    const bed = printerPanel.querySelector("[data-printer-bed]");
    const layer = printerPanel.querySelector("[data-printer-layer]");
    const fan = printerPanel.querySelector("[data-printer-fan]");
    const speed = printerPanel.querySelector("[data-printer-speed]");
    if (bar) {
      bar.style.width = `${s.progress}%`;
      bar.classList.toggle("printer-bar-live", s.state === "printing");
    }
    if (pct) pct.textContent = `${s.progress}%`;
    if (eta) eta.textContent = s.time_remaining;
    if (elapsed) elapsed.textContent = s.time_elapsed;
    if (nozzle) nozzle.innerHTML = `${s.nozzle_temp}<span class="text-xs text-slate-500 font-body"> / ${s.nozzle_target} °C</span>`;
    if (bed) bed.innerHTML = `${s.bed_temp}<span class="text-xs text-slate-500 font-body"> / ${s.bed_target} °C</span>`;
    if (layer) layer.innerHTML = `${s.layer_current}<span class="text-xs text-slate-500 font-body"> / ${s.layer_total}</span>`;
    if (fan && s.fan_speed_pct != null) fan.innerHTML = `${s.fan_speed_pct}<span class="text-xs text-slate-500 font-body"> %</span>`;
    if (speed) speed.innerHTML = `${s.print_speed_pct}<span class="text-xs text-slate-500 font-body"> %</span>`;

    printerPanel.querySelector('[data-printer-action="pause"]')?.toggleAttribute("disabled", !s.can_pause);
    printerPanel.querySelector('[data-printer-action="resume"]')?.toggleAttribute("disabled", !s.can_resume);
    printerPanel.querySelector('[data-printer-action="cancel"]')?.toggleAttribute("disabled", !s.can_cancel);
  }

  async function refreshStatus() {
    const s = await fetch(statusUrl, { headers: { Accept: "application/json" } }).then((r) => r.json());
    applyPrinterStatus(s);
  }

  setInterval(() => refreshStatus().catch(console.error), 12000);

  const webcam = printerPanel.querySelector("[data-printer-webcam]");
  const webcamUrl = printerPanel.dataset.webcamUrl;
  if (webcam && webcamUrl) {
    setInterval(() => {
      webcam.src = `${webcamUrl}?t=${Date.now()}`;
    }, 3000);
  }

  printerPanel.addEventListener("click", async (e) => {
    const preheatBtn = e.target.closest("[data-preheat]");
    if (preheatBtn) {
      const preset = preheatBtn.dataset.preheat;
      if (preset === "off" && !confirm("Turn off bed and nozzle heaters?")) return;
      preheatBtn.disabled = true;
      try {
        const s = await postJSON(printerPanel.dataset.preheatUrl, { preset });
        applyPrinterStatus(s);
      } catch (err) {
        console.error(err);
        alert("Preheat command failed.");
      } finally {
        preheatBtn.disabled = false;
      }
      return;
    }

    const btn = e.target.closest("[data-printer-action]");
    if (!btn || btn.disabled) return;
    const action = btn.dataset.printerAction;
    if (action === "cancel" && !confirm("Cancel the current print job?")) return;
    btn.disabled = true;
    try {
      const url =
        action === "pause" ? printerPanel.dataset.pauseUrl
        : action === "resume" ? printerPanel.dataset.resumeUrl
        : `${printerPanel.dataset.cancelUrl}?confirm=1`;
      const s = await postJSON(url);
      applyPrinterStatus(s);
    } catch (err) {
      console.error(err);
      alert("Printer command failed — check Moonraker is reachable.");
    } finally {
      btn.disabled = false;
    }
  });
}
