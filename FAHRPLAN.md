# Fahrplan — benni_light_policy

**Stand:** 2026-08-30. Teil der koordinierten `benni_*`-Überarbeitung (Abstimmung der Integrationen untereinander).

Issue #59 erweitert den bestehenden terminalen Sleep-Hard-Off additiv auf
`provisional_sleep`. TV-/Entertainment-Activity bleibt tatsächliche Activity,
überstimmt aber weder PS noch S. Es wurde kein zweiter Apply-Pfad eingeführt.

## Rolle in der abgestimmten Welt
**Licht-Orchestrator.** Entscheidet *wann welcher Look* gilt (Profil × Kontext × Tagesphase × Theme × feste Modi) und sendet einen **Look-Ref + Brightness-Override** an `benni_scene_presets`. Verwaltet **keine** Szenen/Lampen selbst (das macht scene_presets). Diese Trennung ist Voraussetzung fürs Eltern-System.

## Offene Punkte (Bahn A — nicht durch Extraktions-WIP blockiert)
- **A2 — Private Time / feste Modi konfigurierbar.** Modi existieren in der Engine (`POLICY_FIXED_MODES` = cinema/private_time/waking/work_home), Look-Ref-Auflösung via `look_map`. Lücke ist **WS-Contract/Coordinator-Setter** (Look-Ref + Brightness + Validitätsstatus), **nicht** die Logik. Kein Panel bauen — WS-Command genügt (Umbrella konsumiert später).
- **A3 — Per-Theme/Season-Brightness.** Engine kann es bereits (`_phase_brightness` liest `<theme>_<phase>` vor globalem Phasen-Default; `async_set_brightness_profile` erlaubt `theme_phase`-Keys). Lücke = nur **WS-Exposition**.
- **A4 — Profil-Modell Benni/Eltern.** Schlanker Config-Flow erzeugt nur Hub/Profil; Slug `<profile>_<integration>_<type>`. **Blaupause: `benni_core_state`** hat das Modell schon (`PROFILE_BENNI/ELTERN`, `PROFILE_PREFILL`).

## Konsumiert (Bahn B — hängt an Extraktions-Pipeline)
- **Theme-Detection** (Kalender/Season/berechnete Feste Ostern/Karneval) → kommt aus dem Context-Layer (`benni_core_state`), wird hier nur als Entity konsumiert. Die **Matrix** `theme×phase→look_ref+brightness` bleibt hier.
- **media_context** (Cinema/Gaming) → kommt aus `benni_media_state` (FLEET-36 Cut-over; vorher Toolbox-`benni_media_context`).

## A1 Brightness — Befund (2026-06-08, live verifiziert)
**Kein Übertragungs-Bug.** End-to-end verifiziert intakt: Wert (`_phase_brightness`, theme-aware) → Hash (triggert Re-Apply) → Reload-Trigger (`add_update_listener`) → `apply_look {look, brightness}` → scene_presets honoriert den Override (Live-Test: `brightness:30` vs `255` greift sichtbar). Gating live ok (`switch.light_policy_apply_enabled=on`, `apply_blocked=off`).

Die als „Brightness kommt nicht an" wahrgenommene Sache reduziert sich auf:
1. **Latenz** — Looks/Scenes mit langer `transition` (live gesehen: 60 s) lassen Änderungen träge wirken. ✅ **Erledigt 2026-06-08:** reine Brightness-Änderung am selben Look schickt jetzt `transition: 2` (const `BRIGHTNESS_CHANGE_TRANSITION_SECONDS`); Erkennung via persistiertem `last_applied_look_ref`/`_brightness` (überlebt den Reload). scene_presets `apply_look` akzeptiert dafür ein optionales `transition`-Feld.
2. **„Eindimensional"** = Feature-Lücke A3 (theme-spezifische Brightness pro Phase), Engine kann's, UX exponiert es nicht. **Offen.**

**Retire-Debt (Strangler) — ✅ erledigt 2026-06-08:** Legacy-Zweit-Owner `automation.living_light_apply_plan_on_change` + `script.living_light_apply_plan` (in `einhornzentrale/packages/light/`) entfernt; einziger Live-Konsument `script.system_bedtime_mode` auf `benni_light_policy.apply_now` umgehängt. **Offener Tiefen-Sweep:** `living_light_*_daylight_seen`-Automationen + input_boolean + die toten `living_light_*_combined`-Templates in `packages/combined/light.yaml`.

## Cinema-durch-PC (#8) — Befund + Fix (2026-06-08, live via Diagnostics)
**Ursache war Verdrahtung, nicht zu grobes media_context.** Live emittiert `media_context` bei PC-Betrieb korrekt `gaming` (nicht `tv`). Der Diagnostics-Dump des Hubs zeigte aber:
- `media_context_entity` **gar nicht gesetzt** → `ctx.media_context = None` → Cinema-Backward-Compat feuerte bei jedem Entertainment (und Cinema-Prio 11 schlägt PC-Gaming-Prio 12).
- `media_device_entity` zeigte falsch auf `sensor.stash_active_streams` (statt `…_media_device`) → bricht auch die Gaming-Subentries.

**Code-Härtung ✅ erledigt 2026-06-08** (`_eval_cinema`): Cinema verlangt jetzt ein *positives* TV-Signal (`media_context ∈ {tv,streaming}` ODER `media_device == "tv"`); Backward-Compat nur noch, wenn **beide** Quellen unverdrahtet (None). Neuer Regression-Test `test_cinema_not_hijacked_by_gaming_media_device`. 45 Tests grün.

**Erledigt via `ENTITY_PREFILL` (Code) + FLEET-36 Cut-over:** Die Media-Bindings sind im Code vorbelegt (kein Options-Setzen nötig) und zeigen seit FLEET-36 auf `benni_media_state`:
- `media_context_entity` → `sensor.benni_media_state_media_context`
- `media_device_entity` → `sensor.benni_media_state_media_device` — fixt zusätzlich die Gaming-Subentries.

## UX
Eigenes Panel (`blp-app`) bleibt **dünn/Wegwerf** — wandert später in die zentrale Umbrella-UX. Wertvoll ist der **WS-Contract**, nicht das Frontend.
