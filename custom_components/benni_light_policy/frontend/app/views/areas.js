// Tab 5 — Bereiche & Ausnahmen: nur echte Sonderwege, die NICHT über den Look-Kanal laufen.
// Gaming/Musik gehören in „Spezialregeln" (hier nur als Hinweis).
import { esc, chip } from "../styles.js";

const TYPE_META = {
  wake_up: { icon: "⏰", label: "Wake-Up", note: "Raw Targets · direktes light.turn_on" },
  hallway: { icon: "🚪", label: "Flur (R14)", note: "Trigger + Timer + 3× Off" },
  bathroom: { icon: "🛁", label: "Bad (R15)", note: "Vergessensschutz" },
  notification_ring: { icon: "🔔", label: "Notification / Ring", note: "Aqara-Effekt (AAL), kein Look" },
};
const HIDDEN_TYPES = new Set(["gaming", "music"]);

const FIELD_LABEL = {
  wake_up_targets: "Aufsteh-Lampen", hallway_light: "Flurlicht",
  hallway_trigger_entities: "Trigger", bathroom_light: "Bad-Licht",
  bathroom_vibration_entity: "Vibrationssensor", bathroom_timeout_seconds: "Timeout (s)",
  ring_target_entities: "RGB-Ringe", activity_state_entity: "Activity-Quelle",
};

export function render(el, ctx) {
  const { store } = ctx;
  const s = store.status;
  if (!s || s._error) {
    el.innerHTML = `<div class="empty"><span class="ico">⏳</span>Status nicht verfügbar.</div>`;
    return;
  }
  const areas = (s.areas || []).filter((a) => !HIDDEN_TYPES.has(a.type));

  const hardOff = `
    <div class="card">
      <h2><span class="ico">⏻</span>Hard-Off (GROUP_ALL)</h2>
      <p class="muted" style="font-size:13px">Bei <b>sleep</b> oder geschlossenem Lux-Gate: direktes
        <span class="mono">light.turn_off</span> auf alle Wohnzimmer-Lampen.</p>
      <div style="margin-top:8px">${chip("info", "direkter Pfad · kein Look")}</div>
    </div>`;

  const cards = areas.map((a) => {
    const meta = TYPE_META[a.type] || { icon: "📦", label: a.type, note: "" };
    const fields = Object.entries(a.data || {})
      .filter(([k]) => k !== "name" && FIELD_LABEL[k])
      .map(([k, v]) => `<div class="kv"><span class="k">${esc(FIELD_LABEL[k])}</span>
        <span class="subtext">${esc(fmt(v))}</span></div>`).join("");
    return `<div class="card">
      <h2><span class="ico">${meta.icon}</span>${esc(a.title || meta.label)}
        <span class="sub">${esc(meta.note)}</span></h2>
      ${fields || `<p class="muted" style="font-size:13px">Keine Felder.</p>`}
      <div style="margin-top:8px">${chip("info",
        a.type === "notification_ring" ? "Aqara-Effekt · kein Look" : "direkter Pfad · kein Look")}</div>
    </div>`;
  }).join("");

  const hint = `
    <div class="card" style="grid-column: 1 / -1;">
      <p class="muted" style="margin:0;font-size:13px">💡 <b>Gaming und Musik</b> werden unter
        <b>Spezialregeln</b> konfiguriert (sie laufen über den Look-Kanal). Hier nur echte Sonderwege.</p>
    </div>`;

  el.innerHTML = `
    <p class="muted" style="margin:-4px 0 14px">Sonderwege außerhalb des normalen
      <span class="mono">apply_look</span>-Kanals.</p>
    <div class="grid cols-3">${hardOff}${cards}${hint}</div>`;
}

function fmt(v) {
  if (Array.isArray(v)) return v.length ? v.join(", ") : "—";
  return v == null || v === "" ? "—" : String(v);
}
