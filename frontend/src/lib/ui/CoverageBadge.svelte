<script lang="ts">
  import StatusBadge from "./StatusBadge.svelte";
  import type { Coverage } from "../light-policy/types";

  let { coverage }: { coverage: Coverage } = $props();

  const labelFor = (value: Coverage["status"]) => ({
    ready: "bereit",
    missing: "fehlt",
    invalid: "ungültig",
    unavailable: "nicht verfügbar",
    stale: "veraltet",
  })[value];
</script>

<div class="lp-badge-row">
  <StatusBadge state={coverage.status} label={labelFor(coverage.status)} />
  {#if coverage.assignment === "fallback"}
    <StatusBadge state="fallback" label="Standard-Zuordnung" />
  {/if}
  {#if coverage.isShared}
    <StatusBadge state="info" label="geteilt" />
  {/if}
</div>
