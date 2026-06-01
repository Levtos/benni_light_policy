// Tab 3 — Tagesphasen-Matrix: Themes (Zeilen) × Phasen (Spalten) → Look.
// Helligkeit kommt aus dem Tagesphasen-Profil und wird getrennt vom Look gezeigt.
import { esc, chip } from "../styles.js";
import { PHASE_LABELS, THEME_LABELS } from "../store.js";
import { lookSelectHTML } from "../components/look-select.js";

const TINT = { ok: "rgba(80,250,123,.10)", invalid: "rgba(255,85,85,.12)", missing: "rgba(241,250,140,.10)" };

export function render(el, ctx) {
  const { store } = ctx;
  const cat = store.catalog;
  if (!cat || cat._error) {
    el.innerHTML = `<div class="empty"><span class="ico">⏳</span>Katalog nicht verfügbar.</div>`;
    return;
  }
  const themes = cat.themes || [];
  const phases = cat.phases || [];
  const looksOk = store.scenePresetsAvailable();
  const bri = (store.status && store.status.brightness_profile) || {};

  const head = `<tr><th>Theme \\ Phase</th>${phases.map((p) =>
    `<th>${esc(PHASE_LABELS[p] || p)}<div class="ph">${
      bri[p] != null ? Math.round((bri[p] / 255) * 100) + " %" : ""}</div></th>`).join("")}</tr>`;

  const body = themes.map((t) => {
    const cells = phases.map((p) => {
      const key = `${t}_${p}`;
      const cov = store.coverage(key);
      return `<td class="cell" style="background:${TINT[cov.status] || ""}">
        ${lookSelectHTML(store.lookMap[key] || "", looksOk ? store.looks : null, { "data-key": key })}
      </td>`;
    }).join("");
    return `<tr><td><b>${esc(THEME_LABELS[t] || t)}</b></td>${cells}</tr>`;
  }).join("");

  el.innerHTML = `
    <div class="card matrix">
      <h2><span class="ico">▦</span>Tagesphasen-Matrix
        <span class="sub">— jede Zelle mappt einen Policy-Key auf einen Look; Helligkeit kommt separat aus dem Profil</span></h2>
      ${!looksOk ? `<div style="margin-bottom:10px">${chip("warn",
        "benni_scene_presets nicht erreichbar — Freitext-Fallback")}</div>` : ""}
      <table><thead>${head}</thead><tbody>${body}</tbody></table>
      <p class="muted" style="font-size:12px;margin-top:10px">
        Zell-Tönung: grün = vorhanden, gelb = fehlt, rot = ungültig (gemappt, aber Look existiert nicht).
        Mehrere Zellen dürfen denselben Look nutzen.</p>
    </div>`;

  const onChange = async (key, value) => {
    const map = { ...store.lookMap };
    if (value) map[key] = value; else delete map[key];
    try {
      await store.setLookMap(map);
      ctx.toast("Matrix gespeichert");
      setTimeout(ctx.refresh, 500);
    } catch (err) {
      ctx.toast("Fehler: " + (err.message || err));
    }
  };
  el.querySelectorAll(".look-select, .look-input").forEach((node) =>
    node.addEventListener("change", () => onChange(node.dataset.key, node.value.trim())));
}
