// Look-Selector aus der echten Look-Liste (Wert = Slug, Anzeige = Name).
// Kein Freitext/UUID, solange die Look-Liste verfügbar ist.
import { esc, chip } from "../styles.js";

// dataAttrs: z.B. {"data-key": "winter_late_evening"} → das aufrufende View hört per change.
export function lookSelectHTML(currentRef, looks, dataAttrs = {}) {
  const attrs = Object.entries(dataAttrs)
    .map(([k, v]) => `${k}="${esc(v)}"`)
    .join(" ");

  if (!Array.isArray(looks)) {
    return `<input type="text" class="look-input" value="${esc(currentRef || "")}"
      placeholder="Look-Slug oder -Name" ${attrs}>`;
  }

  const known = looks.some((l) => l.slug === currentRef || l.name === currentRef);
  const opts = [`<option value="">— kein Look —</option>`];
  for (const l of looks) {
    const sel = l.slug === currentRef || l.name === currentRef ? "selected" : "";
    opts.push(`<option value="${esc(l.slug)}" ${sel}>${esc(l.name || l.slug)}</option>`);
  }
  if (currentRef && !known) {
    opts.push(`<option value="${esc(currentRef)}" selected>⚠ ${esc(currentRef)} (fehlt)</option>`);
  }
  return `<select class="look-select" ${attrs}>${opts.join("")}</select>`;
}

// Einheitliche Optik der 4 Coverage-Zustände.
export const KIND_META = {
  mapped: { chip: "ok", label: "vorhanden", dot: "ok" },
  fallback: { chip: "info", label: "Fallback", dot: "fallback" },
  invalid: { chip: "error", label: "ungültig", dot: "error" },
  missing: { chip: "warn", label: "fehlt", dot: "warn" },
};

export function coverageChip(cov) {
  const m = KIND_META[cov.kind] || KIND_META.missing;
  return chip(m.chip, m.label);
}

// Kompakte, klickbare Matrix-Zelle: kurzer Look-Name + Status-Punkt, kein Dropdown.
export function coverageCellHTML(key, cov, dataAttrs = {}) {
  const m = KIND_META[cov.kind] || KIND_META.missing;
  const attrs = Object.entries({ "data-key": key, ...dataAttrs })
    .map(([k, v]) => `${k}="${esc(v)}"`).join(" ");
  const name = cov.look ? (cov.look.name || cov.look.slug) : (cov.kind === "invalid" ? cov.ref : "—");
  const titleFallback = cov.kind === "fallback" ? ` title="Kein Mapping — Key „${esc(key)}" wird direkt als Look-Ref versucht."` : "";
  return `<div class="mcell ${cov.kind}" ${attrs}${titleFallback}>
    <span class="nm">${esc(name)}</span>
    <span class="st"><span class="dot ${m.dot}"></span>${m.label}</span>
  </div>`;
}
