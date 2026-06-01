// Look-Selector aus der echten Look-Liste (Wert = Slug, Anzeige = Name).
// Kein Freitext/UUID, solange die Look-Liste verfügbar ist.
import { esc, chip } from "../styles.js";

// dataAttrs: z.B. {"data-key": "winter_late_evening"} → das aufrufende View hört per change.
export function lookSelectHTML(currentRef, looks, dataAttrs = {}) {
  const attrs = Object.entries(dataAttrs)
    .map(([k, v]) => `${k}="${esc(v)}"`)
    .join(" ");

  if (!Array.isArray(looks)) {
    // Scene-Presets nicht erreichbar → Freitext als Fallback.
    return `<input type="text" class="look-input" value="${esc(currentRef || "")}"
      placeholder="Look-Slug oder -Name" ${attrs}>`;
  }

  const known = looks.some((l) => l.slug === currentRef || l.name === currentRef);
  const opts = [`<option value="">— kein Mapping (Key-Fallback) —</option>`];
  for (const l of looks) {
    const sel = l.slug === currentRef || l.name === currentRef ? "selected" : "";
    opts.push(`<option value="${esc(l.slug)}" ${sel}>${esc(l.name || l.slug)}</option>`);
  }
  // Aktueller Ref existiert nicht (mehr) → als ungültige Option sichtbar halten.
  if (currentRef && !known) {
    opts.push(`<option value="${esc(currentRef)}" selected>⚠ ${esc(currentRef)} (fehlt)</option>`);
  }
  return `<select class="look-select" ${attrs}>${opts.join("")}</select>`;
}

const STATUS_LABEL = { ok: "vorhanden", invalid: "ungültig", missing: "fehlend" };
const STATUS_CHIP = { ok: "ok", invalid: "error", missing: "warn" };

export function coverageChip(cov) {
  const label = STATUS_LABEL[cov.status] || cov.status;
  return chip(STATUS_CHIP[cov.status] || "info", label);
}
