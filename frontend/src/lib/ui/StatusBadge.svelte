<script lang="ts">
  import { AlertTriangle, Check, CircleAlert, CircleDashed, Info, LoaderCircle } from "@lucide/svelte";
  import type { UiState } from "../light-policy/types";
  import { stateLabel } from "../light-policy/contract";

  let { state, label }: { state: UiState | string; label?: string } = $props();

  const iconFor = (value: string) => {
    if (value === "ready" || value === "success") return Check;
    if (value === "loading" || value === "reconnecting" || value === "pending") return LoaderCircle;
    if (value === "error" || value === "invalid" || value === "blocked") return CircleAlert;
    if (value === "stale" || value === "degraded" || value === "warning") return AlertTriangle;
    if (value === "info" || value === "fallback") return Info;
    return CircleDashed;
  };

  const text = $derived(label ?? (state in {
    loading: true,
    ready: true,
    empty: true,
    stale: true,
    degraded: true,
    unavailable: true,
    reconnecting: true,
    offline: true,
    error: true,
    blocked: true,
  } ? stateLabel(state as UiState) : state));
  const Icon = $derived(iconFor(state));
</script>

<span class="lp-badge {state}"><Icon size={14} strokeWidth={2} />{text}</span>
