// Dracula-inspiriertes Dark-Theme + gemeinsame UI-Helfer für das Light-Policy-Panel.

export const CSS = `
:host, * { box-sizing: border-box; }
:host {
  --bg: #1a1b26;
  --bg2: #21222c;
  --card: #282a36;
  --card2: #2f3240;
  --line: #3a3d4d;
  --fg: #f8f8f2;
  --muted: #9aa0b4;
  --faint: #6b7089;
  --purple: #bd93f9;
  --cyan: #8be9fd;
  --green: #50fa7b;
  --yellow: #f1fa8c;
  --orange: #ffb86c;
  --red: #ff5555;
  --pink: #ff79c6;
  font-family: -apple-system, "Segoe UI", Roboto, Ubuntu, sans-serif;
  color: var(--fg);
}
.app { display: grid; grid-template-columns: 248px 1fr; min-height: 100vh; background: var(--bg); }
.sidebar { background: var(--bg2); border-right: 1px solid var(--line); padding: 18px 12px; display: flex; flex-direction: column; gap: 4px; }
.brand { display: flex; align-items: center; gap: 12px; padding: 6px 10px 18px; }
.brand .logo { width: 38px; height: 38px; border-radius: 11px; background: linear-gradient(135deg, var(--purple), var(--cyan)); display: grid; place-items: center; font-size: 20px; }
.brand b { font-size: 16px; display: block; }
.brand small { color: var(--muted); font-size: 11px; }
.nav { display: flex; flex-direction: column; gap: 2px; }
.nav button { display: flex; align-items: center; gap: 11px; background: none; border: 0; color: var(--muted); text-align: left;
  padding: 11px 12px; border-radius: 10px; cursor: pointer; font-size: 14px; width: 100%; }
.nav button:hover { background: var(--card); color: var(--fg); }
.nav button.active { background: linear-gradient(90deg, rgba(189,147,249,.22), rgba(139,233,253,.06)); color: var(--fg); box-shadow: inset 2px 0 0 var(--purple); }
.nav .ico { width: 18px; text-align: center; }
.sb-foot { margin-top: auto; padding: 10px; color: var(--faint); font-size: 11px; border-top: 1px solid var(--line); }

.main { padding: 22px 26px; overflow: auto; }
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 18px; flex-wrap: wrap; }
.head h1 { font-size: 24px; margin: 0; color: var(--purple); }
.head p { margin: 3px 0 0; color: var(--muted); font-size: 13px; }
.head .chips { display: flex; gap: 8px; flex-wrap: wrap; }
.head-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }

.grid { display: grid; gap: 14px; }
.cols-2 { grid-template-columns: repeat(2, 1fr); }
.cols-3 { grid-template-columns: repeat(3, 1fr); }
.cols-4 { grid-template-columns: repeat(4, 1fr); }
@media (max-width: 1100px) { .cols-3, .cols-4 { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 720px) { .app { grid-template-columns: 1fr; } .cols-2, .cols-3, .cols-4 { grid-template-columns: 1fr; } }

.card { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 16px; }
.card h2 { font-size: 14px; margin: 0 0 12px; display: flex; align-items: center; gap: 8px; }
.card h2 .ico { color: var(--cyan); }
.card .sub { color: var(--muted); font-size: 12px; font-weight: 400; }

.kv { display: flex; justify-content: space-between; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--line); }
.kv:last-child { border-bottom: 0; }
.kv .k { color: var(--muted); font-size: 13px; }
.kv .v { font-weight: 600; font-size: 14px; }
.kv .k small { display: block; color: var(--faint); font-size: 11px; font-weight: 400; }

.tile { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 14px 16px; }
.tile .lbl { color: var(--muted); font-size: 12px; }
.tile .big { font-size: 18px; font-weight: 700; margin-top: 4px; }
.tile .big.purple { color: var(--purple); }

.chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600;
  border: 1px solid var(--line); background: var(--card2); color: var(--fg); white-space: nowrap; }
.chip .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--faint); }
.chip.ok { color: var(--green); border-color: rgba(80,250,123,.3); } .chip.ok .dot { background: var(--green); }
.chip.warn { color: var(--yellow); border-color: rgba(241,250,140,.3); } .chip.warn .dot { background: var(--yellow); }
.chip.error { color: var(--red); border-color: rgba(255,85,85,.35); } .chip.error .dot { background: var(--red); }
.chip.info { color: var(--cyan); border-color: rgba(139,233,253,.3); } .chip.info .dot { background: var(--cyan); }

.mono { font-family: ui-monospace, "Cascadia Code", monospace; font-size: 12px; color: var(--cyan); }
.subtext { color: var(--faint); font-size: 11px; font-family: ui-monospace, monospace; }
.muted { color: var(--muted); }

button.btn { background: var(--card2); color: var(--fg); border: 1px solid var(--line); border-radius: 9px; padding: 8px 13px; cursor: pointer; font-size: 13px; }
button.btn:hover { border-color: var(--purple); }
button.btn.primary { background: linear-gradient(135deg, var(--purple), #9d7cf0); border-color: transparent; color: #1a1b26; font-weight: 600; }
select, input[type=text], input[type=number] { background: var(--bg2); color: var(--fg); border: 1px solid var(--line); border-radius: 8px; padding: 7px 9px; font-size: 13px; width: 100%; }
select:focus, input:focus { outline: 0; border-color: var(--purple); }

table { width: 100%; border-collapse: collapse; }
th, td { padding: 7px 9px; text-align: left; font-size: 13px; border-bottom: 1px solid var(--line); }
th { color: var(--muted); font-weight: 600; font-size: 12px; }

.matrix { overflow-x: auto; }
.matrix table { min-width: 720px; }
.matrix td.cell { text-align: center; cursor: pointer; }
.matrix td.cell:hover { background: var(--card2); }
.matrix .ph { font-size: 11px; color: var(--muted); }

.toggle { position: relative; width: 42px; height: 24px; flex: 0 0 auto; }
.toggle input { display: none; }
.toggle .track { position: absolute; inset: 0; background: var(--card2); border: 1px solid var(--line); border-radius: 999px; transition: .15s; }
.toggle .knob { position: absolute; top: 3px; left: 3px; width: 18px; height: 18px; border-radius: 50%; background: var(--faint); transition: .15s; }
.toggle input:checked + .track { background: rgba(189,147,249,.3); border-color: var(--purple); }
.toggle input:checked + .track .knob { left: 21px; background: var(--purple); }

.empty { text-align: center; color: var(--muted); padding: 26px; border: 1px dashed var(--line); border-radius: 12px; }
.empty .ico { font-size: 28px; display: block; margin-bottom: 8px; }

.toast { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background: var(--card); border: 1px solid var(--purple);
  color: var(--fg); padding: 10px 18px; border-radius: 10px; font-size: 13px; box-shadow: 0 8px 30px rgba(0,0,0,.4); z-index: 50; }

.donut { display: grid; place-items: center; }
.legend { display: flex; flex-direction: column; gap: 6px; font-size: 13px; }
.legend span.sw { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 7px; }

/* Kompakte Matrix-Zellen (statt 56 Dropdowns) */
.matrix table { min-width: 880px; }
.matrix th, .matrix td { padding: 5px 6px; }
.mcell { display: flex; flex-direction: column; gap: 2px; align-items: stretch; min-width: 92px;
  border: 1px solid var(--line); border-radius: 8px; padding: 6px 8px; cursor: pointer; background: var(--card); transition: .12s; }
.mcell:hover { border-color: var(--purple); background: var(--card2); }
.mcell .nm { font-size: 12px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mcell .st { display: inline-flex; align-items: center; gap: 5px; font-size: 11px; }
.mcell .st .dot { width: 7px; height: 7px; border-radius: 50%; }
.mcell.ok { } .mcell.fallback { border-style: dashed; }
.dot.ok { background: var(--green); } .dot.fallback { background: var(--faint); }
.dot.warn { background: var(--yellow); } .dot.error { background: var(--red); }
.tcell .ph { font-size: 10px; color: var(--faint); }
.cell-bri { margin-top: 4px; text-align: center; font-size: 11px; color: var(--cyan); }
.cell-bri.inherited { color: var(--faint); }

/* Inline-Look-Select pro Matrix-Zelle (ersetzt den früheren Modal) */
.mx-cell { vertical-align: top; min-width: 150px; }
.mx-cell .look-select, .mx-cell .look-input { width: 100%; font-size: 12px; padding: 5px 6px; }
.mx-cell.fallback .look-select { border-style: dashed; }
.mx-meta { display: flex; align-items: center; justify-content: space-between; gap: 6px; margin-top: 4px; }
.mx-meta .cell-bri { margin-top: 0; }

/* Modal / Popover für Look-Auswahl */
.modal-bg { position: fixed; inset: 0; background: rgba(10,11,18,.62); display: grid; place-items: center; z-index: 60; }
.modal { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 18px; width: min(440px, 92vw);
  box-shadow: 0 18px 60px rgba(0,0,0,.5); }
.modal h3 { margin: 0 0 4px; font-size: 15px; }
.modal .row { display: flex; gap: 8px; margin-top: 14px; justify-content: flex-end; }
.row-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px; }
.brightness-table { min-width: 980px; }
.brightness-table input { min-width: 72px; }
`;

// Status-Chip (ok/warn/error/info) als HTML-String.
export function chip(status, label) {
  const s = ["ok", "warn", "error", "info"].includes(status) ? status : "";
  return `<span class="chip ${s}"><span class="dot"></span>${esc(label)}</span>`;
}

export function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
