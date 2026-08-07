<script lang="ts">
  import { Tooltip } from "bits-ui";
  import type { Component } from "svelte";

  let {
    label,
    icon: Icon,
    onclick,
    disabled = false,
  }: {
    label: string;
    icon: Component<{ size?: number; strokeWidth?: number }>;
    onclick?: () => void;
    disabled?: boolean;
  } = $props();
</script>

<Tooltip.Provider>
  <Tooltip.Root>
    <Tooltip.Trigger class="lp-icon-button" {disabled} aria-label={label} {onclick}>
      <Icon size={18} strokeWidth={2} />
    </Tooltip.Trigger>
    <Tooltip.Content class="lp-tooltip" side="bottom">{label}</Tooltip.Content>
  </Tooltip.Root>
</Tooltip.Provider>
