<script lang="ts">
  import Panel from "../lib/ui/Panel.svelte";
  import StatusBadge from "../lib/ui/StatusBadge.svelte";
  import { CANONICAL_PHASES, UX_CONTRACT_VERSION, stateLabel } from "../lib/light-policy/contract";
  import type { LightPolicyStore } from "../lib/light-policy/store.svelte";

  let { store }: { store: LightPolicyStore } = $props();
  const status = $derived(store.status);
  const catalog = $derived(store.catalog);
  const primaryCoverage = $derived(catalog ? store.coverage(catalog.matrix_keys) : []);
  const counts = $derived({
    ready: primaryCoverage.filter((item) => item.status === "ready").length,
    missing: primaryCoverage.filter((item) => item.status === "missing").length,
    invalid: primaryCoverage.filter((item) => item.status === "invalid").length,
    unavailable: primaryCoverage.filter((item) => item.status === "unavailable" || item.status === "stale").length,
  });

  const json = (value: unknown) => JSON.stringify(value, null, 2);
  const rawProfile = $derived(status?.brightness_profile ?? {});
</script>

<div class="lp-grid cols-2">
  <Panel title="Verbindungen und Zustände" eyebrow="Read-only">
    <dl class="lp-detail-list">
      <div class="lp-detail-row"><dt>Host-Verbindung</dt><dd><StatusBadge state={store.connectionState === "connected" ? "ready" : store.connectionState} /></dd></div>
      <div class="lp-detail-row"><dt>Gesamtzustand</dt><dd><StatusBadge state={store.overallState} /></dd></div>
      <div class="lp-detail-row"><dt>Statusdaten</dt><dd><StatusBadge state={store.dataState} /></dd></div>
      <div class="lp-detail-row"><dt>Scene-Presets-Katalog</dt><dd><StatusBadge state={store.looksState} /></dd></div>
      <div class="lp-detail-row"><dt>UX-Vertrag</dt><dd>{UX_CONTRACT_VERSION}</dd></div>
      <div class="lp-detail-row"><dt>Backend-Version</dt><dd>{status?.version ?? "nicht geliefert"}</dd></div>
    </dl>
    <div class="lp-help" style="margin-top: 14px">Statuswerte bedeuten: {stateLabel(store.overallState)}. Bei stale/degraded bleiben die zuletzt vorhandenen Daten sichtbar; die Anzeige stuft fehlende Antworten nicht als „fehlt“ ein.</div>
  </Panel>

  <Panel title="Primäre Matrix-Coverage" eyebrow="Neun Phasen je Thema">
    <div class="lp-grid cols-2">
      <div><div class="lp-kicker">Bereit</div><div class="lp-stat-value">{counts.ready}</div></div>
      <div><div class="lp-kicker">Fehlt / ungültig</div><div class="lp-stat-value">{counts.missing + counts.invalid}</div></div>
    </div>
    <div class="lp-badge-row" style="margin-top: 14px">
      <StatusBadge state="ready" label={`${counts.ready} bereit`} />
      <StatusBadge state="missing" label={`${counts.missing} fehlen`} />
      <StatusBadge state="invalid" label={`${counts.invalid} ungültig`} />
      <StatusBadge state="stale" label={`${counts.unavailable} nicht verifizierbar`} />
    </div>
    <div class="lp-help" style="margin-top: 14px">Geteilte Referenzen sind ein gültiges Ergebnis. Fallback-Zuordnungen werden getrennt markiert und nicht als individuell gepflegt ausgegeben.</div>
  </Panel>
</div>

<div style="margin-top: 16px">
<Panel title="Foundation, Plan und Gate" eyebrow="Backend-Snapshot">
    {#if status}
      <div class="lp-grid cols-3">
        <div><div class="lp-kicker">Foundation</div><div class="lp-stat-value small">{status.foundation.ok ?? 0} / {status.foundation.total ?? 0}</div></div>
        <div><div class="lp-kicker">Day-State</div><div class="lp-stat-value small">{status.day_state ?? "–"}</div></div>
        <div><div class="lp-kicker">Activity</div><div class="lp-stat-value small">{status.activity ?? "–"}</div></div>
      </div>
      <div class="lp-divider"></div>
      <div class="lp-grid cols-2">
        <div><div class="lp-kicker">Plan</div><pre class="lp-note">{json(status.plan)}</pre></div>
        <div><div class="lp-kicker">Gate</div><pre class="lp-note">{json(status.gate)}</pre></div>
      </div>
    {:else}
      <div class="lp-empty">Kein Status-Snapshot verfügbar.</div>
    {/if}
</Panel>
</div>

<Panel title="Helligkeitsprofil · Rohdiagnose" eyebrow="Technische Werte" description="0..255 ist absichtlich nur hier sichtbar; die Bedienansicht arbeitet in Prozent.">
    {#if Object.keys(rawProfile).length}
      <div class="lp-table-wrap">
        <table class="lp-table" style="min-width: 420px">
          <thead><tr><th>Key</th><th>Raw 0..255</th><th>Einordnung</th></tr></thead>
          <tbody>
            {#each Object.entries(rawProfile).sort(([a], [b]) => a.localeCompare(b)) as [key, raw] (key)}
              <tr><td class="technical-key">{key}</td><td>{raw}</td><td class="lp-help">{CANONICAL_PHASES.includes(key as (typeof CANONICAL_PHASES)[number]) ? "Standardphase" : "Override oder Legacy-Key"}</td></tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else}
      <div class="lp-empty">Kein Helligkeitsprofil geliefert.</div>
    {/if}
</Panel>

<Panel title="Contract-Details" eyebrow="Keine Schreibaktionen">
    <details class="lp-disclosure" open>
      <summary>Katalog und Legacy-Phasen</summary>
      <div class="lp-disclosure-content"><pre class="lp-note">{json(catalog)}</pre></div>
    </details>
    {#if status?.foundation.missing?.length}
      <details class="lp-disclosure" style="margin-top: 12px">
        <summary>Fehlende Foundation-Eingänge</summary>
        <div class="lp-disclosure-content"><pre class="lp-note">{json(status.foundation.missing)}</pre></div>
      </details>
    {/if}
    {#if status?.subentry_rules?.length}
      <details class="lp-disclosure" style="margin-top: 12px">
        <summary>Bestehende Subentry-Regeln</summary>
        <div class="lp-disclosure-content"><pre class="lp-note">{json(status.subentry_rules)}</pre></div>
      </details>
    {/if}
</Panel>
