# CLAUDE.md — Light Policy

**Status:** Im Bau. Vertikaler Wohnzimmer-Slice steht (Decision/Emit-Layer + gated Apply-Scaffold + pure-logic-Tests).
**Letzte Aktualisierung:** 2026-05-29

## Architektur-Entscheidungen (2026-05-29, beim Bau-Start getroffen)

- **Single-Instance** — ein Config-Entry, Domain `benni_light_policy`. Begründung: ~99% der Lichtlogik ist Wohnzimmer; globale Gates (Lux-Gate, TMC) leben zentral; Bereiche haben heterogene Logik.
- **Apply im Coordinator, gated** an `apply_enabled` (Default `False` = shadow-safe) — wie `cover_policy`. **Weicht bewusst von der Roadmap/alten-CLAUDE-Note „YAML reagiert auf `_scene_hash`" ab.** Die Crossfade-Choreografie (R3/R3b) lebt in Python (`coordinator._apply`), nicht in YAML. `mode`/`scene_hash`/`plan`-Sensoren werden trotzdem emittiert — für Observability + Phase-4-Shadow-Vergleich (Shadow = `apply_enabled=off`).
- **Scene-Hash:** SHA-256[:16] über die sichtbaren Plan-Parameter (mode/preset/brightness/cct/targets/exclusive_off), OHNE Gating. Lesbarer Szenenname kommt als Attribut am `_plan`-Sensor.
- **Scene Presets bleibt eigene Integration** (kein Fork jetzt). Crossfade per Lastenheft-Workaround (KH-7: `apply_preset`+`delay` vor `start_dynamic_scene`). Der harte 0,5s-Sprung sitzt in `dynamic_scenes.py` (`run_count==0 → transition=0.5`) — falls der Workaround live unschön ist, ist ein **2-Zeilen-Mini-Fork** als eigenes Repo der nächste Schritt (Fork-Entscheidung vertagt auf nach erster Verifikation).

## Offene Punkte / noch nicht gebaut

- Apply ist nur verifizierbar, sobald Lampengruppen-Entities + Scene-Presets-Katalog-Sensor (UUID-Lookup) konfiguriert sind. Ohne diese bleibt Apply blockiert (shadow-safe).
- **Spec-Tension:** Entscheidungskette §4.1 setzt „Lux-Gate off → idle hard-off" (Prio 3) ÜBER work_home/private_time/cinema. Heißt: bei hellem Tag gehen auch work_home/Gaming/Cinema hart aus. Exakt per Lastenheft implementiert — vom User zu bestätigen oder anzupassen.

## Gebauter Stand (2026-05-29)

- **Wohnzimmer-Plan** (Entscheidungskette §4.1 komplett), Lux-Gate inkl. **TMC-Latch (R2)** + **Wetter-Dunkelheit (R10)**, Crossfade-Apply (R3/R3b) gated.
- **Bereichs-Controller** in `areas.py`: **Flur (R14)** Tür/Bewegung+Timer+3x-Off, **Bad (R15)** 60-Min-Vergessensschutz+Vibrations-Reset, **Ring (R17)** Aqara via Activity-State (Preset-Namen OQ-1 → nur ring_mode-Sensor bis Map konfiguriert).
- **Schlafzimmer-Bettgeh-Signal (R16)** edge-getriggert im Coordinator.
- Sensoren: mode, scene_hash, brightness/cct_target, preset_enum, plan, ring_mode, debug; binary: lux_gate (`lights_allowed_combined`), apply_blocked, bedtime_signal.
- **31 pure-logic-Tests** grün (decide-Kette, lux_gate/TMC/Wetter, bedtime/hallway-Prädikate, scene_hash).

## Noch offen

- **R12 Heimkommen** (coming_home-Transition) — derzeit über presence_personal-Flip abgedeckt, kein expliziter Trigger.
- **R13 Household-Auto-Off** mit 20s-Debounce — derzeit upstream über activity_state abgedeckt.
- **Manual-Off via Dimm-Diff-Detektion** (CLAUDE-Pattern) — aktuell nur Hold via Service + sleep→awake-Reset (R9).
- Timer-/Service-Pfade (areas.py, Apply) sind **nur in HA verifizierbar** (lokal kein HA/ruff).
- Danach: Fork-/Authoring-Repo `benni_scene_presets` (siehe Memory).

---

## Was ist dieses Modul

Licht-Policy: entscheidet pro Bereich (Wohnzimmer, Küche, Bad, Flur, Schlafzimmer) basierend auf Presence + Bio + Day-State + Media-Context + Lux + Motion welcher Lichtmodus aktiv sein soll. Liefert pro Bereich:
- `sensor.<bereich>_light_mode` (semantischer Modus, z.B. movie/work/sleep/wake/evening)
- `sensor.<bereich>_light_scene_hash` (Hash der wirksamen Parameter — YAML triggert nur bei Change)
- `sensor.<bereich>_light_brightness_target` / `_color_temp_target` (direkt nutzbare Werte)
- `sensor.<bereich>_light_plan` (volles Plan-Objekt als Attribute)
- `binary_sensor.<bereich>_light_apply_blocked` (gated an system_apply_ready)

YAML in einhornzentrale reagiert auf `_scene_hash`-Change mit `light.turn_on`.

**Lastenheft:** `einhornzentrale/docs/lastenhefte/reviewed/lichtlogik/`

## Architektur-Kontext

Eigene HACS-Custom-Integration. **Erstes Aggregat-Modul** (Phase 3, nach kompletter Foundation + Devices). Konsumiert die 3 Herzen + Day-Context + Media-Context als HA-Entities.

**Pattern für Aggregat-Module** ist hier zu etablieren — alle nachfolgenden (Climate, Rollo, etc.) orientieren sich an diesem Modul.

**Pendant-Briefings:**
- `bennis_toolbox/CLAUDE.md` — Foundation + Pattern
- `einhornzentrale/CLAUDE.md` — YAML + Cut-Over-Status
- `einhornzentrale/docs/roadmap.md` — Phase 3 (Aggregat-Module)

## Wann startet der Bau

- Sobald `benni_core_devices` (Atomic Layer) in bennis_toolbox steht
- Sobald `benni_core_day_context` gebaut ist (LH existiert)
- Idealerweise nach erfolgreichem Hybrid-Pivot der Eltern-Module

## Pattern (für den Bau)

Referenz-Implementierungen:
- `bennis_toolbox/modules/benni_core_user_state/` — Single-Instance + Storage + Services
- `bennis_toolbox/modules/benni_core_presence_state/` — Komplexere Timer-Logik im Coordinator
- `bennis_toolbox/modules/cover_policy/` (nach Extraction in `benni_cover_policy`) — Decision/Apply-Pattern mit `apply_blocked`-Sensor

Spezifika für Licht:
- Multi-Instance (eine Config-Entry pro Bereich) ODER Single-Instance mit Bereichs-Liste — Designentscheidung beim Start
- Scene-Hash: SHA-256[:16] oder semantischer Key — beim Start entscheiden
- Manual-Override-Pattern: wenn User Lichtschalter dimmt, Toolbox bemerkt Diff zwischen target und Ist, sperrt Apply bis Mode wechselt
