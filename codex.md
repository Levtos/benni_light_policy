# Codex Instructions — Light Policy

Lies zuerst `CLAUDE.md` in diesem Repo.

## MCP-Server

`einhornzentrale`. Nicht `haos_benni`.

## Aktueller Status

**Keine Aufgabe.** Modul wird in Phase 3 (Aggregat-Module) von Claude neu gebaut. Roadmap: `einhornzentrale/docs/roadmap.md`.

## Wenn der Bau steht (zukünftige Aufgabe Codex)

Dann **YAML in einhornzentrale** anpassen:
- Auf `sensor.<bereich>_light_scene_hash`-Change triggern
- `light.turn_on` mit Parametern aus `_brightness_target`, `_color_temp_target`, `plan`-Attributen
- Apply-Gate: Condition gegen `binary_sensor.<bereich>_light_apply_blocked` und globales `binary_sensor.system_apply_ready`

## Anti-Patterns

- ❌ Direkte `light.turn_on`-Calls aus Toolbox-Modulen
- ❌ Lastenheft-Konsolidierung
- ❌ Auf alter VM Features bauen
