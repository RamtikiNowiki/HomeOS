/** Theme — single source of truth for light/dark (PWA-safe). */
window.HomeOSTheme = (() => {
  function apply(mode) {
    const root = document.documentElement;
    const dark = mode === "dark";
    root.classList.toggle("dark", dark);
    root.dataset.theme = mode;
    root.style.colorScheme = mode;
    try {
      localStorage.setItem("theme", mode);
    } catch (_) {}
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.setAttribute(
        "content",
        dark ? root.dataset.themeDark || "#0b0d16" : root.dataset.themeLight || "#f4f6fb"
      );
    }
  }

  function toggle() {
    const current = document.documentElement.dataset.theme;
    apply(current === "dark" ? "light" : "dark");
  }

  function bindToggleButtons() {
    document.querySelectorAll("[data-action='toggle-theme']").forEach((btn) => {
      if (btn.dataset.themeBound) return;
      btn.dataset.themeBound = "1";
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        toggle();
      });
    });
  }

  function init(defaultTheme) {
    let stored = null;
    try {
      stored = localStorage.getItem("theme");
    } catch (_) {}
    apply(stored === "light" || stored === "dark" ? stored : defaultTheme || "dark");
    bindToggleButtons();
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", bindToggleButtons);
    }
  }

  return { apply, init, toggle, bindToggleButtons };
})();
