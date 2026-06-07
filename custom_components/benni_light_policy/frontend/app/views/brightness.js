// Tab 4 — Helligkeit: Day-State-Profil plus optionale Theme-Overrides.
import { esc } from "../styles.js";
import { MODE_LABELS, PHASE_LABELS, THEME_LABELS } from "../store.js";

const FIXED_KEYS = ["waking", "work_home", "private_time"];

export function render(el, ctx) {
  const { store } = ctx;
  const s = store.status;
  const cat = store.catalog;
  if (!s || s._error || !cat || cat._error) {
    el.innerHTML = `<div class="empty"><span class="ico">⏳</span>Helligkeitsprofil nicht verfügbar.</div>`;
    return;
  }

  const phases = cat.phases || [];
  const themes = cat.themes || [];
  const profile = s.brightness_profile || {};
  const customThemes = cat.custom_themes || [];

  const fixedRows = FIXED_KEYS.map((key) => rowInput(key, MODE_LABELS[key] || key, profile[key])).join("");
  const head = `<tr><th>Theme \\ Phase</th>${phases.map((p) =>
    `<th>${esc(PHASE_LABELS[p] || p)}</th>`).join("")}</tr>`;
  const standard = `<tr><td><b>Standard</b></td>${phases.map((p) =>
    `<td>${brightnessInput(p, profile[p], false)}</td>`).join("")}</tr>`;
  const body = themes.map((theme) => `<tr><td><b>${esc(THEME_LABELS[theme] || theme)}</b></td>${
    phases.map((p) => {
      const key = `${theme}_${p}`;
      return `<td>${brightnessInput(key, profile[key], true, profile[p])}</td>`;
    }).join("")
  }</tr>`).join("");

  el.innerHTML = `
    <div class="grid">
      <div class="card">
        <h2><span class="ico">🔆</span>Day-State-Helligkeit
          <span class="sub">— wird als brightness Override an apply_look gesendet</span></h2>
        <table class="brightness-table"><thead>${head}</thead><tbody>${standard}${body}</tbody></table>
        <div class="row-actions">
          <button class="btn primary" id="saveBrightness">Helligkeit speichern</button>
        </div>
      </div>

      <div class="card">
        <h2><span class="ico">🎛</span>Feste Modi</h2>
        <div class="grid cols-3">${fixedRows}</div>
      </div>

      <div class="card">
        <h2><span class="ico">🗓</span>Zusätzliche Matrix-Zeilen
          <span class="sub">— Slugs, kommasepariert; Kalender-/Season-Sensor muss denselben Slug liefern</span></h2>
        <input type="text" id="customThemes" value="${esc(customThemes.join(", "))}"
          placeholder="sommerferien, urlaub, party">
        <div class="row-actions">
          <button class="btn" id="saveThemes">Zeilen speichern</button>
        </div>
      </div>
    </div>`;

  el.querySelector("#saveBrightness").addEventListener("click", async () => {
    const next = {};
    el.querySelectorAll(".bri-input").forEach((node) => {
      const key = node.dataset.key;
      const raw = node.value.trim();
      if (raw === "") return;
      next[key] = Number(raw);
    });
    try {
      await store.setBrightnessProfile(next);
      ctx.toast("Helligkeit gespeichert");
      ctx.rerender();
    } catch (err) {
      ctx.toast("Fehler: " + (err.message || err));
    }
  });

  el.querySelector("#saveThemes").addEventListener("click", async () => {
    const themes = el.querySelector("#customThemes").value
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean);
    try {
      await store.setCustomThemes(themes);
      await ctx.refresh();
      ctx.toast("Matrix-Zeilen gespeichert");
    } catch (err) {
      ctx.toast("Fehler: " + (err.message || err));
    }
  });
}

function rowInput(key, label, value) {
  return `<div class="kv"><span class="k">${esc(label)}</span>
    <span class="v">${brightnessInput(key, value, false)}</span></div>`;
}

function brightnessInput(key, value, optional, fallback) {
  const placeholder = optional && fallback != null ? String(fallback) : "";
  return `<input type="number" class="bri-input" min="0" max="255" step="1"
    data-key="${esc(key)}" value="${value == null ? "" : esc(value)}" placeholder="${esc(placeholder)}">`;
}
