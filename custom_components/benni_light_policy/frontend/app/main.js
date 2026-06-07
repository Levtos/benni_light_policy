// Light-Policy-Panel — Shell, Sidebar-Navigation, Router, Live-Refresh.
import { CSS, chip, esc } from "./styles.js";
import { Store } from "./store.js";
import * as overview from "./views/overview.js";
import * as lookMapping from "./views/look-mapping.js";
import * as matrix from "./views/matrix.js";
import * as brightness from "./views/brightness.js";
import * as special from "./views/special-rules.js";
import * as areas from "./views/areas.js";
import * as diagnostics from "./views/diagnostics.js";
import * as system from "./views/system.js";

const NAV = [
  { id: "overview", label: "Übersicht", icon: "🏠", view: overview },
  { id: "look-mapping", label: "Look-Mapping", icon: "🎚", view: lookMapping },
  { id: "matrix", label: "Tagesphasen-Matrix", icon: "▦", view: matrix },
  { id: "brightness", label: "Helligkeit", icon: "🔆", view: brightness },
  { id: "special", label: "Spezialregeln", icon: "🎮", view: special },
  { id: "areas", label: "Bereiche & Ausnahmen", icon: "📐", view: areas },
  { id: "diagnostics", label: "Diagnose", icon: "🩺", view: diagnostics },
  { id: "system", label: "System", icon: "⚙️", view: system },
];

class BlpApp extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._store = new Store();
    this._view = "overview";
    this._booted = false;
    this._hass = null;
  }

  set hass(v) {
    this._hass = v;
    this._store.hass = v;
    if (!this._booted) {
      this._boot();
    }
  }
  get hass() { return this._hass; }

  connectedCallback() {}
  disconnectedCallback() {}

  async _boot() {
    if (this._booted) return;
    this._booted = true;
    this._renderShell();
    await this.refresh();
  }

  async refresh() {
    try {
      await this._store.refresh();
    } catch (e) {
      /* transient */
    }
    this._renderLive();
  }

  _ctx() {
    return {
      store: this._store,
      hass: this._hass,
      navigate: (id) => this._navigate(id),
      refresh: () => this.refresh(),
      rerender: () => this._renderView(),
      toast: (m) => this._toast(m),
    };
  }

  _navigate(id) {
    this._view = id;
    this.shadowRoot.querySelectorAll(".nav button").forEach((b) =>
      b.classList.toggle("active", b.dataset.id === id));
    this._renderView();
  }

  _renderShell() {
    const navHtml = NAV.map((n) =>
      `<button data-id="${n.id}" class="${n.id === this._view ? "active" : ""}">
         <span class="ico">${n.icon}</span>${n.label}</button>`).join("");
    this.shadowRoot.innerHTML = `
      <style>${CSS}</style>
      <div class="app">
        <aside class="sidebar">
          <div class="brand">
            <div class="logo">💡</div>
            <div><b>Benni Light Policy</b><small>Intelligente Lichtsteuerung</small></div>
          </div>
          <nav class="nav">${navHtml}</nav>
          <div class="sb-foot" id="sbfoot">benni_light_policy</div>
        </aside>
        <main class="main">
          <div class="head">
            <div><h1 id="vtitle">Übersicht</h1><p id="vsub"></p></div>
            <div class="head-actions">
              <button class="btn" id="manualRefresh">Aktualisieren</button>
              <div class="chips" id="headchips"></div>
            </div>
          </div>
          <div id="content"></div>
        </main>
      </div>`;
    this.shadowRoot.querySelectorAll(".nav button").forEach((b) =>
      b.addEventListener("click", () => this._navigate(b.dataset.id)));
    this.shadowRoot.getElementById("manualRefresh").addEventListener("click", () => this.refresh());
  }

  _renderLive() {
    if (!this._booted) return;
    this._renderHead();
    this._renderView();
  }

  _renderHead() {
    const s = this._store.status;
    const chips = this.shadowRoot.getElementById("headchips");
    if (!chips) return;
    if (!s || s._error) {
      chips.innerHTML = chip("warn", "lädt …");
      return;
    }
    const f = s.foundation || {};
    const gate = s.gate || {};
    const parts = [
      chip(f.total && f.ok === f.total ? "ok" : "warn",
        `System ${f.ok ?? 0}/${f.total ?? 0}`),
      chip(s.apply_enabled ? "ok" : "info", s.apply_enabled ? "Apply aktiv" : "Apply Shadow"),
      chip(gate.lux_gate_on ? "ok" : "info", gate.lux_gate_on ? "Lux-Gate offen" : "Lux-Gate zu"),
      chip(s.manual_off ? "warn" : "ok", s.manual_off ? "Manual-Off aktiv" : "Manual-Off aus"),
    ];
    chips.innerHTML = parts.join("");
  }

  _renderView() {
    const nav = NAV.find((n) => n.id === this._view) || NAV[0];
    const title = this.shadowRoot.getElementById("vtitle");
    const content = this.shadowRoot.getElementById("content");
    if (!content) return;
    title.textContent = nav.label;
    const foot = this.shadowRoot.getElementById("sbfoot");
    const upd = this._hass && this._hass.states["update.benni_light_policy_update"];
    if (foot) foot.textContent = "benni_light_policy" + (upd ? " · " + (upd.attributes.installed_version || "") : "");
    try {
      nav.view.render(content, this._ctx());
    } catch (e) {
      content.innerHTML = `<div class="empty"><span class="ico">⚠️</span>Render-Fehler: ${esc(e.message)}</div>`;
    }
  }

  _toast(msg) {
    const t = document.createElement("div");
    t.className = "toast";
    t.textContent = msg;
    this.shadowRoot.appendChild(t);
    setTimeout(() => t.remove(), 2600);
  }
}

if (!customElements.get("blp-app")) {
  customElements.define("blp-app", BlpApp);
}
