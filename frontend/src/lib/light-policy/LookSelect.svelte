<script lang="ts">
  import type { Look, UiState } from "./types";
  import { lookLabel, lookRef } from "./contract";

  let {
    value,
    looks,
    looksState,
    disabled = false,
    onchange,
  }: {
    value: string;
    looks: Look[];
    looksState: UiState;
    disabled?: boolean;
    onchange: (value: string) => void;
  } = $props();

  const options = $derived(
    looks
      .map((look) => ({ value: lookRef(look), label: lookLabel(look) }))
      .filter((item): item is { value: string; label: string } => Boolean(item.value)),
  );
</script>

{#if looksState === "ready" && options.length}
  <select
    class="lp-select"
    aria-label="Look-Referenz"
    value={value}
    {disabled}
    onchange={(event) => onchange((event.currentTarget as HTMLSelectElement).value)}
  >
    <option value="">Nicht zugeordnet</option>
    {#each options as option (option.value)}
      <option value={option.value}>{option.label} · {option.value}</option>
    {/each}
    {#if value && !options.some((option) => option.value === value)}
      <option value={value}>{value} · nicht im Katalog</option>
    {/if}
  </select>
{:else}
  <input
    class="lp-input"
    aria-label="Look-Referenz"
    placeholder="Look-Ref (Slug oder Name)"
    value={value}
    {disabled}
    onchange={(event) => onchange((event.currentTarget as HTMLInputElement).value)}
  />
{/if}
