// Tab 7 — System: Foundation-Entities, Apply-Schalter, Brightness-Profil, Version.
import { esc, chip } from "../styles.js";
import { PHASE_LABELS, MODE_LABELS } from "../store.js";

export function render(el, ctx) {
  const { store, hass } = ctx;
  const s = store.status;
  if (!s || s._error) {
    el.innerHTML = `<div class="empty"><span class="ico">⏳</span>Status nicht verfügbar.</div>`;
    return;
  }
  const f = s.foundation || {};
  const bri = s.brightness_profile || {};
  const upd = hass && hass.states["update.benni_light_policy_update"];
  const version = upd ? (upd.attributes.installed_version || "—") : "—";

  const missing = (f.missing || []);
  const briRows = Object.entries(bri).map(([k, v]) => `
    <div class="kv"><span class="k">${esc(PHASE_LABELS[k] || MODE_LABELS[k] || k)}</span>
      <span class="v">${v != null ? Math.round((v / 255) * 100) + " %" : "—"}
        <span class="subtext">${v != null ? v + "/255" : ""}</span></span></div>`).join("");

  el.innerHTML = `
    <div class="grid cols-2">
      <div class="card">
        <h2><span class="ico">🧱</span>Foundation-Entities</h2>
        <div class="kv"><span class="k">Verfügbar</span>
          <span class="v">${chip(f.ok === f.total ? "ok" : "warn", `${f.ok ?? 0} / ${f.total ?? 0} OK`)}</span></div>
        ${missing.length
          ? `<div style="margin-top:8px"><div class="muted" style="font-size:12px;margin-bottom:6px">Fehlend / unavailable:</div>
             ${missing.map((m) => `<div class="subtext">• ${esc(m)}</div>`).join("")}</div>`
          : `<div style="margin-top:8px">${chip("ok", "alle Quell-Entities OK")}</div>`}
      </div>

      <div class="card">
        <h2><span class="ico">⚡</span>Apply & Status</h2>
        <div class="kv">
          <span class="k">Apply aktiviert<small>aus = Shadow (sicher)</small></span>
          <label class="toggle"><input type="checkbox" id="applyTgl" ${s.apply_enabled ? "checked" : ""}>
            <span class="track"><span class="knob"></span></span></label>
        </div>
        <div class="kv"><span class="k">Version / Commit</span><span class="mono">${esc(version)}</span></div>
        <div class="kv"><span class="k">Look-Quelle</span>
          <span class="v">${chip(store.scenePresetsAvailable() ? "ok" : "error",
            store.scenePresetsAvailable() ? "benni_scene_presets" : "nicht erreichbar")}</span></div>
        <a class="btn" style="display:inline-block;margin-top:10px;text-decoration:none"
           href="/config/integrations/integration/benni_light_policy" target="_top">Integration-Einstellungen öffnen →</a>
        <div class="row-actions">
          <button class="btn primary" id="saveApply">Apply speichern</button>
        </div>
      </div>

      <div class="card" style="grid-column: span 2;">
        <h2><span class="ico">🔆</span>Brightness-Profil <span class="sub">— Helligkeit je Tagesphase/Modus (Override an apply_look)</span></h2>
        <div class="grid cols-2">${briRows || `<p class="muted">Standardprofil aktiv.</p>`}</div>
      </div>
    </div>`;

  const tgl = el.querySelector("#applyTgl");
  const saveApply = el.querySelector("#saveApply");
  if (tgl && saveApply) saveApply.addEventListener("click", async () => {
    try {
      await store.setApplyEnabled(tgl.checked);
      if (store.status) store.status.apply_enabled = tgl.checked;
      ctx.toast(`Apply ${tgl.checked ? "aktiviert" : "deaktiviert"}`);
      ctx.rerender();
    } catch (err) {
      ctx.toast("Fehler: " + (err.message || err));
    }
  });
}
