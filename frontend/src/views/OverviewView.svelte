<script lang="ts">
  import { Check, LockKeyhole, RefreshCw } from "@lucide/svelte";
  import CoverageBadge from "../lib/ui/CoverageBadge.svelte";
  import Panel from "../lib/ui/Panel.svelte";
  import StateBanner from "../lib/ui/StateBanner.svelte";
  import StatusBadge from "../lib/ui/StatusBadge.svelte";
  import { brightnessProvenance, keyLabel } from "../lib/light-policy/contract";
  import type { LightPolicyStore } from "../lib/light-policy/store.svelte";

  let { store }: { store: LightPolicyStore } = $props();

  const desiredCoverage = $derived(
    store.status?.desired_policy_key ? store.coverage([store.status.desired_policy_key])[0] : null,
  );
  const desiredKey = $derived(store.status?.desired_policy_key ?? "nicht vorhanden");
  const brightness = $derived(
    store.status?.desired_policy_key
      ? brightnessProvenance(store.status.desired_policy_key, store.status.brightness_profile)
      : { raw: null, percent: null, source: "unavailable" as const },
  );
  const foundation = $derived(store.status?.foundation);
  const plan = $derived(store.status?.plan);
  const applyAllowed = $derived(Boolean(store.status?.apply_enabled && plan?.apply_allowed));
</script>

{#if !store.status || !store.catalog}
  <div class="lp-empty">Die bestehende Light-Policy-Status- und Katalogantwort ist noch nicht verfügbar.</div>
{:else}
  <div class="lp-grid cols-3">
    <Panel title="Soll-Zustand" eyebrow="Policy-Auswahl" compact>
      <div class="lp-stat-value small">{keyLabel(desiredKey)}</div>
      <div class="lp-meta">Technischer Key: {desiredKey}</div>
      <div class="lp-meta">Look-Ref: {store.status.desired_look_ref ?? desiredCoverage?.ref ?? "nicht aufgelöst"}</div>
      {#if desiredCoverage}<div style="margin-top: 12px"><CoverageBadge coverage={desiredCoverage} /></div>{/if}
    </Panel>

    <Panel title="Effektive Helligkeit" eyebrow="Policy-Profil" compact>
      {#if brightness.percent !== null}
        <div class="lp-stat-value">{brightness.percent} %</div>
        <div class="lp-meta">{brightness.source === "standard" ? "Standardwert" : "Expliziter Override"}</div>
      {:else}
        <div class="lp-stat-value small">Nicht verfügbar</div>
        <div class="lp-meta">Für diesen Soll-Key liefert der bestehende Vertrag keinen Wert.</div>
      {/if}
    </Panel>

    <Panel title="Apply-Gate" eyebrow="Sicherheitsgrenze" compact>
      <div class="lp-stat-value small">{applyAllowed ? "freigegeben" : "blockiert / Shadow"}</div>
      <div class="lp-meta">{plan?.reason ?? "Kein Plan-Grund geliefert"}</div>
      <div style="margin-top: 12px"><StatusBadge state={applyAllowed ? "success" : "blocked"} label={applyAllowed ? "Apply erlaubt" : "Apply nicht erlaubt"} /></div>
    </Panel>
  </div>

  <div class="lp-grid cols-2" style="margin-top: 16px">
    <Panel title="Verifizierungsgrenze" eyebrow="Wichtig">
      <StateBanner
        state="degraded"
        title="Tatsächlich laufender Look: nicht verifiziert"
        message="Der bestehende Backend-Vertrag liefert keine applied_look- oder Ack-Quelle. Ein gewünschter Look bzw. ein HA-Switch ist deshalb kein Ausführungsbeleg."
      />
      <div class="lp-note">Diese Ansicht behauptet keine Live-Ausführung. Shadow, Merge/Release, HA-Reload und Live Verified bleiben getrennte Gates.</div>
    </Panel>

    <Panel title="Foundation und Kontext" eyebrow="Read-only">
      <dl class="lp-detail-list">
        <div class="lp-detail-row"><dt>Day-State</dt><dd>{store.status.day_state ?? "nicht geliefert"}</dd></div>
        <div class="lp-detail-row"><dt>Activity</dt><dd>{store.status.activity ?? "nicht geliefert"}</dd></div>
        <div class="lp-detail-row"><dt>Foundation</dt><dd>{foundation?.ok ?? 0} / {foundation?.total ?? 0}</dd></div>
        <div class="lp-detail-row"><dt>Lux-Gate</dt><dd><StatusBadge state={store.status.gate.lux_gate_on ? "success" : "info"} label={store.status.gate.lux_gate_on ? "offen" : "geschlossen"} /></dd></div>
        <div class="lp-detail-row"><dt>Manual-Off</dt><dd><StatusBadge state={store.status.manual_off ? "warning" : "success"} label={store.status.manual_off ? "aktiv" : "aus"} /></dd></div>
      </dl>
      {#if foundation?.missing?.length}
        <div class="lp-note" style="margin-top: 14px">Fehlende Eingänge: {foundation.missing.join(", ")}</div>
      {/if}
    </Panel>
  </div>

  <Panel title="Sichere bestehende Aktion" eyebrow="Autorisierter Mutationspfad" description="Die einzige direkte Aktion dieser Übersicht ist der vorhandene Apply-Schalter. Es wird kein neuer Ausführungs- oder Event-Vertrag angelegt." compact={false}>
    <div class="lp-field-row">
      <div>
        <strong>Light Policy Apply</strong>
        <div class="lp-help">Aktuell: {store.status.apply_enabled ? "aktiv" : "Shadow / deaktiviert"}</div>
      </div>
      <button class="lp-button {store.status.apply_enabled ? "danger" : "primary"}" type="button" disabled={store.mutation.state === "pending"} onclick={() => store.setApplyEnabled(!store.status?.apply_enabled)}>
        {#if store.mutation.state === "pending"}<RefreshCw class="lp-spin" size={17} />{:else if store.status.apply_enabled}<LockKeyhole size={17} />{:else}<Check size={17} />{/if}
        {store.status.apply_enabled ? "In Shadow setzen" : "Apply aktivieren"}
      </button>
    </div>
    <div class="lp-help" style="margin-top: 13px">Home Assistant bestätigt die bestehende Admin-Autorisierung. Bei fehlender Berechtigung bleibt die Änderung blockiert und wird nicht lokal simuliert.</div>
  </Panel>

  {#if plan?.blockers?.length}
    <Panel title="Aktuelle Blocker" eyebrow="Plan-Diagnose" compact>
      <ul class="lp-help">
        {#each plan.blockers as blocker (blocker)}<li>{blocker}</li>{/each}
      </ul>
    </Panel>
  {/if}
{/if}
