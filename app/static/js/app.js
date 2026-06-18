/* ========================================================
   Home OS & Fitness Hub — shared client behaviors
   ======================================================== */

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
async function postJSON(url, body) {
  const opts = {
    method: "POST",
    headers: { Accept: "application/json" },
  };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(url, opts);
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

/** ── 3D printer panel — live status, camera, mobile controls ── */
function initPrinterPanel() {
  const printerPanel = document.querySelector("[data-printer-panel]");
  if (!printerPanel) return;

  const statusUrl = printerPanel.dataset.statusUrl;
  const stickyBar = document.querySelector("[data-printer-sticky-bar]");
  const cameraStage = printerPanel.querySelector("[data-printer-camera-stage]");
  const cameraOpenBtn = printerPanel.querySelector("[data-printer-camera-open]");
  const webcam = printerPanel.querySelector("[data-printer-webcam]");
  const webcamUrl = printerPanel.dataset.webcamUrl;
  let cameraStageAnchor = null;
  let lastStatus = null;
  let fsOpen = false;
  let webcamReady = false;
  let statusTimer = null;
  let webcamTimer = null;
  let lastCameraTap = 0;

  function tempBarPct(current, target) {
    const t = parseFloat(target) || 0;
    const c = parseFloat(current) || 0;
    if (t <= 0) return Math.min(100, (c / 300) * 100);
    return Math.min(100, Math.max(0, (c / t) * 100));
  }

  function stateLabel(state) {
    if (state === "printing") return "Printing";
    if (state === "paused") return "Paused";
    if (state === "offline") return "Offline";
    if (state === "cancelled") return "Cancelled";
    return state ? state.charAt(0).toUpperCase() + state.slice(1) : "Standby";
  }

  function badgeClasses(state, online) {
    if (state === "printing") return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
    if (state === "paused") return "bg-amber-500/10 text-amber-400 border-amber-500/30";
    if (!online || state === "offline") return "bg-rose-500/10 text-rose-400 border-rose-500/30";
    return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
  }

  function setSyncLabel(text, isError) {
    const el = printerPanel.querySelector("[data-printer-sync]");
    if (!el) return;
    el.textContent = text;
    el.classList.toggle("text-rose-400", !!isError);
    el.classList.toggle("text-slate-600", !isError);
  }

  function syncTimeLabel() {
    const now = new Date();
    setSyncLabel(`Updated ${now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`, false);
  }

  // Show a timestamp immediately so the label never sticks on "Syncing…"
  syncTimeLabel();

  function setActionButtons(s) {
    document.querySelectorAll("[data-printer-action]").forEach((btn) => {
      const action = btn.dataset.printerAction;
      const enabled =
        (action === "pause" && s.can_pause) ||
        (action === "resume" && s.can_resume) ||
        (action === "cancel" && s.can_cancel);
      btn.toggleAttribute("disabled", !enabled);
    });
  }

  function updateStickyBar(s) {
    if (!stickyBar) return;
    const show = !fsOpen && (s.state === "printing" || s.state === "paused");
    stickyBar.hidden = !show;
    document.body.classList.toggle("printer-sticky-active", show);
  }

  function updateFullscreenHud(s) {
    if (!fsOpen || !cameraStage) return;
    cameraStage.querySelector("[data-printer-fs-pct]")?.textContent = `${s.progress}%`;
    cameraStage.querySelector("[data-printer-fs-layer]")?.textContent = `Layer ${s.layer_current}/${s.layer_total}`;
    cameraStage.querySelector("[data-printer-fs-eta]")?.textContent = `${s.time_remaining} left`;
  }

  function updateCameraOverlay(s) {
    const pct = printerPanel.querySelector("[data-printer-camera-overlay-pct]");
    if (!pct) return;
    if (s.state === "printing" || s.state === "paused") {
      pct.textContent = `${s.progress}%`;
      pct.classList.remove("hidden");
    } else {
      pct.classList.add("hidden");
    }
  }

  function applyPrinterStatus(s) {
    lastStatus = s;
    printerPanel.dataset.state = s.state || "standby";

    const hero = printerPanel.querySelector("[data-printer-hero]");
    if (hero) {
      hero.classList.toggle("printer-hero--printing", s.state === "printing");
      hero.classList.toggle("printer-hero--paused", s.state === "paused");
      hero.classList.remove("border-emerald-500/30", "border-amber-500/30", "border-edge");
      if (s.state === "printing") hero.classList.add("border-emerald-500/30");
      else if (s.state === "paused") hero.classList.add("border-amber-500/30");
      else hero.classList.add("border-edge");
    }

    const stateLabelEl = printerPanel.querySelector("[data-printer-state-label]");
    if (stateLabelEl) {
      stateLabelEl.textContent = stateLabel(s.state);
      stateLabelEl.className = `text-xs font-display font-bold uppercase tracking-widest ${
        s.state === "printing" ? "text-emerald-400"
        : s.state === "paused" ? "text-amber-400"
        : s.state === "offline" ? "text-rose-400"
        : "text-slate-400"
      }`;
    }

    const badge = printerPanel.querySelector("[data-printer-badge]");
    if (badge) {
      badge.textContent = s.state === "printing" ? "Printing" : s.state === "paused" ? "Paused" : s.online === false ? "Offline" : "Live";
      badge.className = `text-[10px] px-2.5 py-1 rounded-full font-display uppercase tracking-wide border ${badgeClasses(s.state, s.online !== false)}`;
    }

    printerPanel.querySelector("[data-printer-message]")?.textContent = s.status_message || "";
    printerPanel.querySelector("[data-printer-name]")?.textContent = s.print_name || "—";

    const bar = printerPanel.querySelector("[data-printer-bar]");
    if (bar) {
      bar.style.width = `${s.progress}%`;
      bar.classList.toggle("printer-bar-live", s.state === "printing");
    }

    printerPanel.querySelector("[data-printer-pct]")?.textContent = `${s.progress}%`;
    printerPanel.querySelector("[data-printer-eta]")?.textContent = s.time_remaining;
    printerPanel.querySelector("[data-printer-elapsed]")?.textContent = s.time_elapsed;
    printerPanel.querySelector("[data-printer-filament]")?.textContent = s.filament_used_m ?? "0";

    const layerEl = printerPanel.querySelector("[data-printer-layer]");
    if (layerEl) {
      layerEl.innerHTML = `${s.layer_current}<span class="text-slate-500 font-body text-xs">/${s.layer_total}</span>`;
    }

    const nozzle = printerPanel.querySelector("[data-printer-nozzle]");
    if (nozzle) {
      nozzle.innerHTML = `${s.nozzle_temp}<span class="text-xs text-slate-500 font-body"> / ${s.nozzle_target} °C</span>`;
    }
    const bed = printerPanel.querySelector("[data-printer-bed]");
    if (bed) {
      bed.innerHTML = `${s.bed_temp}<span class="text-xs text-slate-500 font-body"> / ${s.bed_target} °C</span>`;
    }
    printerPanel.querySelector("[data-printer-nozzle-bar]")?.style.setProperty("width", `${tempBarPct(s.nozzle_temp, s.nozzle_target)}%`);
    printerPanel.querySelector("[data-printer-bed-bar]")?.style.setProperty("width", `${tempBarPct(s.bed_temp, s.bed_target)}%`);

    const fan = printerPanel.querySelector("[data-printer-fan]");
    if (fan) fan.innerHTML = `${s.fan_speed_pct ?? "—"}<span class="text-xs text-slate-500 font-body"> %</span>`;
    const speed = printerPanel.querySelector("[data-printer-speed]");
    if (speed) speed.innerHTML = `${s.print_speed_pct}<span class="text-xs text-slate-500 font-body"> %</span>`;

    setActionButtons(s);
    updateStickyBar(s);
    updateCameraOverlay(s);
    updateFullscreenHud(s);
    syncTimeLabel();
  }

  async function refreshStatus() {
    try {
      const res = await fetch(statusUrl, { headers: { Accept: "application/json" }, credentials: "same-origin" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      try {
        applyPrinterStatus(data);
      } catch (applyErr) {
        console.error(applyErr);
        syncTimeLabel();
      }
    } catch (err) {
      console.error(err);
      setSyncLabel("Printer unreachable", true);
    }
  }

  function preloadWebcamInto(img, url) {
    if (!img) return;
    const loader = new Image();
    loader.onload = () => {
      img.src = loader.src;
      webcamReady = true;
      printerPanel.querySelector("[data-printer-camera-loading]")?.classList.add("is-hidden");
    };
    loader.onerror = () => {
      if (!webcamReady) {
        printerPanel.querySelector("[data-printer-camera-hint]")?.textContent = "Camera loading…";
      }
    };
    loader.src = `${url}?t=${Date.now()}`;
  }

  function refreshWebcam() {
    if (!webcamUrl) return;
    preloadWebcamInto(webcam, webcamUrl);
  }

  function openCameraFs(e) {
    e?.preventDefault();
    e?.stopPropagation();
    if (!cameraStage || fsOpen) return;

    fsOpen = true;
    if (!cameraStageAnchor) {
      cameraStageAnchor = document.createComment("printer-camera-stage");
      cameraStage.parentNode?.insertBefore(cameraStageAnchor, cameraStage);
    }
    document.body.appendChild(cameraStage);
    cameraStage.classList.add("is-fullscreen");
    const fsui = cameraStage.querySelector(".printer-camera-fsui");
    fsui?.removeAttribute("hidden");
    fsui?.setAttribute("aria-hidden", "false");
    document.body.classList.add("printer-camera-fs-open");
    if (lastStatus) {
      updateFullscreenHud(lastStatus);
      updateStickyBar(lastStatus);
    }
    if (webcamUrl) refreshWebcam();
    setWebcamInterval(3000);
  }

  function closeCameraFs(e) {
    e?.preventDefault();
    e?.stopPropagation();
    if (!cameraStage || !fsOpen) return;

    fsOpen = false;
    cameraStage.classList.remove("is-fullscreen");
    const fsui = cameraStage.querySelector(".printer-camera-fsui");
    fsui?.setAttribute("hidden", "");
    fsui?.setAttribute("aria-hidden", "true");
    document.body.classList.remove("printer-camera-fs-open");
    if (cameraStageAnchor?.parentNode) {
      cameraStageAnchor.parentNode.insertBefore(cameraStage, cameraStageAnchor.nextSibling);
    }
    if (lastStatus) updateStickyBar(lastStatus);
    setWebcamInterval(5000);
  }

  function handleCameraOpen(e) {
    if (Date.now() - lastCameraTap < 400) return;
    lastCameraTap = Date.now();
    openCameraFs(e);
  }

  if (cameraOpenBtn) {
    cameraOpenBtn.addEventListener("click", handleCameraOpen);
  }

  cameraStage?.querySelectorAll("[data-printer-camera-close]").forEach((el) => {
    el.addEventListener("click", closeCameraFs);
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && fsOpen) closeCameraFs(e);
  });
  function setWebcamInterval(ms) {
    if (!webcamUrl) return;
    clearInterval(webcamTimer);
    webcamTimer = setInterval(refreshWebcam, ms);
  }

  statusTimer = setInterval(() => refreshStatus(), 8000);
  refreshStatus();

  if (webcamUrl) {
    refreshWebcam();
    setWebcamInterval(5000);
  }

  const ptrRoot = document.getElementById("printer-ptr-root");
  if (ptrRoot && window.HomeOSMotion) {
    HomeOSMotion.initPullToRefresh(ptrRoot, async () => {
      await refreshStatus();
      refreshWebcam();
    });
  }

  async function runPrinterAction(btn, action) {
    if (action === "cancel" && !confirm("Cancel the current print job?")) return;
    btn.disabled = true;
    try {
      const url =
        action === "pause" ? printerPanel.dataset.pauseUrl
        : action === "resume" ? printerPanel.dataset.resumeUrl
        : `${printerPanel.dataset.cancelUrl}?confirm=1`;
      const s = await postJSON(url);
      applyPrinterStatus(s);
      window.HomeOSMotion?.hapticSetLog?.();
    } catch (err) {
      console.error(err);
      alert("Printer command failed — check Moonraker is reachable.");
    } finally {
      btn.disabled = false;
      if (lastStatus) setActionButtons(lastStatus);
    }
  }

  document.addEventListener("click", async (e) => {
    if (!e.target.closest("[data-printer-panel], [data-printer-sticky-bar], [data-printer-camera-stage]")) return;

    const preheatBtn = e.target.closest("[data-preheat]");
    if (preheatBtn && printerPanel.contains(preheatBtn)) {
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
    await runPrinterAction(btn, btn.dataset.printerAction);
  });
}

/** ── Dashboard printer widget live poll ───────────────── */
function initDashboardPrinter() {
  const widget = document.querySelector("[data-dashboard-printer]");
  if (!widget) return;
  const url = widget.dataset.statusUrl;
  if (!url) return;

  const apply = (s) => {
    widget.dataset.state = s.state || "standby";
    widget.querySelector("[data-dp-state]")?.textContent =
      s.state === "printing" ? "Printing" : s.state === "paused" ? "Paused" : s.online === false ? "Offline" : s.state || "Standby";
    widget.querySelector("[data-dp-name]")?.textContent = s.print_name || "—";
    widget.querySelector("[data-dp-pct]")?.textContent = `${s.progress}%`;
    widget.querySelector("[data-dp-eta]")?.textContent = s.time_remaining || "—";
    widget.querySelector("[data-dp-nozzle]")?.textContent = `${s.nozzle_temp}°`;
    widget.querySelector("[data-dp-bed]")?.textContent = `${s.bed_temp}°`;
    const bar = widget.querySelector("[data-dp-bar]");
    if (bar) {
      bar.style.width = `${s.progress}%`;
      bar.classList.toggle("printer-bar-live", s.state === "printing");
    }
    widget.classList.toggle("dashboard-hub--printing", s.state === "printing");
    widget.classList.toggle("dashboard-hub--paused", s.state === "paused");
  };

  const poll = () =>
    fetch(url, { headers: { Accept: "application/json" }, credentials: "same-origin" })
      .then((r) => r.json())
      .then(apply)
      .catch(() => {});

  poll();
  setInterval(poll, 12000);
}

/** ── Dashboard Pi health widget ───────────────────────── */
function initDashboardHealth() {
  const widget = document.querySelector("[data-dashboard-health]");
  if (!widget) return;
  const url = widget.dataset.healthUrl;
  if (!url) return;

  const apply = (h) => {
    widget.dataset.available = h.available ? "1" : "0";
    const tempEl = widget.querySelector("[data-dh-temp]");
    if (tempEl) {
      tempEl.textContent = h.cpu_temp_c != null ? `${h.cpu_temp_c}°C` : "—";
      tempEl.classList.toggle("text-rose-400", !!h.cpu_temp_warn);
      tempEl.classList.toggle("text-slate-200", !h.cpu_temp_warn);
    }
    widget.querySelector("[data-dh-mem]")?.textContent =
      h.memory?.used_pct != null ? `${h.memory.used_pct}%` : "—";
    widget.querySelector("[data-dh-disk]")?.textContent =
      h.disk?.used_pct != null ? `${h.disk.used_pct}%` : "—";
    widget.querySelector("[data-dh-docker]")?.textContent =
      h.docker?.total ? `${h.docker.running}/${h.docker.total} up` : "—";

    const barMem = widget.querySelector("[data-dh-mem-bar]");
    if (barMem && h.memory?.used_pct != null) barMem.style.width = `${h.memory.used_pct}%`;
    const barDisk = widget.querySelector("[data-dh-disk-bar]");
    if (barDisk && h.disk?.used_pct != null) barDisk.style.width = `${h.disk.used_pct}%`;

    const svcWrap = widget.querySelector("[data-dh-services]");
    if (svcWrap && h.docker?.services) {
      svcWrap.innerHTML = h.docker.services
        .map(
          (s) =>
            `<span class="dashboard-health-svc ${s.state === "running" ? "is-up" : "is-down"}">${s.name.replace("home-os-hub-", "")}</span>`
        )
        .join("");
    }
  };

  const poll = () =>
    fetch(url, { headers: { Accept: "application/json" }, credentials: "same-origin" })
      .then((r) => r.json())
      .then(apply)
      .catch(() => {});

  poll();
  setInterval(poll, 30000);
}

/** ── PWA install prompt ───────────────────────────────── */
function initPwaInstall() {
  const banner = document.getElementById("pwa-install-banner");
  if (!banner) return;

  const canonical = document.querySelector('meta[name="homeos-pwa-url"]')?.content?.trim();
  const isStandalone =
    window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;

  if (isStandalone) return;

  const dismissed = Number(localStorage.getItem("pwa-install-dismissed") || 0);
  if (Date.now() - dismissed < 7 * 86400000) return;

  const installBtn = banner.querySelector("[data-pwa-install]");
  const openBtn = banner.querySelector("[data-pwa-open-url]");
  const dismissBtn = banner.querySelector("[data-pwa-dismiss]");
  let deferredPrompt = null;
  let bannerShown = false;

  function setMode(mode) {
    bannerShown = true;
    banner.hidden = false;
    banner.dataset.mode = mode;
    banner.querySelectorAll("[data-pwa-title-install], [data-pwa-title-http], [data-pwa-title-manual]").forEach((el) => {
      el.classList.add("hidden");
    });
    banner.querySelectorAll("[data-pwa-hint-install], [data-pwa-hint-http], [data-pwa-hint-manual]").forEach((el) => {
      el.classList.add("hidden");
    });
    banner.querySelector(`[data-pwa-title-${mode}]`)?.classList.remove("hidden");
    banner.querySelector(`[data-pwa-hint-${mode}]`)?.classList.remove("hidden");
    installBtn?.classList.toggle("hidden", mode === "http");
    openBtn?.classList.toggle("hidden", mode !== "http");
  }

  if (!window.isSecureContext) {
    if (canonical) {
      openBtn?.setAttribute("href", canonical);
      setMode("http");
    }
    return;
  }

  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    setMode("install");
  });

  installBtn?.addEventListener("click", async () => {
    if (!deferredPrompt) {
      setMode("manual");
      return;
    }
    deferredPrompt.prompt();
    await deferredPrompt.userChoice.catch(() => {});
    deferredPrompt = null;
    banner.hidden = true;
  });

  dismissBtn?.addEventListener("click", () => {
    banner.hidden = true;
    localStorage.setItem("pwa-install-dismissed", String(Date.now()));
  });

  setTimeout(() => {
    if (!bannerShown) setMode("manual");
  }, 5000);
}

function bootHomeOS() {
  initPrinterPanel();
  initDashboardPrinter();
  initDashboardHealth();
  initPwaInstall();
  lockPortraitInStandalone();
}

/** Lock PWA to portrait (respects installed-app orientation). */
function lockPortraitInStandalone() {
  const standalone =
    window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
  if (!standalone || !screen.orientation?.lock) return;
  screen.orientation.lock("portrait-primary").catch(() => {});
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootHomeOS);
} else {
  bootHomeOS();
}
