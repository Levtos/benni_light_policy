// Tab 3 — Tagesphasen-Matrix: Themes (Zeilen) × Phasen (Spalten) → Look.
// Kompakte, klickbare Zellen (Status + kurzer Look-Name); Look-Auswahl per Modal.
// Helligkeit kommt aus dem Tagesphasen-Profil und wird getrennt vom Look gezeigt.
import { esc, chip } from "../styles.js";
import { PHASE_LABELS, THEME_LABELS } from "../store.js";
import { lookSelectHTML, coverageCellHTML } from "../components/look-select.js";

export function render(el, ctx) {
  const { store } = ctx;
  const cat = store.catalog;
  if (!cat || cat._error) {
    el.innerHTML = `<div class="empty"><span class="ico">⏳</span>Katalog nicht verfügbar.</div>`;
    return;
  }
  const themes = cat.themes || [];
  const phases = cat.phases || [];
  const looksOk = store.scenePresetsAvailable();
  const bri = (store.status && store.status.brightness_profile) || {};

  const head = `<tr><th>Theme \\ Phase</th>${phases.map((p) =>
    `<th class="tcell">${esc(PHASE_LABELS[p] || p)}<div class="ph">${
      bri[p] != null ? Math.round((bri[p] / 255) * 100) + " %" : ""}</div></th>`).join("")}</tr>`;

  const body = themes.map((t) => {
    const cells = phases.map((p) => {
      const key = `${t}_${p}`;
      return `<td>${coverageCellHTML(key, store.coverage(key))}</td>`;
    }).join("");
    return `<tr><td><b>${esc(THEME_LABELS[t] || t)}</b></td>${cells}</tr>`;
  }).join("");

  el.innerHTML = `
    <div class="card matrix">
      <h2><span class="ico">▦</span>Tagesphasen-Matrix
        <span class="sub">— Zelle anklicken, um einen Look zu wählen; Helligkeit kommt separat aus dem Profil</span></h2>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
        ${chip("ok", "vorhanden")} ${chip("info", "Fallback (Key = Look-Ref)")}
        ${chip("warn", "fehlt")} ${chip("error", "ungültig")}
      </div>
      <table><thead>${head}</thead><tbody>${body}</tbody></table>
      <p class="muted" style="font-size:12px;margin-top:10px">
        Mehrere Zellen dürfen denselben Look nutzen. „Fallback" heißt: kein Mapping gesetzt — der
        Key-Name wird direkt als Look-Ref versucht.</p>
    </div>
    <div id="mx-modal"></div>`;

  const openModal = (key) => {
    const t = key.split("_").slice(0, -2).join("_") || key.split("_")[0];
    const p = key.split("_").slice(-2).join("_");
    const label = `${THEME_LABELS[t] || t} · ${PHASE_LABELS[p] || p}`;
    const cur = store.lookMap[key] || "";
    const host = el.querySelector("#mx-modal");
    host.innerHTML = `
      <div class="modal-bg">
        <div class="modal">
          <h3>${esc(label)}</h3>
          <div class="subtext" style="margin-bottom:10px">${esc(key)}</div>
          ${lookSelectHTML(cur, looksOk ? store.looks : null, { id: "mx-pick" })}
          <div class="row">
            <button class="btn" data-act="cancel">Abbrechen</button>
            <button class="btn" data-act="clear">Kein Mapping</button>
            <button class="btn primary" data-act="save">Speichern</button>
          </div>
        </div>
      </div>`;
    const close = () => (host.innerHTML = "");
    host.querySelector(".modal-bg").addEventListener("click", (e) => {
      if (e.target.classList.contains("modal-bg")) close();
    });
    host.querySelector('[data-act="cancel"]').addEventListener("click", close);
    const save = async (value) => {
      const map = { ...store.lookMap };
      if (value) map[key] = value; else delete map[key];
      close();
      try {
        await store.setLookMap(map);
        ctx.toast(value ? "Look gespeichert" : "Mapping entfernt");
        setTimeout(ctx.refresh, 500);
      } catch (err) { ctx.toast("Fehler: " + (err.message || err)); }
    };
    host.querySelector('[data-act="save"]').addEventListener("click", () =>
      save((host.querySelector("#mx-pick").value || "").trim()));
    host.querySelector('[data-act="clear"]').addEventListener("click", () => save(""));
  };

  el.querySelectorAll(".mcell").forEach((cell) =>
    cell.addEventListener("click", () => openModal(cell.dataset.key)));
}
