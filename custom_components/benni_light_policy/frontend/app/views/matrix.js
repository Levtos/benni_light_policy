// Tab 3 — Tagesphasen-Matrix: Themes (Zeilen) × Phasen (Spalten) → Look.
// Look-Auswahl per inline-Select direkt in der Zelle (kein Modal); Änderung wird
// sofort gespeichert. Helligkeit kommt aus dem Tagesphasen-Profil und wird separat gezeigt.
import { esc, chip } from "../styles.js";
import { PHASE_LABELS, THEME_LABELS } from "../store.js";
import { lookSelectHTML, coverageChip } from "../components/look-select.js";

export function render(el, ctx) {
  const { store } = ctx;
  const cat = store.catalog;
  if (!cat || cat._error) {
    el.innerHTML = `<div class="empty"><span class="ico">⏳</span>Katalog nicht verfügbar.</div>`;
    return;
  }
  const themes = cat.themes || [];
  const phases = cat.phases || [];
  const legacyPhases = cat.legacy_phases || [];
  const looksOk = store.scenePresetsAvailable();
  const bri = (store.status && store.status.brightness_profile) || {};

  const head = `<tr><th>Theme \\ Phase</th>${phases.map((p) =>
    `<th class="tcell">${esc(PHASE_LABELS[p] || p)}<div class="ph">${
      bri[p] != null ? Math.round((bri[p] / 255) * 100) + " %" : ""}</div></th>`).join("")}</tr>`;

  const body = themes.map((t) => {
    const cells = phases.map((p) => {
      const key = `${t}_${p}`;
      const cov = store.coverage(key);
      const cur = store.lookMap[key] || "";
      const value = bri[key] != null ? bri[key] : bri[p];
      const inherited = bri[key] == null;
      return `<td class="mx-cell ${cov.kind}">
        ${lookSelectHTML(cur, looksOk ? store.looks : null, { "data-key": key })}
        <div class="mx-meta">
          ${coverageChip(cov)}
          <span class="cell-bri ${inherited ? "inherited" : ""}">${
            value != null ? Math.round((value / 255) * 100) + " %" : "—"
          }</span>
        </div></td>`;
    }).join("");
    return `<tr><td><b>${esc(THEME_LABELS[t] || t)}</b></td>${cells}</tr>`;
  }).join("");

  el.innerHTML = `
    <div class="card matrix">
      <h2><span class="ico">▦</span>Tagesphasen-Matrix
        <span class="sub">— Look pro Zelle direkt wählen; Helligkeit kommt separat aus dem Profil</span></h2>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
        ${chip("ok", "vorhanden")} ${chip("info", "Fallback (Key = Look-Ref)")}
        ${chip("warn", "fehlt")} ${chip("error", "ungültig")}
      </div>
      <table><thead>${head}</thead><tbody>${body}</tbody></table>
      <p class="muted" style="font-size:12px;margin-top:10px">
        Mehrere Zellen dürfen denselben Look nutzen. „Fallback" heißt: kein Mapping gesetzt — der
        Key-Name wird direkt als Look-Ref versucht.${legacyPhases.length ? ` Legacy-Kompatibilitätsphasen
        bleiben außerhalb der Primärmatrix erhalten: ${esc(legacyPhases.join(", "))}.` : ""}</p>
    </div>`;

  const applyLook = async (key, value) => {
    const map = { ...store.lookMap };
    if (value) map[key] = value; else delete map[key];
    try {
      await store.setLookMap(map);
      ctx.toast(value ? "Look gespeichert" : "Mapping entfernt");
      ctx.rerender();
    } catch (err) {
      ctx.toast("Fehler: " + (err.message || err));
      ctx.rerender(); // Select auf den gespeicherten Stand zurücksetzen
    }
  };

  el.querySelectorAll(".look-select, .look-input").forEach((sel) =>
    sel.addEventListener("change", (e) =>
      applyLook(e.target.dataset.key, (e.target.value || "").trim())));
}
