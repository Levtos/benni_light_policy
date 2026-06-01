// Tab 2 — Look-Mapping: feste Policy-Modi → Look (Selector aus echter Look-Liste).
import { esc, chip } from "../styles.js";
import { MODE_LABELS } from "../store.js";
import { lookSelectHTML, coverageChip } from "../components/look-select.js";

export function render(el, ctx) {
  const { store } = ctx;
  const cat = store.catalog;
  if (!cat || cat._error) {
    el.innerHTML = `<div class="empty"><span class="ico">⏳</span>Katalog nicht verfügbar.</div>`;
    return;
  }
  const fixed = cat.fixed_modes || [];
  const looksOk = store.scenePresetsAvailable();

  const rows = fixed.map((key) => {
    const cov = store.coverage(key);
    return `<tr>
      <td><b>${esc(MODE_LABELS[key] || key)}</b><div class="subtext">${esc(key)}</div></td>
      <td>${lookSelectHTML(store.lookMap[key] || "", looksOk ? store.looks : null, { "data-key": key })}</td>
      <td>${coverageChip(cov)}</td>
    </tr>`;
  }).join("");

  el.innerHTML = `
    <div class="card">
      <h2><span class="ico">🎚️</span>Feste Modi → Look
        <span class="sub">— der Policy-Key (Subtext) wird auf einen echten Look (Slug/Name) gemappt</span></h2>
      ${!looksOk ? `<div style="margin-bottom:10px">${chip("warn",
        "benni_scene_presets nicht erreichbar — Freitext-Fallback")}</div>` : ""}
      <table>
        <thead><tr><th>Modus</th><th>Look</th><th>Coverage</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <p class="muted" style="font-size:12px;margin-top:12px">
        Mehrere Keys dürfen denselben Look nutzen. „kein Mapping" fällt auf den Key-Namen als Look-Ref zurück
        (nur falls ein Look exakt so heißt). Tagesphasen-Looks bearbeitest du in der Matrix.</p>
    </div>`;

  const onChange = async (key, value) => {
    const map = { ...store.lookMap };
    if (value) map[key] = value; else delete map[key];
    try {
      await store.setLookMap(map);
      ctx.toast("Mapping gespeichert");
      setTimeout(ctx.refresh, 500);
    } catch (err) {
      ctx.toast("Fehler: " + (err.message || err));
    }
  };
  el.querySelectorAll(".look-select, .look-input").forEach((node) => {
    const ev = node.classList.contains("look-input") ? "change" : "change";
    node.addEventListener(ev, () => onChange(node.dataset.key, node.value.trim()));
  });
}
