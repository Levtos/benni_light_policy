# UX-Frontend-Standard (verbindlich)

Der UX-, Technologie- und Designstandard für alle 19 HA-HACS-Integrationen der
Gruppe `Levtos` ist **verbindlich**. Kanonische Quelle ist ausschließlich das
ADR im zentralen Repo `Levtos/control` — der Standard wird hier **nicht kopiert**.

- **ADR (normativ):** https://github.com/Levtos/control/blob/main/docs/adr/0001-ux-frontend-standard.md
- **Entscheidungs-Issue:** https://github.com/Levtos/control/issues/17
- **Einstieg:** https://github.com/Levtos/control/tree/main/docs/ux

Bei UX-/Frontend-Arbeit an dieser Integration zuerst das ADR lesen.

## Kurzform

- Backend bleibt eine eigenständige native HA-Integration.
- Zentrale UX = statisches Frontend-Bundle + dünnes UX-Gateway (primär HA-Ingress;
  Docker/LXC = alternative Verpackung desselben Bundles).
- Frontend-Stack: Svelte 5 · Vite · TypeScript · statische SPA · Bits UI ·
  shadcn-svelte · Tailwind · CSS Custom Properties · Lucide · Svelte-5-Runes.
- Design: „Graphite Dark – semantic accent system", semantische Farb-Tokens.
- Contracts: versioniert/typisiert; REST-Snapshot + WebSocket-Live; Reconnect ⇒ Resync.
- Zustände: loading · ready · empty · stale · degraded · unavailable · reconnecting ·
  offline · error · blocked.

## Abweichungen

Eine Abweichung von Frontend-Framework, Build-System, Komponentenbibliothek,
Design-Token-System, Contract-Modell, zentraler Shell, Authentifizierungsmodell,
Deployment-Grundmodell, Statussemantik oder Farbsemantik benötigt eine **neue
dokumentierte Entscheidungsänderung** (neues `type/decision`-Issue in
`Levtos/control` + Supersede-Vermerk im ADR). Bestehende Regeln dieses Repos
werden ergänzt, nie überschrieben oder entfernt.
