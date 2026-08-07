import { mount, unmount } from "svelte";
import App from "./App.svelte";
import { bridge } from "./lib/light-policy/bridge.svelte";
import styles from "./styles/global.css?inline";

const PORTAL_STYLES = `
.lp-tooltip {
  z-index: 1000;
  max-width: 280px;
  padding: 8px 10px;
  color: #eef2f6;
  font: 0.75rem/1.45 Inter, ui-sans-serif, system-ui, sans-serif;
  background: #252b34;
  border: 1px solid #4b5563;
  border-radius: 7px;
  box-shadow: 0 16px 45px rgb(0 0 0 / 22%);
}`;

function ensureStyle(root: Document | ShadowRoot, id: string, content: string): void {
  if (root.querySelector(`style[data-${id}]`)) return;
  const element = document.createElement("style");
  element.setAttribute(`data-${id}`, "true");
  element.textContent = content;
  if (root instanceof Document) root.head.appendChild(element);
  else root.appendChild(element);
}

class BlpApp extends HTMLElement {
  private mountTarget: HTMLDivElement | null = null;
  private app: ReturnType<typeof mount> | null = null;
  private hostHass: unknown = null;

  constructor() {
    super();
    const root = this.attachShadow({ mode: "open" });
    ensureStyle(root, "blp-ux-shadow", styles);
    this.mountTarget = document.createElement("div");
    root.appendChild(this.mountTarget);
  }

  set hass(value: unknown) {
    this.hostHass = value;
    bridge.hass = value as typeof bridge.hass;
  }

  get hass(): unknown {
    return this.hostHass;
  }

  connectedCallback(): void {
    if (!this.mountTarget || this.app) return;
    ensureStyle(document, "blp-ux-portal", PORTAL_STYLES);
    this.app = mount(App, { target: this.mountTarget });
  }

  disconnectedCallback(): void {
    if (!this.app) return;
    unmount(this.app);
    this.app = null;
  }
}

if (!customElements.get("blp-app")) customElements.define("blp-app", BlpApp);
