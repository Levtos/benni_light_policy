// Tab 4 — Spezialregeln: Gaming/Musik-Subentries, classifier_value → Look.
import { esc, chip } from "../styles.js";
import { lookSelectHTML } from "../components/look-select.js";

const TYPE_LABEL = { gaming: "Gaming", music: "Musik-Party" };

export function render(el, ctx) {
  const { store } = ctx;
  const s = store.status;
  if (!s || s._error) {
    el.innerHTML = `<div class="empty"><span class="ico">⏳</span>Status nicht verfügbar.</div>`;
    return;
  }
  const rules = (s.subentry_rules || []).filter((r) => r.type === "gaming" || r.type === "music");
  const looksOk = store.scenePresetsAvailable();

  if (!rules.length) {
    el.innerHTML = `<div class="empty"><span class="ico">🎮</span>
      Keine Gaming-/Musik-Subentries konfiguriert.<br>
      <span class="muted">Über Einstellungen → Integration → „Subentry hinzufügen" anlegen.</span></div>`;
    return;
  }

  el.innerHTML = `<div class="grid cols-2">${rules.map((r) => card(r, store, looksOk)).join("")}</div>`;

  el.querySelectorAll(".rule-card").forEach((cardEl) => {
    const subId = cardEl.dataset.sub;
    cardEl.querySelector(".rule-save").addEventListener("click", async () => {
      const mappings = {};
      cardEl.querySelectorAll(".map-row").forEach((row) => {
        const v = row.querySelector(".map-val").value.trim();
        const node = row.querySelector(".look-select, .look-input");
        const look = node ? node.value.trim() : "";
        if (v && look) mappings[v] = look;
      });
      try {
        await store.setSubentryMappings(subId, mappings);
        ctx.toast("Spezialregel gespeichert");
        setTimeout(ctx.refresh, 600);
      } catch (err) {
        ctx.toast("Fehler: " + (err.message || err));
      }
    });
  });
}

function card(r, store, looksOk) {
  const entries = Object.entries(r.mappings || {});
  const filled = entries.length;
  const valid = entries.filter(([, ref]) => store.lookFor(ref)).length;
  const completeChip = filled === 0
    ? chip("warn", "leer")
    : chip(valid === filled ? "ok" : "error", `${valid}/${filled} Looks`);

  const row = (val, ref) => `
    <div class="map-row" style="display:grid;grid-template-columns:130px 1fr auto;gap:8px;align-items:center;margin-bottom:7px">
      <input type="text" class="map-val" value="${esc(val)}" placeholder="Classifier-Wert">
      ${lookSelectHTML(ref || "", looksOk ? store.looks : null, {})}
      <span>${ref ? chip(store.lookFor(ref) ? "ok" : "error", store.lookFor(ref) ? "ok" : "fehlt") : ""}</span>
    </div>`;

  const rows = entries.map(([v, ref]) => row(v, ref)).join("");
  const emptyRow = row("", "");

  return `
    <div class="card rule-card" data-sub="${esc(r.subentry_id)}">
      <h2><span class="ico">${r.type === "gaming" ? "🎮" : "🎵"}</span>${esc(r.title || TYPE_LABEL[r.type])}
        <span class="sub">${esc(TYPE_LABEL[r.type] || r.type)}</span></h2>
      <div class="kv"><span class="k">Classifier</span>
        <span class="subtext">${esc(r.classifier_entity || "—")}</span></div>
      ${r.source_id ? `<div class="kv"><span class="k">Source-ID</span><span class="mono">${esc(r.source_id)}</span></div>` : ""}
      <div class="kv"><span class="k">Mapping</span><span class="v">${completeChip}</span></div>
      <div style="margin-top:10px">${rows}${emptyRow}</div>
      <button class="btn primary rule-save" style="margin-top:8px">Speichern</button>
    </div>`;
}
