/* ========================================================
   Home OS — motion, haptics, sounds, view transitions
   ======================================================== */

const HomeOSMotion = (() => {
  const SOUND_KEY = "fitness-sound-enabled";
  const SEASONAL_KEY = "homeos-seasonal-bg";

  function accent() {
    return document.documentElement.dataset.accent || "indigo";
  }

  function isPink() {
    return accent() === "pink";
  }

  function soundsEnabled() {
    return localStorage.getItem(SOUND_KEY) === "1";
  }

  function seasonalEnabled() {
    const stored = localStorage.getItem(SEASONAL_KEY);
    if (stored === "0") return false;
    if (stored === "1") return true;
    return true;
  }

  /** ── Haptics ───────────────────────────────────────── */
  function vibrate(pattern) {
    if (navigator.vibrate) navigator.vibrate(pattern);
  }

  function hapticSetLog() {
    vibrate(18);
  }

  function hapticRestDone() {
    vibrate([180, 80, 220]);
  }

  function hapticPr() {
    vibrate([70, 40, 110, 40, 160]);
  }

  /** ── Accent-aware sounds (off by default) ──────────── */
  let audioCtx = null;
  function getAudio() {
    if (!audioCtx) {
      try {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      } catch (_) {
        return null;
      }
    }
    return audioCtx;
  }

  function tone(freqs, duration, type = "sine", gainVal = 0.07) {
    if (!soundsEnabled()) return;
    const ctx = getAudio();
    if (!ctx) return;
    if (ctx.state === "suspended") ctx.resume().catch(() => {});
    const t0 = ctx.currentTime;
    freqs.forEach((f, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = type;
      osc.frequency.value = f;
      gain.gain.setValueAtTime(gainVal, t0 + i * 0.08);
      gain.gain.exponentialRampToValueAtTime(0.001, t0 + duration);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(t0 + i * 0.08);
      osc.stop(t0 + duration);
    });
  }

  function playRestSound() {
    if (isPink()) tone([523, 659, 784], 0.55, "sine", 0.06);
    else tone([880, 1100], 0.12, "square", 0.04);
  }

  function playPrSound() {
    if (isPink()) tone([659, 784, 988, 1175], 0.7, "sine", 0.07);
    else tone([440, 660, 880], 0.35, "square", 0.05);
  }

  /** ── Particle burst (hearts / hex) ─────────────────── */
  function ensureParticleLayer() {
    let layer = document.getElementById("particle-layer");
    if (!layer) {
      layer = document.createElement("div");
      layer.id = "particle-layer";
      layer.className = "particle-layer";
      layer.setAttribute("aria-hidden", "true");
      document.body.appendChild(layer);
    }
    return layer;
  }

  function burstParticles(originEl) {
    const layer = ensureParticleLayer();
    const rect = originEl?.getBoundingClientRect();
    const cx = rect ? rect.left + rect.width / 2 : window.innerWidth / 2;
    const cy = rect ? rect.top + rect.height / 3 : window.innerHeight * 0.35;
    const pink = isPink();
    const count = pink ? 28 : 22;

    for (let i = 0; i < count; i++) {
      const p = document.createElement("span");
      p.className = `burst-particle ${pink ? "burst-particle--heart" : "burst-particle--hex"}`;
      p.textContent = pink ? "♥" : "⬡";
      const angle = (Math.PI * 2 * i) / count + Math.random() * 0.4;
      const dist = 60 + Math.random() * 120;
      const dx = Math.cos(angle) * dist;
      const dy = Math.sin(angle) * dist - 40;
      p.style.left = `${cx}px`;
      p.style.top = `${cy}px`;
      p.style.setProperty("--dx", `${dx}px`);
      p.style.setProperty("--dy", `${dy}px`);
      p.style.setProperty("--rot", `${Math.random() * 360}deg`);
      p.style.animationDelay = `${Math.random() * 0.12}s`;
      layer.appendChild(p);
      p.addEventListener("animationend", () => p.remove(), { once: true });
    }
  }

  /** ── View Transitions (Train → Log → Session) ──────── */
  function initViewTransitions() {
    if (!document.startViewTransition) return;

    document.addEventListener("click", (e) => {
      const a = e.target.closest("a[href]");
      if (!a || a.target === "_blank" || e.metaKey || e.ctrlKey || e.shiftKey) return;
      if (a.hasAttribute("download") || a.getAttribute("href")?.startsWith("#")) return;

      let url;
      try {
        url = new URL(a.href, location.href);
      } catch (_) {
        return;
      }
      if (url.origin !== location.origin) return;

      const path = url.pathname;
      const isFitnessNav =
        path === "/fitness/" ||
        path === "/fitness" ||
        /^\/fitness\/session\/\d+/.test(path) ||
        /^\/fitness\/session\/\d+\/exercise\/\d+/.test(path);

      if (!isFitnessNav) return;
      e.preventDefault();
      document.startViewTransition(() => {
        window.location.href = a.href;
      });
    });
  }

  /** ── Tab bar icon bounce ───────────────────────────── */
  function initNavBounce() {
    document.querySelectorAll(".nav-pill-item").forEach((item) => {
      item.addEventListener("click", () => {
        const icon = item.querySelector("svg");
        if (!icon) return;
        icon.classList.remove("nav-icon-bounce");
        void icon.offsetWidth;
        icon.classList.add("nav-icon-bounce");
        icon.addEventListener("animationend", () => icon.classList.remove("nav-icon-bounce"), { once: true });
      });
    });
  }

  /** ── Pull-to-refresh (Train exercise list) ─────────── */
  function initPullToRefresh(container, onRefresh) {
    if (!container || window.innerWidth >= 1024) return;

    let startY = 0;
    let pulling = false;
    let dist = 0;
    const threshold = 72;
    const indicator = document.createElement("div");
    indicator.className = "ptr-indicator";
    indicator.innerHTML = '<span class="ptr-spinner"></span><span class="ptr-label">Pull to refresh</span>';
    container.prepend(indicator);

    container.addEventListener(
      "touchstart",
      (e) => {
        if (window.scrollY > 8) return;
        startY = e.touches[0].clientY;
        pulling = true;
        dist = 0;
      },
      { passive: true }
    );

    container.addEventListener(
      "touchmove",
      (e) => {
        if (!pulling) return;
        dist = Math.max(0, e.touches[0].clientY - startY);
        if (dist > 0 && window.scrollY <= 8) {
          const eased = Math.min(dist * 0.45, threshold * 1.4);
          indicator.style.transform = `translateY(${eased}px)`;
          indicator.classList.toggle("ptr-indicator--ready", eased >= threshold);
        }
      },
      { passive: true }
    );

    const endPull = async () => {
      if (!pulling) return;
      pulling = false;
      const ready = dist >= threshold;
      indicator.style.transform = "";
      indicator.classList.remove("ptr-indicator--ready");
      dist = 0;
      if (ready) {
        indicator.classList.add("ptr-indicator--loading");
        try {
          await onRefresh();
        } finally {
          indicator.classList.remove("ptr-indicator--loading");
        }
      }
    };

    container.addEventListener("touchend", endPull);
    container.addEventListener("touchcancel", endPull);
  }

  /** ── Skeleton chart reveal ─────────────────────────── */
  function revealChartWrap(wrap) {
    if (!wrap) return;
    wrap.classList.remove("is-loading");
    const canvas = wrap.querySelector("canvas");
    if (canvas) canvas.classList.remove("opacity-0");
  }

  function initChartSkeletons() {
    document.querySelectorAll("[data-skeleton-chart]").forEach((wrap) => {
      wrap.classList.add("is-loading");
    });
  }

  /** ── Seasonal background (Aylin light — blossoms / snow) ─ */
  function initSeasonal() {
    const layer = document.getElementById("seasonal-layer");
    if (!layer || !seasonalEnabled()) return;
    if (!isPink() || document.documentElement.classList.contains("dark")) return;

    const month = new Date().getMonth();
    const kind = month >= 2 && month <= 4 ? "blossom" : month >= 11 || month <= 1 ? "snow" : "blossom";
    layer.dataset.season = kind;
    layer.hidden = false;

    for (let i = 0; i < 18; i++) {
      const flake = document.createElement("span");
      flake.className = `seasonal-bit seasonal-bit--${kind}`;
      flake.style.left = `${Math.random() * 100}%`;
      flake.style.animationDuration = `${8 + Math.random() * 12}s`;
      flake.style.animationDelay = `${Math.random() * 10}s`;
      flake.style.setProperty("--drift", `${-20 + Math.random() * 40}px`);
      layer.appendChild(flake);
    }
  }

  /** ── Widget live indicators ────────────────────────── */
  function initPrinterPulse() {
    const panel = document.querySelector("[data-printer-panel]");
    if (!panel) return;
    const bar = panel.querySelector("[data-printer-bar]");
    const refresh = () => {
      const printing = panel.querySelector(".text-emerald-400")?.textContent?.includes("Printing");
      bar?.classList.toggle("printer-bar-live", !!printing);
    };
    refresh();
    setInterval(refresh, 16000);
  }

  function syncLightGlow() {
    document.querySelectorAll("[data-light-card]").forEach((card) => {
      card.classList.toggle("light-card-live", card.dataset.state === "on");
    });
  }

  return {
    accent,
    isPink,
    soundsEnabled,
    hapticSetLog,
    hapticRestDone,
    hapticPr,
    playRestSound,
    playPrSound,
    burstParticles,
    initViewTransitions,
    initNavBounce,
    initPullToRefresh,
    revealChartWrap,
    initChartSkeletons,
    initSeasonal,
    initPrinterPulse,
    syncLightGlow,
  };
})();

document.addEventListener("DOMContentLoaded", () => {
  HomeOSMotion.initViewTransitions();
  HomeOSMotion.initNavBounce();
  HomeOSMotion.initChartSkeletons();
  HomeOSMotion.initSeasonal();
  HomeOSMotion.initPrinterPulse();
  HomeOSMotion.syncLightGlow();

  const ptrRoot = document.getElementById("train-ptr-root");
  if (ptrRoot) {
    HomeOSMotion.initPullToRefresh(ptrRoot, () => {
      window.location.reload();
    });
  }
});

window.HomeOSMotion = HomeOSMotion;
