<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    title,
    eyebrow,
    description,
    actions,
    children,
    compact = false,
  }: {
    title: string;
    eyebrow?: string;
    description?: string;
    actions?: Snippet;
    children?: Snippet;
    compact?: boolean;
  } = $props();
</script>

<section class:compact class="lp-panel">
  <header>
    <div>
      {#if eyebrow}<div class="lp-kicker">{eyebrow}</div>{/if}
      <h2>{title}</h2>
      {#if description}<p class="lp-help">{description}</p>{/if}
    </div>
    {#if actions}<div class="lp-page-actions">{@render actions()}</div>{/if}
  </header>
  {@render children?.()}
</section>
