<script lang="ts">
  import { Copy, RotateCcw, Save } from "@lucide/svelte";
  import CoverageBadge from "../lib/ui/CoverageBadge.svelte";
  import IconButton from "../lib/ui/IconButton.svelte";
  import LookSelect from "../lib/light-policy/LookSelect.svelte";
  import Panel from "../lib/ui/Panel.svelte";
  import { CANONICAL_PHASES, LEGACY_PHASES, PHASE_LABELS, SEASON_KEYS, THEME_LABELS } from "../lib/light-policy/contract";
  import { cloneStringMap } from "../lib/light-policy/store.svelte";
  import type { LightPolicyStore } from "../lib/light-policy/store.svelte";

  let { store }: { store: LightPolicyStore } = $props();
  let draftMap = $state<Record<string, string>>({});
  let initialized = $state(false);
  let serverSignature = "";
  let copySourcePhase = $state<(typeof CANONICAL_PHASES)[number]>("early_night");

  const mapSignature = (map: Record<string, string>) => JSON.stringify(Object.entries(map).sort(([a], [b]) => a.localeCompare(b)));
  const dirty = $derived(mapSignature(draftMap) !== mapSignature(store.lookMap));
  const themes = $derived(store.catalog?.themes ?? []);
  const seasons = $derived(themes.filter((theme) => (SEASON_KEYS as readonly string[]).includes(theme)));
  const events = $derived(themes.filter((theme) => !(SEASON_KEYS as readonly string[]).includes(theme)));

  $effect(() => {
    const incoming = store.lookMap;
    const signature = mapSignature(incoming);
    if (!initialized || (!dirty && signature !== serverSignature)) {
      draftMap = cloneStringMap(incoming);
      serverSignature = signature;
      initialized = true;
    }
  });

  const setValue = (key: string, value: string) => {
    const next = { ...draftMap };
    const clean = value.trim();
    if (clean) next[key] = clean;
    else delete next[key];
    draftMap = next;
  };

  const copyTheme = (theme: string) => {
    const source = draftMap[`${theme}_${copySourcePhase}`] ?? "";
    const next = { ...draftMap };
    for (const phase of CANONICAL_PHASES) {
      const key = `${theme}_${phase}`;
      if (source) next[key] = source;
      else delete next[key];
    }
    draftMap = next;
  };

  const resetDraft = () => {
    draftMap = cloneStringMap(store.lookMap);
  };

  const save = async () => {
    await store.setLookMap(cloneStringMap(draftMap));
    serverSignature = mapSignature(draftMap);
  };
</script>

<Panel title="Kanonische Tagesphasen" eyebrow="Primärer Slice" description="Jede Zelle ist eine unabhängige Look-Referenz. Wiederholte Referenzen sind zulässig und werden als geteilt angezeigt; sie bedeuten keine vererbte Standard-Zuordnung.">
  {#snippet actions()}
    <select class="lp-select" style="width: auto" aria-label="Quelle für Kopierhilfe" value={copySourcePhase} onchange={(event) => (copySourcePhase = (event.currentTarget as HTMLSelectElement).value as (typeof CANONICAL_PHASES)[number])}>
      {#each CANONICAL_PHASES as phase (phase)}<option value={phase}>{PHASE_LABELS[phase]} kopieren</option>{/each}
    </select>
    <button class="lp-button" type="button" onclick={resetDraft} disabled={!dirty}><RotateCcw size={17} />Entwurf verwerfen</button>
    <button class="lp-button primary" type="button" onclick={save} disabled={!dirty || store.mutation.state === "pending"}><Save size={17} />Alle Änderungen speichern</button>
  {/snippet}

  <div class="lp-note" style="margin-bottom: 16px">Gespeichert wird bewusst einmalig als vollständige vorhandene Map; ein Zellwechsel führt zu keinem automatischen Re-Apply. Die bestehenden Admin- und Resync-Grenzen bleiben beim Host.</div>

  {#if !themes.length}
    <div class="lp-empty">Der bestehende Katalog liefert keine Themen oder Ereignisse.</div>
  {:else}
    {#if seasons.length}
      <details class="lp-disclosure" open>
        <summary>Jahreszeiten · {seasons.length}</summary>
        <div class="lp-disclosure-content">{@render MatrixTable(seasons, store, draftMap, setValue, copyTheme)}</div>
      </details>
    {/if}

    {#if events.length}
      <details class="lp-disclosure" style="margin-top: 12px" open>
        <summary>Ereignisse · {events.length}</summary>
        <div class="lp-disclosure-content">{@render MatrixTable(events, store, draftMap, setValue, copyTheme)}</div>
      </details>
    {/if}
  {/if}
</Panel>

<Panel title="Legacy-Kompatibilität" eyebrow="Nicht primär" description="late_morning und early_evening stammen aus der historischen Acht-Phasen-Generation. Sie bleiben für Bestandsdaten sichtbar, erweitern aber nicht die primäre Neun-Phasen-Matrix.">
    <div class="lp-note" style="margin-bottom: 14px">Legacy-Zellen werden nicht automatisch in neue Werte umgeschrieben. Die neun primären Werte müssen explizit gepflegt werden.</div>
    {#if themes.length}
      <div class="lp-table-wrap">
        <table class="lp-table">
          <thead><tr><th>Thema / Ereignis</th>{#each LEGACY_PHASES as phase (phase)}<th>{PHASE_LABELS[phase]}<span class="technical-key">legacy · {phase}</span></th>{/each}</tr></thead>
          <tbody>
            {#each themes as theme (theme)}
              <tr>
                <td><strong>{THEME_LABELS[theme] ?? theme}</strong><span class="technical-key">{theme}</span></td>
                {#each LEGACY_PHASES as phase (phase)}
                  {@const key = `${theme}_${phase}`}
                  <td>
                    <LookSelect value={draftMap[key] ?? ""} looks={store.looks} looksState={store.looksState} onchange={(value) => setValue(key, value)} />
                    <div style="margin-top: 7px"><CoverageBadge coverage={store.coverage([key])[0]} /></div>
                  </td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else}
      <div class="lp-empty">Keine Legacy-Themen im aktuellen Katalog.</div>
    {/if}
</Panel>

{#snippet MatrixTable(themes: string[], store: LightPolicyStore, draftMap: Record<string, string>, setValue: (key: string, value: string) => void, copyTheme: (theme: string) => void)}
  <div class="lp-table-wrap">
    <table class="lp-table">
      <thead>
        <tr>
          <th>Theme / Ereignis</th>
          {#each CANONICAL_PHASES as phase (phase)}
            <th>{PHASE_LABELS[phase]}<span class="technical-key">{phase}</span></th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each themes as theme (theme)}
          <tr>
            <td>
              <strong>{THEME_LABELS[theme] ?? theme}</strong>
              <span class="technical-key">{theme}</span>
              <div style="margin-top: 8px"><IconButton label="Diesen Look über alle neun Phasen kopieren" icon={Copy} onclick={() => copyTheme(theme)} /></div>
            </td>
            {#each CANONICAL_PHASES as phase (phase)}
              {@const key = `${theme}_${phase}`}
              <td>
                <LookSelect value={draftMap[key] ?? ""} looks={store.looks} looksState={store.looksState} onchange={(value) => setValue(key, value)} />
                <div style="margin-top: 7px"><CoverageBadge coverage={store.coverage([key])[0]} /></div>
                {#if store.coverage([key])[0].notIndividuallyMaintained}<div class="lp-help" style="margin-top: 4px">Fallback · nicht einzeln gepflegt</div>{/if}
              </td>
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{/snippet}
