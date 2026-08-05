# benni_light_policy

Licht-Policy als eigenständige HACS-Custom-Integration.

## FLEET-54 source migration

Seit `0.2.5` migriert die Integration bekannte alte Toolbox/YAML-Quellen in
bestehenden ConfigEntries automatisch auf die Core-Integrationen:

- `sensor.garden_illuminance_atomic` -> `sensor.benni_device_garden_lux`
- `sensor.weather_season_meteorological_atomic` ->
  `sensor.benni_device_weather_season_meteorological`
- `sensor.benni_context_day_context` /
  `sensor.benni_combined_context_day_context` ->
  `sensor.benni_core_state_day_context`
- Legacy Core-State context/activity/presence entities -> their matching
  `sensor.benni_core_state_*` clean IDs
- `binary_sensor.benni_media_context_entertainment_active` ->
  `binary_sensor.benni_media_state_entertainment_active`
