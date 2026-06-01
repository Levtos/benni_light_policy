// Tab 6 — Diagnose: Entscheidungskette, Gates, blockierende Gründe, Coverage-Probleme.
import { esc, chip } from "../styles.js";
import { PHASE_LABELS, THEME_LABELS, MODE_LABELS } from "../store.js";

export function render(el, ctx) {
  const { store } = ctx;
  const s = store.status;
  if (!s || s._error) {
    el.innerHTML = `<div class="empty"><span class="ico">⏳</span>${
      s && s._error ? esc(s._error) : "Lade …"}</div>`;
    return;
  }
  const g = s.gate || {};
  const plan = s.plan || {};
  const thr = g.thresholds || {};

  const kv = (k, v, st) => `<div class="kv"><span class="k">${esc(k)}</span>
    <span class="v">${st ? chip(st, v) : esc(v)}</span></div>`;

  const left = `
    <div class="card">
      <h2><span class="ico">🩺</span>Entscheidung & Gates</h2>
      ${kv("System bereit", g.startup_ready ? "ja" : "nein", g.startup_ready ? "ok" : "warn")}
      ${kv("Apply aktiviert", s.apply_enabled ? "ja" : "Shadow", s.apply_enabled ? "ok" : "info")}
      ${kv("Lux-Gate", g.lux_gate_on ? "offen" : "zu", g.lux_gate_on ? "ok" : "info")}
      ${kv("TMC-Latch (war hell)", g.tmc_set ? "ja" : "nein", g.tmc_set ? "ok" : "info")}
      ${kv("Wetter-Dunkelheit", g.weather_dark ? "ja" : "nein", g.weather_dark ? "warn" : "ok")}
      ${kv("Manual-Off", s.manual_off ? "aktiv" : "inaktiv", s.manual_off ? "warn" : "ok")}
      ${kv("Day-State", PHASE_LABELS[s.day_state] || s.day_state || "—")}
      ${kv("Activity", s.activity || "—")}
      ${kv("Jahreszeit", THEME_LABELS[g.season] || g.season || "—")}
      ${kv("Lux-Schwellen", `dunkel ${thr.dark ?? "?"} / hell ${thr.bright ?? "?"} lx`)}
      ${kv("Lux-Samples (10 min)", String(g.lux_samples ?? 0))}
    </div>`;

  const desiredKey = s.desired_policy_key;
  const cov = desiredKey ? store.coverage(desiredKey) : null;
  const blockers = plan.blockers || [];

  // Coverage-Probleme über alle Soll-Keys.
  const problems = store.policyKeys()
    .map((k) => ({ k, c: store.coverage(k) }))
    .filter((x) => x.c.status !== "ok");

  const problemList = problems.length
    ? problems.map(({ k, c }) => `<div class="kv">
        <span class="k">${esc(labelFor(k))}<small>${esc(k)}${c.mapped ? " → " + esc(c.ref) : ""}</small></span>
        <span class="v">${chip(c.status === "invalid" ? "error" : "warn",
          c.status === "invalid" ? "ungültig" : "fehlt")}</span></div>`).join("")
    : `<div style="margin-top:6px">${chip("ok", "alle Soll-Keys gemappt")}</div>`;

  const right = `
    <div class="card">
      <h2><span class="ico">🎯</span>Gewünschter Look</h2>
      ${kv("Policy-Key", desiredKey || "idle (kein Look)")}
      ${kv("Aufgelöster Look-Ref", cov ? cov.ref : "—",
        cov ? (cov.status === "ok" ? "ok" : cov.status === "invalid" ? "error" : "warn") : null)}
      ${kv("Helligkeit", plan.brightness != null ? plan.brightness + " / 255" : "—")}
      ${kv("Apply erlaubt", plan.apply_allowed ? "ja" : "nein", plan.apply_allowed ? "ok" : "warn")}
      <div class="kv"><span class="k">Blockierende Gründe</span>
        <span class="v">${blockers.length ? chip("error", blockers.join(", ")) : chip("ok", "keine")}</span></div>
      <div class="kv"><span class="k">Grund</span><span class="subtext">${esc(plan.reason || "—")}</span></div>
    </div>
    <div class="card">
      <h2><span class="ico">🧩</span>Coverage-Probleme <span class="sub">${problems.length} betroffen</span></h2>
      <div style="max-height:280px;overflow:auto">${problemList}</div>
    </div>`;

  el.innerHTML = `<div class="grid cols-2"><div>${left}</div><div class="grid">${right}</div></div>`;
}

function labelFor(key) {
  if (MODE_LABELS[key]) return MODE_LABELS[key];
  const parts = key.split("_");
  const phase = parts.slice(-2).join("_");
  const theme = parts.slice(0, -2).join("_") || parts[0];
  if (THEME_LABELS[theme] && PHASE_LABELS[phase]) return `${THEME_LABELS[theme]} · ${PHASE_LABELS[phase]}`;
  return key;
}
