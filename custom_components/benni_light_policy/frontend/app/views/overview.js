// Tab 1 — Übersicht: aktuelle Entscheidung, Zusammenfassung, Coverage, Direkt-Aktionen.
import { esc, chip } from "../styles.js";
import { coverageChip } from "../components/look-select.js";

export function render(el, ctx) {
  const { store } = ctx;
  const s = store.status;
  if (!s || s._error) {
    el.innerHTML = `<div class="empty"><span class="ico">⏳</span>${
      s && s._error ? "Status nicht verfügbar: " + esc(s._error) : "Lade Status …"}</div>`;
    return;
  }

  const plan = s.plan || {};
  const gate = s.gate || {};
  const desiredKey = s.desired_policy_key;
  const isIdle = plan.apply_kind === "off" || !desiredKey;
  const cov = !isIdle && desiredKey ? store.coverage(desiredKey) : null;
  const desiredLook = cov && cov.look;
  const running = desiredLook ? store.lookSwitchState(desiredLook) : null;
  const briPct = plan.brightness != null ? Math.round((plan.brightness / 255) * 100) : null;
  const sum = store.coverageSummary(store.policyKeys());

  const blockers = plan.blockers || [];
  const summaryRows = [
    ["System bereit", `${(s.foundation || {}).ok ?? 0}/${(s.foundation || {}).total ?? 0} Entities`,
      (s.foundation || {}).ok === (s.foundation || {}).total ? "ok" : "warn"],
    ["Apply", s.apply_enabled ? "Automatische Anwendung" : "Shadow (aus)", s.apply_enabled ? "ok" : "info"],
    ["Lux-Gate", gate.lux_gate_on ? "offen (dunkel genug)" : "zu (hell genug)", gate.lux_gate_on ? "ok" : "info"],
    ["Manual-Off", s.manual_off ? "aktiv (blockiert)" : "inaktiv", s.manual_off ? "warn" : "ok"],
    ["Blockierende Gründe", blockers.length ? blockers.join(", ") : "keine", blockers.length ? "error" : "ok"],
  ];

  // Erste Kachel: bei Idle „Kein Look nötig" statt Fehleroptik.
  const lookTile = isIdle
    ? `<div class="tile">
         <div class="lbl">Gewünschter Look (Policy)</div>
         <div class="big">Kein Look nötig</div>
         <div class="subtext">${esc(plan.mode || "idle")}</div>
         <div style="margin-top:8px">${chip("info", idleReason(plan))}</div>
       </div>`
    : `<div class="tile">
         <div class="lbl">Gewünschter Look (Policy)</div>
         <div class="big purple">${esc(cov ? cov.ref : "—")}</div>
         <div class="subtext">${esc(desiredKey)}</div>
         <div style="margin-top:8px">${cov ? coverageChip(cov) : ""}</div>
       </div>`;

  const runTile = isIdle
    ? `<div class="tile"><div class="lbl">Tatsächlich</div>
         <div class="big">Lampen aus</div>
         <div style="margin-top:8px">${chip("ok", "wie gewünscht")}</div></div>`
    : `<div class="tile"><div class="lbl">Tatsächlich laufend</div>
         <div class="big">${desiredLook ? esc(desiredLook.name || desiredLook.slug) : "—"}</div>
         <div style="margin-top:8px">${
           running == null ? chip("info", "unbekannt")
             : chip(running === "on" ? "ok" : "info", running === "on" ? "läuft" : "aus")}</div></div>`;

  el.innerHTML = `
    <div class="grid cols-3">
      <div class="card" style="grid-column: span 2;">
        <h2><span class="ico">🧭</span>Aktuelle Entscheidung</h2>
        <div class="grid cols-3">
          ${lookTile}
          ${runTile}
          <div class="tile">
            <div class="lbl">Helligkeit (Tagesphase)</div>
            <div class="big">${isIdle ? "—" : (briPct != null ? briPct + " %" : "—")}</div>
            <div class="subtext">${isIdle ? "kein Licht" : (plan.brightness != null ? plan.brightness + " / 255" : "kein Override")}</div>
          </div>
          <div class="tile"><div class="lbl">Modus</div><div class="big">${esc(plan.mode || "—")}</div></div>
          <div class="tile"><div class="lbl">Scene-Hash</div><div class="mono" style="margin-top:6px">${esc(plan.scene_hash || "—")}</div></div>
          <div class="tile"><div class="lbl">Begründung</div><div style="margin-top:4px;font-size:13px">${esc(plan.reason || "—")}</div></div>
        </div>
      </div>

      <div class="card">
        <h2><span class="ico">🧾</span>Entscheidungs-Zusammenfassung</h2>
        ${summaryRows.map(([k, v, st]) => `
          <div class="kv"><span class="k">${esc(k)}</span>
            <span class="v">${chip(st, v)}</span></div>`).join("")}
      </div>
    </div>

    <div class="grid cols-3" style="margin-top:14px">
      <div class="card">
        <h2><span class="ico">🛡️</span>Look-Abdeckung</h2>
        ${donut(sum)}
        <button class="btn primary" id="toMap" style="margin-top:12px;width:100%">Look-Mapping öffnen →</button>
      </div>

      <div class="card" style="grid-column: span 2;">
        <h2><span class="ico">⚡</span>Direkt-Aktionen <span class="sub">— Apply runtime-Schalter</span></h2>
        <div class="kv">
          <span class="k">Apply<small>Automatische Lichtanwendung</small></span>
          <label class="toggle"><input type="checkbox" id="applyTgl" ${s.apply_enabled ? "checked" : ""}>
            <span class="track"><span class="knob"></span></span></label>
        </div>
        <div class="kv"><span class="k">Lux-Gate<small>aus Wetter/Lux/Tagesphase</small></span>
          <span class="v">${chip(gate.lux_gate_on ? "ok" : "info", gate.lux_gate_on ? "offen" : "zu (hell genug)")}</span></div>
        <div class="kv"><span class="k">Manual-Off<small>per Switch Manager</small></span>
          <span class="v">${chip(s.manual_off ? "warn" : "ok", s.manual_off ? "aktiv" : "inaktiv")}</span></div>
        <div class="kv"><span class="k">Bettgeh-Signal (R16)</span>
          <span class="v">${chip(s.bedtime_active ? "info" : "ok", s.bedtime_active ? "aktiv" : "inaktiv")}</span></div>
      </div>
    </div>`;

  el.querySelector("#toMap").addEventListener("click", () => ctx.navigate("look-mapping"));
  el.querySelector("#applyTgl").addEventListener("change", async (e) => {
    try {
      await store.setApplyEnabled(e.target.checked);
      ctx.toast(`Apply ${e.target.checked ? "aktiviert" : "deaktiviert"}`);
      setTimeout(ctx.refresh, 600);
    } catch (err) { ctx.toast("Fehler: " + (err.message || err)); }
  });
}

function idleReason(plan) {
  const r = (plan.reason || "").toLowerCase();
  if (r.includes("lux_gate")) return "Lux-Gate geschlossen – hell genug";
  if (r.includes("sleep")) return "Schlafmodus aktiv";
  if (r.includes("manual_off")) return "Manual-Off aktiv";
  return "bewusst kein Licht";
}

function donut(sum) {
  const total = sum.total || 1;
  const okDeg = (sum.ok / total) * 360;
  const missDeg = okDeg + (sum.missing / total) * 360;
  return `
    <div style="display:flex;gap:16px;align-items:center">
      <div class="donut" style="width:118px;height:118px;border-radius:50%;
        background: conic-gradient(var(--green) 0 ${okDeg}deg, var(--yellow) ${okDeg}deg ${missDeg}deg, var(--red) ${missDeg}deg 360deg);">
        <div style="width:84px;height:84px;border-radius:50%;background:var(--card);display:grid;place-items:center">
          <div style="text-align:center"><b style="font-size:18px">${sum.ok}/${sum.total}</b><br><small class="muted">gemappt</small></div>
        </div>
      </div>
      <div class="legend">
        <div><span class="sw" style="background:var(--green)"></span>Gemappt <b>${sum.ok}</b></div>
        <div><span class="sw" style="background:var(--yellow)"></span>Offen <b>${sum.missing}</b></div>
        ${sum.invalid ? `<div><span class="sw" style="background:var(--red)"></span>Ungültig <b>${sum.invalid}</b></div>` : ""}
        <div class="muted" style="font-size:12px;margin-top:4px">${sum.missing} offen — über Look-Mapping &amp; Matrix zuweisen.</div>
      </div>
    </div>`;
}
