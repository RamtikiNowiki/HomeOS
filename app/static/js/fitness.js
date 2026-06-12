/* ---- Fitness Hub — in-gym UX helpers ---- */

/** Exercise list search/filter with optional muscle-group chips + beginner mode */
function initExercisePicker({ searchId, listSelector, rowSelector, chipsSelector, groupSelectId, defaultGroup, beginnerToggleId }) {
  const input = document.getElementById(searchId);
  const list = document.querySelector(listSelector);
  if (!list) return;

  let activeGroup = defaultGroup || "";
  const supportsBeginner = Boolean(
    beginnerToggleId || list.querySelector(`${rowSelector}[data-beginner]`)
  );
  let beginnerOnly = supportsBeginner && localStorage.getItem("fitness-beginner-mode") === "1";

  const beginnerToggle = beginnerToggleId ? document.getElementById(beginnerToggleId) : null;
  const syncBeginnerToggle = () => {
    if (!beginnerToggle) return;
    beginnerToggle.classList.toggle("border-neon/40", beginnerOnly);
    beginnerToggle.classList.toggle("bg-neon/10", beginnerOnly);
    beginnerToggle.classList.toggle("text-neon", beginnerOnly);
    beginnerToggle.setAttribute("aria-pressed", beginnerOnly ? "true" : "false");
  };
  syncBeginnerToggle();
  beginnerToggle?.addEventListener("click", () => {
    beginnerOnly = !beginnerOnly;
    localStorage.setItem("fitness-beginner-mode", beginnerOnly ? "1" : "0");
    syncBeginnerToggle();
    filter();
  });

  const setChipStyles = () => {
    if (!chipsSelector) return;
    document.querySelectorAll(chipsSelector).forEach((chip) => {
      const on = (chip.dataset.group || "") === activeGroup;
      chip.classList.toggle("border-neon/40", on);
      chip.classList.toggle("bg-neon/10", on);
      chip.classList.toggle("text-neon", on);
      chip.classList.toggle("border-edge", !on);
      chip.classList.toggle("bg-raised", !on);
      chip.classList.toggle("text-slate-400", !on);
    });
  };

  const filter = () => {
    const q = (input?.value || "").trim().toLowerCase();
    let visible = 0;
    list.querySelectorAll(rowSelector).forEach((row) => {
      const name = (row.dataset.name || "").toLowerCase();
      const searchText = (row.dataset.searchText || name).toLowerCase();
      const group = (row.dataset.group || "").toLowerCase();
      const matchSearch = !q || searchText.includes(q) || name.includes(q) || group.includes(q);
      const matchGroup = !activeGroup || row.dataset.group === activeGroup;
      const matchBeginner = !beginnerOnly || row.dataset.beginner === "1";
      const show = matchSearch && matchGroup && matchBeginner;
      row.classList.toggle("hidden", !show);
      if (show) visible += 1;
    });
    const empty = list.querySelector("[data-search-empty]");
    if (empty) {
      const filtered = visible === 0 && list.querySelectorAll(rowSelector).length > 0;
      empty.classList.toggle("hidden", !filtered);
      if (filtered && beginnerOnly) {
        empty.textContent = "No machine-friendly exercises match — try All groups or turn off Machines only.";
      } else if (filtered && activeGroup) {
        empty.textContent = `No ${activeGroup} exercises in your library — tap All or import from Catalog.`;
      } else if (filtered) {
        empty.textContent = "No exercises match your search.";
      }
    }
  };

  input?.addEventListener("input", filter);

  if (chipsSelector) {
    document.querySelectorAll(chipsSelector).forEach((chip) => {
      chip.addEventListener("click", () => {
        const group = chip.dataset.group || "";
        activeGroup = activeGroup === group ? "" : group;
        setChipStyles();
        filter();
      });
    });
    setChipStyles();
  }

  const groupSelect = groupSelectId ? document.getElementById(groupSelectId) : null;
  groupSelect?.addEventListener("change", () => {
    activeGroup = groupSelect.value || "";
    filter();
  });

  filter();
  return filter;
}

/** @deprecated — use initExercisePicker for richer filtering */
function initExerciseSearch(inputId, listSelector, rowSelector) {
  return initExercisePicker({ searchId: inputId, listSelector, rowSelector });
}

/** Hide built-in split cards the user doesn't use */
function initHiddenSplits(storageKey) {
  const grid = document.getElementById("split-grid");
  if (!grid) return;

  const key = storageKey || "fitness-hidden-splits";
  let hidden = [];
  try {
    hidden = JSON.parse(localStorage.getItem(key) || "[]");
  } catch (_) {
    hidden = [];
  }

  const apply = () => {
    grid.querySelectorAll("[data-split-id]").forEach((card) => {
      const id = card.dataset.splitId;
      card.classList.toggle("hidden", hidden.includes(id));
    });
    const customize = document.getElementById("split-customize-panel");
    if (customize) {
      customize.querySelectorAll("[data-split-toggle]").forEach((cb) => {
        cb.checked = !hidden.includes(cb.value);
      });
    }
  };

  apply();

  document.getElementById("split-customize-toggle")?.addEventListener("click", () => {
    document.getElementById("split-customize-panel")?.classList.toggle("hidden");
  });

  document.getElementById("split-customize-save")?.addEventListener("click", () => {
    const panel = document.getElementById("split-customize-panel");
    hidden = [];
    panel?.querySelectorAll("[data-split-toggle]").forEach((cb) => {
      if (!cb.checked) hidden.push(cb.value);
    });
    localStorage.setItem(key, JSON.stringify(hidden));
    apply();
    panel?.classList.add("hidden");
  });
}

/** Numeric steppers for weight/reps inputs */
function initSteppers(root) {
  (root || document).querySelectorAll("[data-stepper]").forEach((wrap) => {
    const input = wrap.querySelector("input");
    const dec = wrap.querySelector("[data-step-dec]");
    const inc = wrap.querySelector("[data-step-inc]");
    if (!input) return;

    const step = parseFloat(wrap.dataset.step || input.step || "1");
    const min = input.min !== "" ? parseFloat(input.min) : null;
    const max = input.max !== "" ? parseFloat(input.max) : null;

    const bump = (delta) => {
      let val = parseFloat(input.value) || 0;
      val = Math.round((val + delta) / step) * step;
      if (min !== null) val = Math.max(min, val);
      if (max !== null) val = Math.min(max, val);
      input.value = Number.isInteger(step) ? Math.round(val) : val.toFixed(1).replace(/\.0$/, "");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    };

    dec?.addEventListener("click", () => bump(-step));
    inc?.addEventListener("click", () => bump(step));
  });
}

/** RPE chip selector */
function initRpeChips(container, input) {
  if (!container || !input) return;
  container.querySelectorAll("[data-rpe]").forEach((chip) => {
    chip.addEventListener("click", () => {
      const val = chip.dataset.rpe;
      if (val === "clear") {
        input.value = "";
      } else {
        input.value = val;
      }
      container.querySelectorAll("[data-rpe]").forEach((c) => {
        c.classList.toggle("ring-2", c.dataset.rpe === val && val !== "clear");
        c.classList.toggle("ring-neon/60", c.dataset.rpe === val && val !== "clear");
      });
    });
  });
}

/** Warm-up segmented toggle */
function initWarmupToggle(wrap) {
  if (!wrap) return;
  const hidden = wrap.querySelector('input[type="hidden"]');

  const applyWarmupState = (isWarmup) => {
    hidden.value = isWarmup ? "1" : "0";
    wrap.querySelectorAll("[data-warmup]").forEach((b) => {
      const on = b.dataset.warmup === (isWarmup ? "1" : "0");
      b.classList.toggle("bg-neon/15", on);
      b.classList.toggle("border-neon/40", on);
      b.classList.toggle("text-neon", on);
      b.classList.toggle("text-slate-500", !on); /* ensure off-state colour is visible */
      b.classList.toggle("font-semibold", on);
    });
  };

  wrap.querySelectorAll("[data-warmup]").forEach((btn) => {
    btn.addEventListener("click", () => applyWarmupState(btn.dataset.warmup === "1"));
  });
}

/** Rest timer with remembered duration, optional next-exercise hint + sound */
function createRestTimer(opts) {
  const panel = document.getElementById(opts.panelId || "rest-timer");
  const display = document.getElementById(opts.displayId || "rest-display");
  const bar = document.getElementById(opts.barId || "rest-bar");
  const ring = document.getElementById(opts.ringId || "rest-ring-progress");
  const nextHint = document.getElementById(opts.nextHintId || "rest-next-exercise");
  const storageKey = opts.storageKey || "fitness-rest-seconds";
  const soundKey = "fitness-rest-sound";
  let interval = null;
  let seconds = 0;
  let total = 90;
  const ringLen = ring ? parseFloat(ring.getAttribute("stroke-dasharray") || "326.7") : 326.7;

  const updateRing = (sec, tot) => {
    if (!ring || !tot) return;
    ring.style.strokeDashoffset = String(ringLen * (1 - sec / tot));
  };

  const playDoneSound = () => {
    if (localStorage.getItem(soundKey) !== "1") return;
    if (window.HomeOSMotion) HomeOSMotion.playRestSound();
  };

  const format = (s) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return m > 0 ? `${m}:${sec.toString().padStart(2, "0")}` : `${s}s`;
  };

  const start = (sec) => {
    total = sec;
    seconds = sec;
    localStorage.setItem(storageKey, String(sec));
    if (panel) panel.hidden = false;
    if (display) {
      display.textContent = format(seconds);
      display.classList.remove("text-emerald-400");
    }
    if (bar) bar.style.width = "100%";
    updateRing(seconds, total);
    clearInterval(interval);
    interval = setInterval(() => {
      seconds -= 1;
      if (display) display.textContent = format(Math.max(0, seconds));
      if (bar) bar.style.width = `${(seconds / total) * 100}%`;
      updateRing(Math.max(0, seconds), total);
      if (seconds <= 0) {
        clearInterval(interval);
        if (display) {
          display.textContent = "Go!";
          display.classList.add("text-emerald-400");
        }
        if (window.HomeOSMotion) HomeOSMotion.hapticRestDone();
        else if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
        playDoneSound();
      }
    }, 1000);
  };

  document.querySelectorAll(".rest-preset").forEach((btn) => {
    btn.addEventListener("click", () => start(parseInt(btn.dataset.rest, 10)));
  });

  document.getElementById("rest-dismiss")?.addEventListener("click", () => {
    if (panel) panel.hidden = true;
    clearInterval(interval);
    if (display) display.classList.remove("text-emerald-400");
  });

  document.getElementById("rest-add-30")?.addEventListener("click", () => {
    seconds += 30;
    total += 30;
    if (display) display.textContent = format(seconds);
    updateRing(seconds, total);
  });

  const soundBtn = document.getElementById("rest-sound-toggle");
  if (soundBtn) {
    const syncSoundToggle = () => {
      const on = localStorage.getItem(soundKey) === "1";
      soundBtn.setAttribute("aria-pressed", on ? "true" : "false");
      soundBtn.textContent = on ? "🔔" : "🔕";
    };
    syncSoundToggle();
    soundBtn.addEventListener("click", () => {
      const on = localStorage.getItem(soundKey) === "1";
      localStorage.setItem(soundKey, on ? "0" : "1");
      syncSoundToggle();
    });
  }

  const defaultSec = parseInt(localStorage.getItem(storageKey) || "90", 10);
  return { start, defaultSeconds: defaultSec, setNextExercise(name, url, iconUrl) {
    if (!nextHint) return;
    if (!name) { nextHint.hidden = true; return; }
    nextHint.hidden = false;
    const label = nextHint.querySelector("[data-rest-next-label]");
    const link = nextHint.querySelector("[data-rest-next-link]");
    const img = nextHint.querySelector("[data-rest-next-icon]");
    if (label) label.textContent = name;
    if (link && url) link.href = url;
    if (img && iconUrl) img.src = iconUrl;
  }};
}

/** Build a set row DOM node from JSON */
function buildSetRow(data, weightFormat) {
  const fmt = weightFormat || ((n) => n);
  const tpl = document.getElementById("set-row-template");
  if (!tpl) return null;
  const row = tpl.content.cloneNode(true).querySelector("[data-set-row]");
  row.dataset.setId = String(data.id);
  row.dataset.completed = data.completed ? "1" : "0";
  if (data.is_warmup) row.classList.add("set-warmup");

  const num = row.querySelector("[data-set-num]");
  num.textContent = data.is_warmup ? "W" : data.set_number;

  const summary = row.querySelector("[data-set-summary]");
  summary.innerHTML = `${fmt(data.weight)} <span class="text-slate-500 text-sm">lb</span>
    <span class="text-slate-600 mx-1">×</span>
    ${data.reps} <span class="text-slate-500 text-sm">reps</span>
    ${data.is_warmup ? '<span class="ml-2 text-[10px] uppercase text-amber-600 dark:text-amber-400">warm-up</span>' : ""}
    ${data.rpe ? `<span class="text-slate-600 mx-1">·</span><span class="text-xs text-pulse">RPE ${fmt(data.rpe)}</span>` : ""}`;

  const toggle = row.querySelector("[data-set-toggle]");
  toggle.dataset.url = data.toggle_url;
  toggle.dataset.completed = data.completed ? "1" : "0";

  const editBtn = row.querySelector("[data-edit-toggle]");
  editBtn.dataset.editToggle = String(data.id);

  const editForm = row.querySelector("[data-edit-form]");
  editForm.id = `edit-set-${data.id}`;
  editForm.action = data.edit_url;
  editForm.querySelector('[name="weight"]').value = data.weight;
  editForm.querySelector('[name="reps"]').value = data.reps;
  editForm.querySelector('[name="rpe"]').value = data.rpe || "";
  editForm.querySelector('[name="is_warmup"]').checked = data.is_warmup;

  const delForm = row.querySelector("[data-delete-form]");
  delForm.action = data.delete_url;

  row.classList.add("set-row-enter");
  row.addEventListener("animationend", () => row.classList.remove("set-row-enter"), { once: true });

  return row;
}

/** ══════════════════════════════════════════════════════════
 *  Collapsible Log Sheet — swipe-down to minimise, shows
 *  workout-plan quick-pick tray in the collapsed strip.
 *  ══════════════════════════════════════════════════════════ */
function initLogSheet() {
  const sheet = document.getElementById("log-sheet");
  const dragZone = document.getElementById("sheet-drag-zone");
  const body = document.getElementById("sheet-body");
  const expandBtn = document.getElementById("sheet-expand-btn");
  const tray = document.getElementById("sheet-exercise-tray");
  const miniLabel = document.getElementById("sheet-mini-label");
  const spacer = document.getElementById("log-sheet-spacer");

  if (!sheet || !body) return null;

  let exercises = [];
  try {
    const dataEl = document.getElementById("sheet-exercises-data");
    if (dataEl) exercises = JSON.parse(dataEl.textContent || "[]");
  } catch (_) {}

  let collapsed = false;
  let autoExpandTimer = null;
  let dragging = false;
  let dragStartY = 0;
  let dragStartTranslate = 0;

  function buildTray(scrollToEnd = false) {
    if (!tray) return;
    tray.innerHTML = "";
    if (!exercises.length) {
      const hint = document.createElement("span");
      hint.className = "text-[10px] text-slate-500 px-2 py-1 whitespace-nowrap";
      hint.textContent = "Add exercises in Switch panel ↑";
      tray.appendChild(hint);
      return;
    }
    exercises.forEach((ex) => {
      const chip = document.createElement(ex.current ? "span" : "a");
      if (!ex.current) chip.href = ex.url;
      chip.className = "sheet-tray-chip";
      if (ex.priority) chip.classList.add("is-priority");
      if (ex.current) chip.classList.add("is-current");
      if (ex.done) chip.classList.add("is-done");
      chip.title = ex.display_name || ex.name;
      if (ex.icon) {
        const img = document.createElement("img");
        img.src = `/static/${ex.icon}`;
        img.alt = "";
        img.width = 24;
        img.height = 24;
        img.className = "pixel-icon shrink-0";
        img.loading = "lazy";
        chip.appendChild(img);
      }
      const label = document.createElement("span");
      label.textContent = ex.display_name || ex.name;
      chip.appendChild(label);
      tray.appendChild(chip);
    });
    if (scrollToEnd) {
      requestAnimationFrame(() => {
        tray.scrollTo({ left: tray.scrollWidth, behavior: "smooth" });
      });
    }
  }

  function setPlanExercises(plan, { scrollToEnd = false } = {}) {
    exercises = plan || [];
    buildTray(scrollToEnd);
  }

  function navPad() {
    if (window.innerWidth >= 1024) return 0;
    return parseFloat(getComputedStyle(sheet).paddingBottom) || 0;
  }

  function visibleHeight() {
    const handleH = sheet.querySelector(".sheet-handle")?.offsetHeight || 0;
    const bodyH = collapsed ? 0 : body.offsetHeight;
    return handleH + bodyH + navPad();
  }

  function updateSpacer() {
    if (!spacer) return;
    const extra = window.innerWidth >= 1024 ? 12 : 8;
    spacer.style.height = `${visibleHeight() + extra}px`;
  }

  function getSlideAmount() {
    return body.offsetHeight;
  }

  function collapse({ auto = false } = {}) {
    collapsed = true;
    clearTimeout(autoExpandTimer);
    sheet.classList.add("is-collapsed");
    sheet.style.transform = `translateY(${getSlideAmount()}px)`;
    updateSpacer();
    if (auto) autoExpandTimer = setTimeout(() => expand(), 10000);
  }

  function expand() {
    collapsed = false;
    clearTimeout(autoExpandTimer);
    sheet.classList.remove("is-collapsed");
    sheet.style.transform = "translateY(0)";
    updateSpacer();
  }

  buildTray();
  requestAnimationFrame(updateSpacer);

  expandBtn?.addEventListener("click", (e) => {
    e.stopPropagation();
    expand();
  });

  dragZone?.addEventListener("pointerdown", (e) => {
    dragging = true;
    dragStartY = e.clientY;
    const mat = new DOMMatrix(getComputedStyle(sheet).transform);
    dragStartTranslate = isNaN(mat.m42) ? 0 : mat.m42;
    sheet.style.transition = "none";
    dragZone.setPointerCapture(e.pointerId);
  });

  dragZone?.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    const dy = e.clientY - dragStartY;
    const max = getSlideAmount();
    const next = Math.max(0, Math.min(max, dragStartTranslate + dy));
    sheet.style.transform = `translateY(${next}px)`;
  });

  const snapAfterDrag = () => {
    if (!dragging) return;
    dragging = false;
    sheet.style.transition = "";
    const mat = new DOMMatrix(getComputedStyle(sheet).transform);
    const cur = isNaN(mat.m42) ? 0 : mat.m42;
    if (cur > getSlideAmount() * 0.35) collapse();
    else expand();
  };

  dragZone?.addEventListener("pointerup", snapAfterDrag);
  dragZone?.addEventListener("pointercancel", () => {
    dragging = false;
    sheet.style.transition = "";
    expand();
  });

  dragZone?.addEventListener("click", () => {
    if (dragging) return;
    collapsed ? expand() : collapse();
  });

  new ResizeObserver(updateSpacer).observe(body);
  new ResizeObserver(updateSpacer).observe(sheet.querySelector(".sheet-handle") || body);
  window.addEventListener("resize", updateSpacer);

  const api = {
    collapse,
    expand,
    setPlanExercises,
    afterSetLogged(setCount) {
      if (miniLabel) miniLabel.textContent = `Set ${setCount + 1}`;
      const submitBtn = document.querySelector("#log-set-form [type=submit]");
      if (submitBtn) submitBtn.textContent = `Log Set ${setCount + 1}`;
      collapse({ auto: true });
    },
  };
  window.logSheetApi = api;
  return api;
}

/** AJAX add/remove for workout plan on the log page — updates tray live */
function initPlanAjax(sheetApi) {
  const switchPanel = document.getElementById("workout-switch");
  if (!switchPanel || !sheetApi) return;

  switchPanel.querySelectorAll("form.plan-ajax-form").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const msg = form.dataset.confirm;
      if (msg && !confirm(msg)) return;

      const btn = form.querySelector("[type=submit]");
      if (btn) btn.disabled = true;

      try {
        const res = await fetch(form.action, {
          method: "POST",
          body: new FormData(form),
          headers: { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" },
        });
        const data = await res.json();
        if (!res.ok || !data.ok) throw new Error("Failed");

        const isAdd = form.action.includes("/plan/add/");
        sheetApi.setPlanExercises(data.plan, { scrollToEnd: isAdd });

        if (isAdd && data.exercise) {
          const row = form.closest(".exercise-switch-row");
          row?.classList.add("border-neon/30", "bg-neon/5");
          const added = data.plan.find((p) => p.id === data.exercise.id);
          const logUrl = added?.url || "#";
          form.outerHTML = `<a href="${logUrl}" class="shrink-0 text-[10px] font-display uppercase text-neon px-2 py-1">Log →</a>`;
        } else if (!isAdd) {
          form.closest(".switch-plan-row")?.remove();
        }
      } catch (err) {
        form.submit();
      } finally {
        if (btn) btn.disabled = false;
      }
    });
  });
}

function showPrCelebration(pr) {
  const el = document.getElementById("pr-celebration");
  if (!el || !pr) return;
  const msg = el.querySelector("[data-pr-msg]");
  if (msg) {
    msg.textContent = `New PR — ${pr.weight} lb × ${pr.reps} (est. ${pr.estimated_1rm} lb 1RM)`;
  }
  el.classList.remove("hidden");
  el.classList.add("pr-pop");
  if (window.HomeOSMotion) {
    HomeOSMotion.burstParticles(el);
    HomeOSMotion.hapticPr();
    HomeOSMotion.playPrSound();
  } else if (navigator.vibrate) {
    navigator.vibrate([80, 40, 120]);
  }
  setTimeout(() => {
    el.classList.add("hidden");
    el.classList.remove("pr-pop");
  }, 3200);
}

/** AJAX set logging on exercise page */
function initAjaxSetLogging(formId, sheetApi) {
  const form = document.getElementById(formId || "log-set-form");
  if (!form) return;

  const weightInput = form.querySelector("#weight");
  const repsInput = form.querySelector("#reps");
  const rpeInput = form.querySelector("#rpe");
  const warmupInput = form.querySelector('[name="is_warmup"]');
  const setsList = document.getElementById("sets-list");
  const setsEmpty = document.getElementById("sets-empty");
  const setLabel = document.getElementById("log-set-label");
  const plateHint = document.getElementById("plate-hint");
  const logBtn = form.querySelector("[type=submit]");
  const sameBtn = document.getElementById("log-same-btn");
  const rest = createRestTimer({});
  const nextDataEl = document.getElementById("next-exercise-data");
  if (nextDataEl) {
    try {
      const nx = JSON.parse(nextDataEl.textContent || "null");
      if (nx) rest.setNextExercise(nx.name, nx.url, nx.icon ? `/static/${nx.icon}` : null);
    } catch (_) {}
  }

  initSteppers(form);
  initRpeChips(document.getElementById("rpe-chips"), rpeInput);
  initWarmupToggle(document.getElementById("warmup-toggle"));

  const updatePlateHint = async () => {
    if (!plateHint || !weightInput) return;
    const w = parseFloat(weightInput.value);
    if (!w || w <= 0) {
      plateHint.textContent = "";
      return;
    }
    // Client-side plate calc (mirrors server)
    const bar = 45;
    let perSide = Math.round(((w - bar) / 2) / 2.5) * 2.5;
    if (perSide < 0) perSide = 0;
    const plates = [45, 35, 25, 10, 5, 2.5];
    const side = [];
    let rem = perSide;
    for (const p of plates) {
      while (rem >= p - 0.001) {
        side.push(p);
        rem = Math.round((rem - p) * 100) / 100;
      }
    }
    plateHint.textContent = side.length
      ? `≈ 45 lb bar + ${side.map((p) => p + "×2").join(", ")}`
      : "Bar only";
    const plateLink = document.getElementById("plate-calc-link");
    if (plateLink && w > 0) plateLink.href = `/fitness/plates?weight=${w}`;
  };

  weightInput?.addEventListener("input", updatePlateHint);
  updatePlateHint();

  const submitSet = async (e) => {
    if (e) e.preventDefault();
    if (logBtn) {
      logBtn.disabled = true;
      logBtn.textContent = "Logging…";
    }

    const body = new FormData(form);
    if (warmupInput && warmupInput.type === "hidden") {
      body.set("is_warmup", warmupInput.value === "1" ? "1" : "0");
    }

    try {
      const res = await fetch(form.action, {
        method: "POST",
        body,
        headers: { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" },
      });
      if (!res.ok) throw new Error("Failed");
      const data = await res.json();
      const row = buildSetRow(data.set);
      if (row && setsList) {
        setsEmpty?.classList.add("hidden");
        setsList.appendChild(row);
      }
      if (setLabel) setLabel.textContent = `Log Set ${data.set_count + 1}`;
      if (data.prefill) {
        weightInput.value = data.prefill.weight;
        repsInput.value = data.prefill.reps;
        if (rpeInput) rpeInput.value = data.prefill.rpe || "";
      }
      updatePlateHint();
      if (window.HomeOSMotion) HomeOSMotion.hapticSetLog();
      else if (navigator.vibrate) navigator.vibrate(18);
      if (logBtn) {
        logBtn.classList.remove("btn-log-bounce");
        void logBtn.offsetWidth;
        logBtn.classList.add("btn-log-bounce");
      }
      rest.start(rest.defaultSeconds);
      if (data.pr) showPrCelebration(data.pr);
      showUndoToast(data.set, form.action.replace("/sets", "/sets"));
      sheetApi?.afterSetLogged(data.set_count);
    } catch (err) {
      console.error(err);
      form.submit();
    } finally {
      if (logBtn) {
        logBtn.disabled = false;
        logBtn.textContent = "Log Set";
      }
    }
  };

  form.addEventListener("submit", submitSet);
  sameBtn?.addEventListener("click", submitSet);

  document.getElementById("sets-list")?.addEventListener("click", async (e) => {
    const editBtn = e.target.closest("[data-edit-toggle]");
    if (editBtn) {
      const formEl = document.getElementById("edit-set-" + editBtn.dataset.editToggle);
      formEl?.classList.toggle("hidden");
      return;
    }
    const delBtn = e.target.closest("[data-delete-set]");
    if (delBtn) {
      e.preventDefault();
      const row = delBtn.closest("[data-set-row]");
      const delForm = row?.querySelector("[data-delete-form]");
      if (!delForm) return;
      try {
        const res = await fetch(delForm.action, {
          method: "POST",
          headers: { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" },
        });
        if (!res.ok) throw new Error("Failed");
        const data = await res.json();
        row.remove();
        if (setLabel) setLabel.textContent = `Log Set ${data.set_count + 1}`;
        if (setsList && !setsList.querySelector("[data-set-row]")) {
          setsEmpty?.classList.remove("hidden");
        }
      } catch (err) {
        delForm.submit();
      }
    }
  });
}

let undoTimer = null;
function showUndoToast(setData, _) {
  const toast = document.getElementById("undo-toast");
  if (!toast) return;
  toast.classList.remove("hidden");
  clearTimeout(undoTimer);
  undoTimer = setTimeout(() => toast.classList.add("hidden"), 5000);
  toast.dataset.setId = setData.id;
}

document.getElementById("undo-set-btn")?.addEventListener("click", async () => {
  const toast = document.getElementById("undo-toast");
  const id = toast?.dataset.setId;
  if (!id) return;
  const row = document.querySelector(`[data-set-row][data-set-id="${id}"]`);
  const delForm = row?.querySelector("[data-delete-form]");
  if (delForm) {
    await fetch(delForm.action, {
      method: "POST",
      headers: { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" },
    });
    row?.remove();
  }
  toast?.classList.add("hidden");
});

/** Debounced session notes autosave */
function initNotesAutosave(textareaId, url) {
  const ta = document.getElementById(textareaId);
  if (!ta || !url) return;
  let timer = null;
  const status = document.getElementById("notes-save-status");

  const save = async () => {
    const body = new FormData();
    body.set("notes", ta.value);
    try {
      await fetch(url, {
        method: "POST",
        body,
        headers: { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" },
      });
      if (status) {
        status.textContent = "Saved";
        setTimeout(() => { status.textContent = ""; }, 2000);
      }
    } catch (_) {
      if (status) status.textContent = "Save failed";
    }
  };

  ta.addEventListener("input", () => {
    if (status) status.textContent = "Saving…";
    clearTimeout(timer);
    timer = setTimeout(save, 800);
  });
}

/** Collapsible sections */
function initCollapsible(toggleId, panelId) {
  document.getElementById(toggleId)?.addEventListener("click", () => {
    document.getElementById(panelId)?.classList.toggle("hidden");
    const btn = document.getElementById(toggleId);
    const open = btn?.getAttribute("aria-expanded") === "true";
    btn?.setAttribute("aria-expanded", open ? "false" : "true");
  });
}

/** Confirm destructive actions */
function initConfirmForms(selector) {
  document.querySelectorAll(selector).forEach((form) => {
    form.addEventListener("submit", (e) => {
      const msg = form.dataset.confirm;
      if (msg && !confirm(msg)) e.preventDefault();
    });
  });
}

/** Collapsible switch panel (#workout-switch) */
function initSwitchPanel() {
  const header = document.getElementById("switch-header");
  const body = document.getElementById("switch-body");
  const chevron = document.getElementById("switch-chevron");
  if (!header || !body) return;

  let open = false;
  const toggle = (force) => {
    open = force !== undefined ? force : !open;
    body.classList.toggle("hidden", !open);
    header.setAttribute("aria-expanded", String(open));
    chevron?.classList.toggle("rotate-180", open);
  };

  /* Auto-open on log page if user has exercises to show (no sets yet) */
  const hasSets = document.getElementById("sets-list")?.querySelector("[data-set-row]");
  if (!hasSets) toggle(true);

  header.addEventListener("click", () => toggle());
}

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("exercise-list")) {
    initExercisePicker({
      searchId: "exercise-search",
      listSelector: "#exercise-list",
      rowSelector: ".exercise-row",
      groupSelectId: "muscle-filter",
      beginnerToggleId: "index-beginner-mode-toggle",
    });
  }

  /* Session page: picker with defaultGroup from data-attr */
  const sessionPicker = document.getElementById("session-exercise-picker");
  if (sessionPicker) {
    initExercisePicker({
      searchId: "session-exercise-search",
      listSelector: "#session-exercise-list",
      rowSelector: ".exercise-row",
      chipsSelector: "#session-muscle-chips .muscle-chip",
      defaultGroup: sessionPicker.dataset.defaultMuscle || "",
    });
  }

  /* Switch-panel: pass defaultGroup so LEGS session pre-selects the Legs chip */
  const switchSection = document.getElementById("workout-switch");
  initExercisePicker({
    searchId: "switch-exercise-search",
    listSelector: "#switch-exercise-list",
    rowSelector: ".exercise-switch-row",
    chipsSelector: "#switch-muscle-chips .muscle-chip",
    defaultGroup: switchSection?.dataset.defaultMuscle || "",
    beginnerToggleId: "beginner-mode-toggle",
  });

  initExerciseSearch("routine-exercise-search", "#routine-pick-list", ".routine-pick-row");
  initHiddenSplits();
  initConfirmForms("[data-confirm]");
  initCollapsible("prev-target-toggle", "prev-target-panel");
  initSwitchPanel();

  const sheetApi = initLogSheet();
  initPlanAjax(sheetApi);
  initAjaxSetLogging("log-set-form", sheetApi);
  initNotesAutosave("session-notes", document.getElementById("session-notes")?.dataset.autosaveUrl);
});
