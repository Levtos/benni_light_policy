# CLAUDE.md — Light Policy

## GitLab Workflow

- GitLab project `ha-platform/control` is the central workflow truth.
- Relevant work requires a GitLab issue in `ha-platform/control`.
- Before work starts, read the issue description and all issue notes.
- Document current state, decisions, scope changes, tests, commits, merge requests, blockers, and completion in the issue.
- Code changes happen in the matching GitLab repository. `origin` must point to GitLab.
- GitHub is only the public distribution and HACS mirror. Do not develop directly on GitHub and do not push manually to GitHub.
- Plane and Forgejo are historical sources only and are not used for active work.
- Full rules live in `ha-platform/control/AGENTS.md`, `ha-platform/control/CLAUDE.md`, and `ha-platform/control/docs/workflow/`.

## Project-Memory Bootstrap

- Before significant work, read the matching GitLab issue description and all notes, then `ha-platform/control/docs/workflow/README.md`, its linked workflow documents, and relevant `ha-platform/control` wiki pages.
- GitLab is the workflow truth. GitHub is only the distribution/HACS mirror; do not develop there directly. Plane is frozen historical context, and Forgejo is out of service.
- Stay inside the decided issue scope: no side quests and no overwriting foreign branches or dirty worktrees.
- Use the smallest sufficient verification for the risk tier. Stable changes to behavior, contracts, operations, or rules belong in the wiki; use live evidence when runtime behavior must be proved. Completion notes must document wiki impact, verification/tests, release state where applicable, and required live evidence.

## Safety

- Do not put secrets in issues, commits, logs, or reports.
- Do not touch production Home Assistant systems without explicit approval.
- No admin, delete, runner, or bulk actions without explicit approval.

**Status:** Im Bau. Vertikaler Wohnzimmer-Slice steht (Decision/Emit-Layer + gated Apply-Scaffold + pure-logic-Tests).
**Letzte Aktualisierung:** 2026-06-01

## Apply-Kanal: benni_scene_presets Looks (2026-06-01, Schritt 1)

Der Apply-Kanal wurde von der **Szenen-/UUID-Ebene** auf die **Look-Ebene** von
`benni_scene_presets` umgestellt:
- Domain ist jetzt `benni_scene_presets` (vorher `scene_presets`).
- Der Coordinator ruft für alle Look-Modi **einen** Service: `apply_look {look, brightness}`.
  Der **Look** ist die deploybare Einheit und trägt Targets, Off-Bindings (`kind:"off"`)
  und Crossfade (`look_transition`) selbst. Damit entfällt im Coordinator die alte
  Choreografie (`stop_dynamic_scenes_for_targets` → `apply_preset` → `sleep` → `exclusive_off`
  → `start_dynamic_scene`) sowie die UUID-Auflösung (`_resolve_preset_id` + Katalog-Sensor).
- Die Policy liefert die **Look-Ref über `preset_enum`** (Name **oder** Slug, 1:1 durchgereicht).
  Kernmodi: `cinema`/`private_time` (fix), `<theme>_<phase>` (dayphase/household/presence_sim),
  Gaming/Musik aus den Subentry-Mappings. **CCT-Modi** (`waking`/`work_home`) zeigen jetzt auch
  auf Kelvin-Looks (`preset_enum=MODE_WAKING`/`MODE_WORK_HOME`). **Brightness** kommt weiter aus
  der Tagesphase und wird als Override an `apply_look` übergeben.
- **Ausnahme:** `wake_up`-Subentry (freie `raw_targets`, kein Look) bleibt direkter
  `light.turn_on` (Kelvin+Brightness). `APPLY_OFF` bleibt `light.turn_off` auf GROUP_ALL.
- `manifest.json`: `after_dependencies: ["benni_scene_presets"]`.
- **Voraussetzung live:** die referenzierten Looks müssen im benni_scene_presets-Panel
  existieren (Off-Bindings für cinema/private_time, Kelvin-Looks für waking/work_home auf die
  weißen Ceilings). Fehlender Look → `apply_look` wirft `vol.Invalid`, HA loggt es (kein Crash).
- **Aufgeschoben auf UX-Rework:** konfigurierbare Look-Map für Kernmodi; Entfernen des
  jetzt ungenutzten `CONF_PRESET_CATALOG`-Felds + Umlabeln der Mapping-Slots
  („Scene-Preset-UUID" → „Look-Slug") in config_flow/strings; `scene_interval_seconds`-Option
  (Interval lebt jetzt im Look/Binding).

## Architektur-Entscheidungen (2026-05-29, beim Bau-Start getroffen)

- **Hub + typisierte Subentries** (ersetzt die alte „Single-Instance, flache Config", die zur „Litanei" wurde). **Hub-Entry**: Foundation-Entities EINMAL (breites Auto-Prefill aus Live-IDs via `ENTITY_PREFILL` + `GROUP_PREFILL` + `SUBENTRY_PREFILL` — Singletons wie Garten-Lux, Entertainment-Active, System-Ready, Jahreszeit, alle benni_*-Sensoren werden vorbelegt wenn vorhanden), Lampengruppen, Katalog, globale Gates + Apply + Arbitrierung. **Lampengruppen sind Multi-Light-Listen** (keine HA-Group-Entity existiert) — `_resolve_targets` flacht sie. **Subentries pro Anwendungsfall** (`config_subentries`): Gaming, Musik, Notification-RGB, Flur, Bad, Schlafzimmer — jede mit NUR ihren Feldern. Kern-Wohnzimmer-Policies (waking/sleep/lux-off/work_home/private_time/household/presence_sim/cinema/dayphase) laufen ohne Subentry; Gaming/Musik werden per Subentry als `extra_policies` in die Prioritäts-Arbitrierung eingespeist (`policy.make_gaming_policy`/`make_music_policy`). Flur/Bad/Ring = Controller je Subentry (`areas.build_controllers_from_subentries`); Bettgeh-Signal pro Bedroom-Subentry. **Title-Classifier-Split:** kein Sammelfeld mehr — jede Gaming-/Musik-Subentry trägt ihren eigenen Classifier + Wert→Preset. **Status: gebaut, Tests grün, aber Config-Subentry-/Coordinator-Verdrahtung NUR in HA verifizierbar (lokal kein HA).** Reconfigure von Subentries: v1 nicht implementiert (löschen + neu anlegen).
- **Apply im Coordinator, gated** an `apply_enabled` (Default `False` = shadow-safe) — wie `cover_policy`. **Weicht bewusst von der Roadmap/alten-CLAUDE-Note „YAML reagiert auf `_scene_hash`" ab.** Die Crossfade-Choreografie (R3/R3b) lebt in Python (`coordinator._apply`), nicht in YAML. `mode`/`scene_hash`/`plan`-Sensoren werden trotzdem emittiert — für Observability + Phase-4-Shadow-Vergleich (Shadow = `apply_enabled=off`).
- **Scene-Hash:** SHA-256[:16] über die sichtbaren Plan-Parameter (mode/preset/brightness/cct/targets/exclusive_off), OHNE Gating. Lesbarer Szenenname kommt als Attribut am `_plan`-Sensor.
- **Scene Presets = eigener Fork `benni_scene_presets`** (Render-Schicht mit Looks). Crossfade & Off liegen jetzt im Look (`look_transition` + Off-Bindings) — der alte KH-7-Workaround (`apply_preset`+`delay`) ist hinfällig, s. „Apply-Kanal"-Abschnitt oben.

## Offene Punkte / noch nicht gebaut

- Apply ist live verifizierbar, sobald die referenzierten **Looks** im benni_scene_presets-Panel angelegt sind (kein Katalog-Sensor mehr nötig). Bis `apply_enabled` an ist, bleibt alles shadow-safe.
- **Spec-Tension:** Entscheidungskette §4.1 setzt „Lux-Gate off → idle hard-off" (Prio 3) ÜBER work_home/private_time/cinema. Heißt: bei hellem Tag gehen auch work_home/Gaming/Cinema hart aus. Exakt per Lastenheft implementiert — vom User zu bestätigen oder anzupassen.

## Gebauter Stand (2026-05-29)

- **Wohnzimmer-Plan** (Entscheidungskette §4.1 komplett), Lux-Gate inkl. **TMC-Latch (R2)** + **Wetter-Dunkelheit (R10)**, Crossfade-Apply (R3/R3b) gated.
- **Bereichs-Controller** in `areas.py`: **Flur (R14)** Tür/Bewegung+Timer+3x-Off, **Bad (R15)** 60-Min-Vergessensschutz+Vibrations-Reset, **Ring (R17)** Aqara via Activity-State (Preset-Namen OQ-1 → nur ring_mode-Sensor bis Map konfiguriert).
- **Schlafzimmer-Bettgeh-Signal (R16)** edge-getriggert im Coordinator.
- **R12 Heimkommen:** coming_home unterdrückt presence_sim sofort + erzwingt Re-Apply.
- **Manual-Off (R9):** `switch.lights_manual_off_living_room` — vom User per Switch Manager auf eine Taste legbar. Hold blockiert Apply, Auto-Reset bei sleep→awake, persistiert. (Bewusst KEINE Dimm-Diff-Auto-Detektion — unsere eigene Dynamic-Scene-Engine würde sonst Falschauslöser erzeugen.)
- Sensoren: mode, scene_hash, brightness/cct_target, preset_enum, plan, ring_mode, debug; binary: lux_gate (`lights_allowed_combined`), apply_blocked, bedtime_signal; switch: manual_off.
- **32 pure-logic-Tests** grün (decide-Kette inkl. coming_home, lux_gate/TMC/Wetter, bedtime/hallway-Prädikate, scene_hash).

## UX / Config (2026-05-29)

- **Mehrstufiger Config-Flow** (7 Kategorien, je ~5 Felder, Wording 1:1 Toolbox), Selektoren ungefiltert. Options-Flow als **Menü** (Kategorie einzeln editierbar).
- **Ring = Mehrfach** (`ring_target_entities`) → simultane Status-Effekte auf alle Ringe (Wohnzimmer + Küche).
- Shadow-Helfer: `switch.lights_apply_enabled` (Apply runtime-toggle), Lux-Gate-Internals im Debug-Sensor (`gate_internals()`), `diagnostics.py` (State-Dump-Download).

## Noch offen

- **Lampengruppen → Atomic Light Groups in `benni_core_devices`** (Entscheidung 2026-05-29). **Gebaut:** bennis_toolbox PR #19 — `sensor.benni_light_group_<slug>` je Gruppe, Member im `entity_id`-Attribut, CRUD im Options-Flow. **Migration light_policy noch offen:** Gruppen-Felder von Multi-Light-Listen → EINE Gruppen-Entity je Gruppe + Member-Expansion (Light-Group `entity_id`-Attribut) für scene_presets. **Aktuell Stopgap:** Multi-Light-Listen direkt in light_policy (prefilled `GROUP_PREFILL`). Migration sobald PR #19 gemerged + Gruppen in HA angelegt.
- **Kein Scene-Presets-Katalog-Sensor mehr nötig** — der Look-Kanal referenziert Looks per Name/Slug direkt (`CONF_PRESET_CATALOG` ist deprecated, Entfernung im UX-Rework).
- **R13 Household-Auto-Off** mit 20s-Debounce — derzeit upstream über activity_state abgedeckt (Modus folgt activity_state direkt).
- Timer-/Service-Pfade (areas.py, Apply, Switch) sind **nur in HA verifizierbar** (lokal kein HA/ruff).
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

## UX-Frontend-Standard (verbindlich)

Für jede UX-/Frontend-Arbeit gilt der verbindliche, fleet-weite UX-, Technologie- und
Designstandard. Kanonische Quelle: ADR `ha-platform/control:docs/adr/0001-ux-frontend-standard.md`
(Issue `control#58`). Kurzform: Svelte 5 · Vite · TypeScript · Bits UI · shadcn-svelte ·
Tailwind · CSS Custom Properties · Lucide; Design "Graphite Dark – semantic accent system";
zentrale UX = statisches Bundle + dünnes UX-Gateway (primär HA-Ingress); versionierte/typisierte
Contracts. Details und Abweichungsprozess: `docs/ux-frontend-standard.md` und das ADR. Bestehende
Regeln werden dadurch ergänzt, nie überschrieben oder entfernt.
