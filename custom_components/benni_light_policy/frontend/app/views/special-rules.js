// Tab 4 — Spezialregeln: Gaming/Musik-Subentries, classifier_value → Look.
// Auto-Save (konsistent mit Look-Mapping & Matrix).
import { esc, chip } from "../styles.js";
import { lookSelectHTML } from "../components/look-select.js";

const TYPE_LABEL = { gaming: "Gaming", music: "Musik-Party" };
const TYPE_ICON = { gaming: "🎮", music: "🎵" };
const SLOTS = 8;

export function render(el, ctx) {
  const { store, hass } = ctx;
  const s = store.status;
  if (!s || s._error) {
    el.innerHTML = `<div class="empty"><span class="ico">⏳</span>Status nicht verfügbar.</div>`;
    return;
  }
  const rules = (s.subentry_rules || []).filter((r) => r.type === "gaming" || r.type === "music");
  const looksOk = store.scenePresetsAvailable();

  if (!rules.length) {
    el.innerHTML = `<div class="empty"><span class="ico">🎮</span>
      Keine Gaming-/Musik-Regeln konfiguriert.<br>
      <span class="muted">Über Einstellungen → Integration → „Unterkategorie hinzufügen" anlegen.</span></div>`;
    return;
  }

  // Eindeutige Namen je Typ erzeugen.
  const counters = {};
  const named = rules.map((r) => {
    counters[r.type] = (counters[r.type] || 0) + 1;
    let name = r.title && r.title !== TYPE_LABEL[r.type] && r.title !== "Gaming" && r.title !== "Musik"
      ? r.title
      : (r.source_id ? `${TYPE_LABEL[r.type]} · ${r.source_id}` : `${TYPE_LABEL[r.type]} · Regel ${counters[r.type]}`);
    return { ...r, _name: name };
  });

  el.innerHTML = `<div class="grid cols-2">${named.map((r) => card(r, store, hass, looksOk)).join("")}</div>`;

  el.querySelectorAll(".rule-card").forEach((cardEl) => {
    const subId = cardEl.dataset.sub;
    const save = async () => {
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
      } catch (err) { ctx.toast("Fehler: " + (err.message || err)); }
    };
    cardEl.querySelectorAll(".map-val, .look-select, .look-input").forEach((node) =>
      node.addEventListener("change", save));
  });
}

function card(r, store, hass, looksOk) {
  const entries = Object.entries(r.mappings || {});
  const filled = entries.length;
  const valid = entries.filter(([, ref]) => store.lookFor(ref)).length;
  const curVal = r.classifier_entity && hass && hass.states[r.classifier_entity]
    ? hass.states[r.classifier_entity].state : null;
  const active = curVal != null && Object.prototype.hasOwnProperty.call(r.mappings || {}, curVal);

  // Primärer Status-Chip.
  let statusChip;
  if (filled === 0) statusChip = chip("warn", "leer");
  else if (active) statusChip = chip("ok", "aktiv");
  else if (valid === filled) statusChip = chip("ok", "vollständig");
  else statusChip = chip("warn", "unvollständig");

  const rowHTML = (val, ref) => {
    const ok = ref && store.lookFor(ref);
    return `<tr class="map-row">
      <td><input type="text" class="map-val" value="${esc(val)}" placeholder="Wert"></td>
      <td>${lookSelectHTML(ref || "", looksOk ? store.looks : null, {})}</td>
      <td style="width:18px">${ref ? `<span class="dot ${ok ? "ok" : "error"}" style="display:inline-block;width:8px;height:8px;border-radius:50%"></span>` : ""}</td>
    </tr>`;
  };

  const rows = entries.map(([v, ref]) => rowHTML(v, ref)).join("");
  const emptyRow = rowHTML("", "");

  return `
    <div class="card rule-card" data-sub="${esc(r.subentry_id)}">
      <h2><span class="ico">${TYPE_ICON[r.type] || "🎯"}</span>${esc(r._name)}
        <span class="sub">${esc(TYPE_LABEL[r.type] || r.type)}</span></h2>
      <div class="kv"><span class="k">Classifier</span>
        <span class="subtext">${esc(r.classifier_entity || "—")}</span></div>
      <div class="kv"><span class="k">Aktueller Wert</span>
        <span class="v">${curVal != null ? `<span class="mono">${esc(curVal)}</span>` : `<span class="muted">—</span>`}</span></div>
      <div class="kv"><span class="k">Belegt</span>
        <span class="v">${chip(filled ? "info" : "warn", `${filled} / ${SLOTS} belegt`)} ${statusChip}</span></div>
      <table style="margin-top:10px">
        <thead><tr><th>Classifier-Wert</th><th>Look</th><th></th></tr></thead>
        <tbody>${rows}${emptyRow}</tbody>
      </table>
      <p class="subtext" style="margin-top:8px">Änderungen werden automatisch gespeichert.</p>
    </div>`;
}
