/** Workout planner — live preview, add/remove/reorder exercises */

(function initPlanEditor() {
  const container = document.getElementById("plan-rows");
  const tpl = document.getElementById("plan-row-template");
  const previewList = document.getElementById("plan-preview-list");
  const previewEmpty = document.getElementById("plan-preview-empty");
  const previewCount = document.getElementById("plan-preview-count");
  const addSelect = document.getElementById("plan-add-select");
  const addSearch = document.getElementById("plan-add-search");
  if (!container || !tpl) return;

  function syncRowFields(row) {
    const sel = row.querySelector(".plan-exercise-select");
    if (!sel) return;
    const id = sel.value;
    const sets = row.querySelector("[data-sets]");
    const reps = row.querySelector("[data-reps]");
    if (sets) sets.name = `target_sets_${id}`;
    if (reps) reps.name = `target_reps_${id}`;
  }

  function updatePreview() {
    const rows = container.querySelectorAll(".plan-row");
    previewList.querySelectorAll("li:not(#plan-preview-empty)").forEach((li) => li.remove());

    if (!rows.length) {
      previewEmpty?.classList.remove("hidden");
      if (previewCount) previewCount.textContent = "0 exercises";
      return;
    }
    previewEmpty?.classList.add("hidden");
    if (previewCount) previewCount.textContent = `${rows.length} exercise${rows.length === 1 ? "" : "s"}`;

    rows.forEach((row, i) => {
      const sel = row.querySelector(".plan-exercise-select");
      const opt = sel?.selectedOptions[0];
      const sets = row.querySelector("[data-sets]")?.value || "3";
      const reps = row.querySelector("[data-reps]")?.value?.trim();
      const li = document.createElement("li");
      li.className = "flex items-baseline gap-2";
      li.innerHTML = `<span class="text-neon font-display font-bold w-5 shrink-0">${i + 1}.</span>
        <span class="flex-1">${opt?.dataset.name || opt?.textContent?.split(" (")[0] || "—"}</span>
        <span class="text-xs text-slate-500 shrink-0">${sets} sets${reps ? ` · ${reps} reps` : ""}</span>`;
      previewList.appendChild(li);
    });
  }

  function bindRow(row) {
    row.querySelector(".plan-exercise-select")?.addEventListener("change", () => {
      syncRowFields(row);
      updatePreview();
    });
    row.querySelector("[data-sets]")?.addEventListener("input", updatePreview);
    row.querySelector("[data-reps]")?.addEventListener("input", updatePreview);
    syncRowFields(row);
  }

  document.getElementById("plan-add-btn")?.addEventListener("click", () => {
    const row = tpl.content.cloneNode(true).querySelector(".plan-row");
    const sel = row.querySelector(".plan-exercise-select");
    if (addSelect && sel) sel.value = addSelect.value;
    bindRow(row);
    container.appendChild(row);
    updatePreview();
  });

  container.addEventListener("click", (e) => {
    const row = e.target.closest(".plan-row");
    if (!row) return;
    if (e.target.classList.contains("remove-row")) {
      row.remove();
      updatePreview();
      return;
    }
    if (e.target.classList.contains("move-up")) {
      const prev = row.previousElementSibling;
      if (prev) {
        container.insertBefore(row, prev);
        updatePreview();
      }
      return;
    }
    if (e.target.classList.contains("move-down")) {
      const next = row.nextElementSibling;
      if (next) {
        container.insertBefore(next, row);
        updatePreview();
      }
    }
  });

  if (addSearch && addSelect) {
    addSearch.addEventListener("input", () => {
      const q = addSearch.value.trim().toLowerCase();
      [...addSelect.options].forEach((opt) => {
        const name = (opt.dataset.name || "").toLowerCase();
        const group = (opt.dataset.group || "").toLowerCase();
        opt.hidden = q && !name.includes(q) && !group.includes(q);
      });
      const firstVisible = [...addSelect.options].find((o) => !o.hidden);
      if (firstVisible) addSelect.value = firstVisible.value;
    });
  }

  container.querySelectorAll(".plan-row").forEach(bindRow);
  updatePreview();
})();
