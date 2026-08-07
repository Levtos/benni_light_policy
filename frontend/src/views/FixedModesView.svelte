<script lang="ts">
  import { RotateCcw, Save } from "@lucide/svelte";
  import CoverageBadge from "../lib/ui/CoverageBadge.svelte";
  import LookSelect from "../lib/light-policy/LookSelect.svelte";
  import Panel from "../lib/ui/Panel.svelte";
  import { MODE_LABELS } from "../lib/light-policy/contract";
  import { cloneStringMap } from "../lib/light-policy/store.svelte";
  import type { LightPolicyStore } from "../lib/light-policy/store.svelte";

  let { store }: { store: LightPolicyStore } = $props();
  let draft = $state<Record<string, string>>({});
  let initialized = $state(false);
  let serverSignature = "";
  const modes = $derived(store.catalog?.fixed_modes ?? []);
  const signature = (map: Record<string, string>) => JSON.stringify(Object.entries(map).sort(([a], [b]) => a.localeCompare(b)));
  const dirty = $derived(signature(draft) !== signature(Object.fromEntries(modes.flatMap((mode) => store.lookMap[mode] ? [[mode, store.lookMap[mode]]] : []))));

  $effect(() => {
    const incoming = Object.fromEntries(modes.flatMap((mode) => store.lookMap[mode] ? [[mode, store.lookMap[mode]]] : []));
    const nextSignature = signature(incoming);
    if (!initialized || (!dirty && nextSignature !== serverSignature)) {
      draft = cloneStringMap(incoming);
      serverSignature = nextSignature;
      initialized = true;
    }
  });

  const setValue = (mode: string, value: string) => {
    const next = { ...draft };
    const clean = value.trim();
    if (clean) next[mode] = clean;
    else delete next[mode];
    draft = next;
  };

  const resetDraft = () => {
    draft = Object.fromEntries(modes.flatMap((mode) => store.lookMap[mode] ? [[mode, store.lookMap[mode]]] : []));
  };

  const save = async () => {
    const next = cloneStringMap(store.lookMap);
    for (const mode of modes) {
      if (draft[mode]) next[mode] = draft[mode];
      else delete next[mode];
    }
    await store.setLookMap(next);
    serverSignature = signature(draft);
  };
</script>

<Panel title="Feste Modi" eyebrow="Unabhängige Look-Referenzen" description="Alle bestehenden festen Modi bleiben sichtbar und editierbar. Idle / Hard-Off wird nicht entfernt oder stillschweigend verändert.">
  {#snippet actions()}
    <button class="lp-button" type="button" onclick={resetDraft} disabled={!dirty}><RotateCcw size={17} />Entwurf verwerfen</button>
    <button class="lp-button primary" type="button" onclick={save} disabled={!dirty || store.mutation.state === "pending"}><Save size={17} />Speichern</button>
  {/snippet}

  <div class="lp-note" style="margin-bottom: 14px">Die bestehende `set_look_map`-Mutation ersetzt die Map vollständig. Deshalb wird beim Speichern die unveränderte Matrix und alle übrigen vorhandenen Schlüssel mitgeführt.</div>

  {#if !modes.length}
    <div class="lp-empty">Der Backend-Katalog liefert keine festen Modi.</div>
  {:else}
    <div class="lp-table-wrap">
      <table class="lp-table">
        <thead><tr><th>Modus</th><th>Look-Referenz</th><th>Coverage</th><th>Vertragshinweis</th></tr></thead>
        <tbody>
          {#each modes as mode (mode)}
            <tr>
              <td><strong>{MODE_LABELS[mode] ?? mode}</strong><span class="technical-key">{mode}</span></td>
              <td><LookSelect value={draft[mode] ?? ""} looks={store.looks} looksState={store.looksState} onchange={(value) => setValue(mode, value)} /></td>
              <td><CoverageBadge coverage={store.coverage([mode])[0]} /></td>
              <td class="lp-help">{mode === "idle" ? "Hard-Off-Ziel bleibt ein bestehender Look-Map-Schlüssel; die Sicherheitsabschaltung bleibt Backend-Eigentum." : "Nur vorhandene Look-Referenz; Inhalt und Ausführung gehören weiterhin Scene Presets."}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</Panel>
