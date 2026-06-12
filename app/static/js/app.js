/* ---- Home OS & Fitness Hub — shared client behaviors ---- */

/** Dark / light theme toggle */
(function initTheme() {
  const btn = document.getElementById("theme-toggle");
  if (!btn) return;
  btn.addEventListener("click", () => {
    const dark = document.documentElement.classList.toggle("dark");
    localStorage.setItem("theme", dark ? "dark" : "light");
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", dark ? "#12141c" : "#f4f6fb");
  });
})();

/** PWA service worker */
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/static/sw.js").catch(() => {});
}

async function postJSON(url) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json();
}

/**
 * Workout set "completed" checkboxes.
 * Markup: <button data-set-toggle data-url="..."> with data-completed="1|0".
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

/**
 * Smart home light toggles.
 * Markup: <button data-light-toggle data-url="..."> with data-state="on|off".
 */
document.addEventListener("click", async (event) => {
  const toggle = event.target.closest("[data-light-toggle]");
  if (!toggle) return;

  toggle.disabled = true;
  try {
    const data = await postJSON(toggle.dataset.url);
    const card = toggle.closest("[data-light-card]");
    if (card) card.dataset.state = data.state;
    toggle.dataset.state = data.state;
    toggle.setAttribute("aria-checked", data.state === "on" ? "true" : "false");
  } catch (err) {
    console.error(err);
  } finally {
    toggle.disabled = false;
  }
});

/**
 * 3D printer panel auto-refresh (every 15s, only on the printer page).
 */
const printerPanel = document.querySelector("[data-printer-panel]");
if (printerPanel) {
  const url = printerPanel.dataset.statusUrl;
  setInterval(async () => {
    try {
      const s = await fetch(url, { headers: { Accept: "application/json" } }).then((r) => r.json());
      const bar = printerPanel.querySelector("[data-printer-bar]");
      const pct = printerPanel.querySelector("[data-printer-pct]");
      const eta = printerPanel.querySelector("[data-printer-eta]");
      if (bar) bar.style.width = `${s.progress}%`;
      if (pct) pct.textContent = `${s.progress}%`;
      if (eta) eta.textContent = s.time_remaining;
    } catch (err) {
      console.error(err);
    }
  }, 15000);
}
