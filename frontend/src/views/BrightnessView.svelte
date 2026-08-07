<script lang="ts">
  import { RotateCcw, Save } from "@lucide/svelte";
  import IconButton from "../lib/ui/IconButton.svelte";
  import Panel from "../lib/ui/Panel.svelte";
  import {
    CANONICAL_PHASES,
    DEFAULT_BRIGHTNESS,
    FIXED_MODES,
    LEGACY_PHASES,
    PHASE_LABELS,
    SEASON_KEYS,
    THEME_LABELS,
    percentToRaw,
    rawToPercent,
  } from "../lib/light-policy/contract";
  import type { LightPolicyStore } from "../lib/light-policy/store.svelte";

  let { store }: { store: LightPolicyStore } = $props();
  let overrides = $state<Record<string, number>>({});
  let initialized = $state(false);
  let serverSignature = "";
  const profile = $derived(store.status?.brightness_profile ?? {});
  const themes = $derived(store.catalog?.themes ?? []);
  const seasons = $derived(themes.filter((theme) => (SEASON_KEYS as readonly string[]).includes(theme)));
  const events = $derived(themes.filter((theme) => !(SEASON_KEYS as readonly string[]).includes(theme)));
  const standardPhases = $derived(CANONICAL_PHASES.filter((phase) => DEFAULT_BRIGHTNESS[phase] !== undefined));
  const fixedBrightnessModes = $derived(FIXED_MODES.filter((mode) => DEFAULT_BRIGHTNESS[mode] !== undefined));
  const dirty = $derived(JSON.stringify(Object.entries(overrides).sort(([a], [b]) => a.localeCompare(b))) !== JSON.stringify(Object.entries(inferOverrides(profile)).sort(([a], [b]) => a.localeCompare(b))));

  const isThemePhaseKey = (key: string) => [...CANONICAL_PHASES, ...LEGACY_PHASES].some((phase) => key.endsWith(`_${phase}`));

  function inferOverrides(source: Record<string, number>): Record<string, number> {
    const result: Record<string, number> = {};
    for (const [key, value] of Object.entries(source)) {
      if (DEFAULT_BRIGHTNESS[key] !== undefined) {
        if (DEFAULT_BRIGHTNESS[key] !== value) result[key] = value;
      } else if (isThemePhaseKey(key)) {
        result[key] = value;
      }
    }
    return result;
  }

  $effect(() => {
    const incoming = inferOverrides(profile);
    const signature = JSON.stringify(Object.entries(incoming).sort(([a], [b]) => a.localeCompare(b)));
    if (!initialized || (!dirty && signature !== serverSignature)) {
      overrides = incoming;
      serverSignature = signature;
      initialized = true;
    }
  });

  const effectiveRaw = (key: string, fallbackPhase?: string): number | null => {
    if (overrides[key] !== undefined) return overrides[key];
    if (profile[key] !== undefined) return profile[key];
    return fallbackPhase ? DEFAULT_BRIGHTNESS[fallbackPhase] ?? null : DEFAULT_BRIGHTNESS[key] ?? null;
  };

  const sourceFor = (key: string, fallbackPhase?: string): "explicit" | "standard" | "unavailable" => {
    if (overrides[key] !== undefined) return "explicit";
    if (profile[key] !== undefined && DEFAULT_BRIGHTNESS[key] === undefined) return "explicit";
    if (fallbackPhase ? DEFAULT_BRIGHTNESS[fallbackPhase] !== undefined : DEFAULT_BRIGHTNESS[key] !== undefined) return "standard";
    return "unavailable";
  };

  const setPercent = (key: string, value: string) => {
    const next = { ...overrides, [key]: percentToRaw(Number(value)) };
    overrides = next;
  };

  const reset = (key: string) => {
    const next = { ...overrides };
    delete next[key];
    overrides = next;
  };

  const resetDraft = () => {
    overrides = inferOverrides(profile);
  };

  const save = async () => {
    await store.setBrightnessProfile({ ...overrides });
    serverSignature = JSON.stringify(Object.entries(overrides).sort(([a], [b]) => a.localeCompare(b)));
  };

</script>

<Panel title="Standardprofil" eyebrow="Effektive Werte" description="Die UI zeigt Prozentwerte. Die bestehende Light Policy speichert weiterhin ihre eigenen Rohwerte; diese technische Darstellung ist ausschließlich unter Diagnose sichtbar.">
  {#snippet actions()}
    <button class="lp-button" type="button" onclick={resetDraft} disabled={!dirty}><RotateCcw size={17} />Entwurf verwerfen</button>
    <button class="lp-button primary" type="button" onclick={save} disabled={!dirty || store.mutation.state === "pending"}><Save size={17} />Profil speichern</button>
  {/snippet}

  <div class="lp-note" style="margin-bottom: 14px">Ein Override wird lokal gesammelt und erst mit „Profil speichern“ an den vorhandenen `set_brightness_profile`-Befehl gesendet. „Reset“ entfernt den Override aus dem nächsten vollständigen Profil.</div>

  <h3>Neun kanonische Tagesphasen</h3>
  <div style="margin-top: 8px">
    {#each standardPhases as phase (phase)}
      {@const raw = effectiveRaw(phase)}
      <div class="lp-range-row">
        <div><strong>{PHASE_LABELS[phase]}</strong><div class="technical-key">{phase}</div></div>
        <input type="range" min="0" max="100" step="1" value={rawToPercent(raw) ?? 0} aria-label={`${PHASE_LABELS[phase]} Prozent`} oninput={(event) => setPercent(phase, (event.currentTarget as HTMLInputElement).value)} />
        <div class="lp-percent">{rawToPercent(raw) ?? "–"} %</div>
        <div class="lp-badge-row"><span class="lp-badge {sourceFor(phase)}">{sourceFor(phase) === "standard" ? "Standard" : "Override"}</span><IconButton label="Override zurücksetzen" icon={RotateCcw} disabled={overrides[phase] === undefined} onclick={() => reset(phase)} /></div>
      </div>
    {/each}
  </div>

  <h3 style="margin-top: 22px">Feste Modi mit bestehendem Helligkeitswert</h3>
  <div style="margin-top: 8px">
    {#each fixedBrightnessModes as mode (mode)}
      {@const raw = effectiveRaw(mode)}
      <div class="lp-range-row">
        <div><strong>{THEME_LABELS[mode] ?? mode}</strong><div class="technical-key">{mode}</div></div>
        <input type="range" min="0" max="100" step="1" value={rawToPercent(raw) ?? 0} aria-label={`${mode} Prozent`} oninput={(event) => setPercent(mode, (event.currentTarget as HTMLInputElement).value)} />
        <div class="lp-percent">{rawToPercent(raw) ?? "–"} %</div>
        <div class="lp-badge-row"><span class="lp-badge {sourceFor(mode)}">{sourceFor(mode) === "standard" ? "Standard" : "Override"}</span><IconButton label="Override zurücksetzen" icon={RotateCcw} disabled={overrides[mode] === undefined} onclick={() => reset(mode)} /></div>
      </div>
    {/each}
  </div>
  <div class="lp-help" style="margin-top: 11px">Idle und Cinema haben im bestehenden Backend-Profil keinen Helligkeitsschlüssel. Dafür wird hier kein neuer Default erfunden.</div>
</Panel>

<Panel title="Optionale Theme- und Ereignis-Overrides" eyebrow="Separate Ebene" description="Ein Eintrag überschreibt nur die jeweilige Phase. Ohne Eintrag gilt der Standardwert der Phase; Look-Inhalt und Look-Generierung liegen weiterhin bei Scene Presets.">
    <div class="lp-note" style="margin-bottom: 14px">Die vorhandene Statusantwort enthält das gemergte Profil. Gleichheit mit dem Standardwert kann deshalb nicht beweisen, ob historisch ein expliziter Override gespeichert ist; die UI behauptet diese Unterscheidung nicht.</div>
    {#if seasons.length}
      <details class="lp-disclosure" open>
        <summary>Jahreszeiten · {seasons.length}</summary>
        <div class="lp-disclosure-content">{@render ThemeOverrides(seasons)}</div>
      </details>
    {/if}
    {#if events.length}
      <details class="lp-disclosure" style="margin-top: 12px">
        <summary>Ereignisse · {events.length}</summary>
        <div class="lp-disclosure-content">{@render ThemeOverrides(events)}</div>
      </details>
    {/if}
</Panel>

{#snippet ThemeOverrides(group: string[])}
  {#each group as theme (theme)}
    <div class="lp-panel compact" style="margin-bottom: 10px">
      <div class="lp-section-head"><div><h3>{THEME_LABELS[theme] ?? theme}</h3><div class="technical-key">{theme}</div></div><span class="lp-meta">9 optionale Werte</span></div>
      {#each CANONICAL_PHASES as phase (phase)}
        {@const key = `${theme}_${phase}`}
        {@const raw = effectiveRaw(key, phase)}
        <div class="lp-range-row">
          <div><strong>{PHASE_LABELS[phase]}</strong><div class="technical-key">{key}</div></div>
          <input type="range" min="0" max="100" step="1" value={rawToPercent(raw) ?? 0} aria-label={`${THEME_LABELS[theme] ?? theme} ${PHASE_LABELS[phase]} Prozent`} oninput={(event) => setPercent(key, (event.currentTarget as HTMLInputElement).value)} />
          <div class="lp-percent">{rawToPercent(raw) ?? "–"} %</div>
          <div class="lp-badge-row"><span class="lp-badge {sourceFor(key, phase)}">{sourceFor(key, phase) === "standard" ? "Phasenstandard" : "Override"}</span><IconButton label="Theme-Override zurücksetzen" icon={RotateCcw} disabled={overrides[key] === undefined} onclick={() => reset(key)} /></div>
        </div>
      {/each}
    </div>
  {/each}
{/snippet}
