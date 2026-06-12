/* ---- Fitness Hub — in-gym UX helpers ---- */

/** Exercise list search/filter */
function initExerciseSearch(inputId, listSelector, rowSelector) {
  const input = document.getElementById(inputId);
  const list = document.querySelector(listSelector);
  if (!input || !list) return;

  const filter = () => {
    const q = input.value.trim().toLowerCase();
    list.querySelectorAll(rowSelector).forEach((row) => {
      const name = (row.dataset.name || "").toLowerCase();
      const group = (row.dataset.group || "").toLowerCase();
      const match = !q || name.includes(q) || group.includes(q);
      row.classList.toggle("hidden", !match);
    });
    const empty = list.querySelector("[data-search-empty]");
    if (empty) {
      const visible = [...list.querySelectorAll(rowSelector)].some(
        (r) => !r.classList.contains("hidden")
      );
      empty.classList.toggle("hidden", visible || !q);
    }
  };

  input.addEventListener("input", filter);
  return filter;
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
  wrap.querySelectorAll("[data-warmup]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const val = btn.dataset.warmup === "1";
      hidden.value = val ? "1" : "0";
      wrap.querySelectorAll("[data-warmup]").forEach((b) => {
        const on = b.dataset.warmup === (val ? "1" : "0");
        b.classList.toggle("bg-neon/15", on);
        b.classList.toggle("border-neon/40", on);
        b.classList.toggle("text-neon", on);
      });
    });
  });
}

/** Rest timer with remembered duration */
function createRestTimer(opts) {
  const panel = document.getElementById(opts.panelId || "rest-timer");
  const display = document.getElementById(opts.displayId || "rest-display");
  const bar = document.getElementById(opts.barId || "rest-bar");
  const storageKey = opts.storageKey || "fitness-rest-seconds";
  let interval = null;
  let seconds = 0;
  let total = 90;

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
    clearInterval(interval);
    interval = setInterval(() => {
      seconds -= 1;
      if (display) display.textContent = format(Math.max(0, seconds));
      if (bar) bar.style.width = `${(seconds / total) * 100}%`;
      if (seconds <= 0) {
        clearInterval(interval);
        if (display) {
          display.textContent = "Go!";
          display.classList.add("text-emerald-400");
        }
        if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
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
  });

  const defaultSec = parseInt(localStorage.getItem(storageKey) || "90", 10);
  return { start, defaultSeconds: defaultSec };
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

  return row;
}

/** AJAX set logging on exercise page */
function initAjaxSetLogging(formId) {
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
      rest.start(rest.defaultSeconds);
      showUndoToast(data.set, form.action.replace("/sets", "/sets"));
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

document.addEventListener("DOMContentLoaded", () => {
  initExerciseSearch("exercise-search", "#exercise-list", ".exercise-row");
  initExerciseSearch("session-exercise-search", "#session-exercise-list", ".exercise-row");
  initExerciseSearch("switch-exercise-search", "#switch-exercise-list", ".exercise-switch-row");
  initExerciseSearch("routine-exercise-search", "#routine-pick-list", ".routine-pick-row");
  initHiddenSplits();
  initConfirmForms("[data-confirm]");
  initCollapsible("prev-target-toggle", "prev-target-panel");
  initCollapsible("all-exercises-toggle", "all-exercises-panel");
  initAjaxSetLogging("log-set-form");
  initNotesAutosave("session-notes", document.getElementById("session-notes")?.dataset.autosaveUrl);
});
