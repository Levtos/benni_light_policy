<script lang="ts">
  import { AlertTriangle, CircleAlert, Info, LoaderCircle, WifiOff } from "@lucide/svelte";
  import type { UiState } from "../light-policy/types";

  let { state, message, title }: { state: UiState; message: string; title?: string } = $props();

  const iconFor = (value: UiState) => {
    if (value === "loading" || value === "reconnecting") return LoaderCircle;
    if (value === "offline") return WifiOff;
    if (value === "error" || value === "blocked") return CircleAlert;
    if (value === "stale" || value === "degraded") return AlertTriangle;
    return Info;
  };
  const Icon = $derived(iconFor(state));
</script>

<div class="lp-state-banner {state}" role="status" aria-live="polite">
  <span class:lp-spin={state === "loading" || state === "reconnecting"}><Icon size={18} strokeWidth={2} /></span>
  <div>
    {#if title}<strong>{title}</strong>{/if}
    <div>{message}</div>
  </div>
</div>
