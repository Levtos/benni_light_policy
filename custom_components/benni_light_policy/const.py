"""Konstanten der Benni-Light-Policy.

Eigenständige HA-Integration (eigene Domain), erstes Aggregat-Modul. Konsumiert
Foundation-Sensoren (benni_core_*, benni_context, benni_media_context) AUSSCHLIESSLICH
als HA-Entity-IDs aus dem Config-Flow — kein Python-Cross-Modul-Import.

Apply läuft im Coordinator, gated an `apply_enabled` (wie cover_policy). Die
mode/scene_hash/plan-Sensoren werden für Observability + Phase-4-Shadow-Vergleich
immer emittiert, auch wenn apply blockiert ist.

Lastenheft: einhornzentrale/docs/lastenhefte/reviewed/lichtlogik/
"""
from __future__ import annotations

from typing import Final

DOMAIN: Final[str] = "benni_light_policy"
MODULE_ID: Final[str] = "light_policy"

# Datenwurzel in hass.data[DOMAIN].
DATA_COORDINATOR: Final[str] = "coordinator"

STORAGE_VERSION: Final[int] = 1


def unique_id(*parts: str) -> str:
    """Stabile unique_id über alle Entities des Moduls."""
    return "_".join((DOMAIN, *parts))


def storage_suffix(entry_id: str) -> str:
    return f"state_{entry_id}"


# --------------------------------------------------------------------------- #
# Modi — Wohnzimmer-Entscheidungskette (Lastenheft §4.1)
# --------------------------------------------------------------------------- #
MODE_WAKING: Final = "waking"
MODE_IDLE: Final = "idle"          # Hard-Off: sleep ODER Lux-Gate zu
MODE_PRIVATE_TIME: Final = "private_time"
MODE_WORK_HOME: Final = "work_home"
MODE_HOUSEHOLD: Final = "household"
MODE_PRESENCE_SIM: Final = "presence_sim"
MODE_MUSIC_PARTY: Final = "music_party"
MODE_PC_OVERWATCH: Final = "pc_overwatch"
MODE_PC_HEARTHSTONE: Final = "pc_hearthstone"
MODE_CINEMA: Final = "cinema"

# Day-State-Detailphasen (Fallback-Modi, Priorität 12).
PHASE_EARLY_MORNING: Final = "early_morning"
PHASE_LATE_MORNING: Final = "late_morning"
PHASE_FORENOON: Final = "forenoon"
PHASE_AFTERNOON: Final = "afternoon"
PHASE_EARLY_EVENING: Final = "early_evening"
PHASE_LATE_EVENING: Final = "late_evening"
PHASE_EARLY_NIGHT: Final = "early_night"
PHASE_LATE_NIGHT: Final = "late_night"

DAY_PHASES: Final = (
    PHASE_EARLY_MORNING, PHASE_LATE_MORNING, PHASE_FORENOON, PHASE_AFTERNOON,
    PHASE_EARLY_EVENING, PHASE_LATE_EVENING, PHASE_EARLY_NIGHT, PHASE_LATE_NIGHT,
)

# Phasen, in denen Anwesenheitssimulation läuft (early_evening..early_night).
PRESENCE_SIM_PHASES: Final = frozenset(
    {PHASE_EARLY_EVENING, PHASE_LATE_EVENING, PHASE_EARLY_NIGHT}
)

# --------------------------------------------------------------------------- #
# Eingangs-Wertebereiche (konsumiert aus benni_context / benni_core_*)
# --------------------------------------------------------------------------- #
BIO_SLEEP: Final = "sleep"
BIO_WAKING: Final = "waking"
BIO_AWAKE: Final = "awake"

ACTIVITY_PRIVATE_TIME: Final = "private_time"
ACTIVITY_WORK_HOME: Final = "work_home"
ACTIVITY_HOUSEHOLD: Final = "household"
ACTIVITY_FREE_TIME: Final = "free_time"
ACTIVITY_IDLE: Final = "idle"
ACTIVITY_PRESET_DRIVING: Final = frozenset({ACTIVITY_FREE_TIME, ACTIVITY_IDLE})

PRESENCE_HOME: Final = "zuhause"
PRESENCE_AWAY: Final = "abwesend"
PRESENCE_PARENTS: Final = "bei_eltern"
PRESENCE_SIM_TRIGGERS: Final = frozenset({PRESENCE_AWAY, PRESENCE_PARENTS})

TITLE_OVERWATCH: Final = "1"
TITLE_HEARTHSTONE: Final = "2"

SEASON_SPRING: Final = "spring"
SEASON_SUMMER: Final = "summer"
SEASON_AUTUMN: Final = "autumn"
SEASON_WINTER: Final = "winter"
SEASONS: Final = (SEASON_SPRING, SEASON_SUMMER, SEASON_AUTUMN, SEASON_WINTER)

CALENDAR_BIRTHDAY: Final = "geburtstag"

# --------------------------------------------------------------------------- #
# Config-Keys — Quell-Entities (alle als Entity-IDs aus dem Flow)
# --------------------------------------------------------------------------- #
CONF_BIO_STATE: Final = "bio_state_entity"
CONF_DAY_STATE: Final = "day_state_entity"
CONF_ACTIVITY_STATE: Final = "activity_state_entity"
CONF_LUX: Final = "lux_entity"
CONF_PRESENCE_PERSONAL: Final = "presence_personal_entity"
CONF_PRESENCE_HOUSEHOLD: Final = "presence_household_entity"
CONF_GUEST: Final = "guest_entity"
CONF_SEASON: Final = "season_entity"
CONF_CALENDAR_THEME: Final = "calendar_theme_entity"
CONF_TITLE_CLASSIFIER: Final = "title_classifier_entity"
CONF_ENTERTAINMENT_STABLE: Final = "entertainment_stable_entity"
CONF_OVERNIGHT_AWAY: Final = "overnight_away_entity"
CONF_SYSTEM_READY: Final = "system_ready_entity"
CONF_WEATHER: Final = "weather_entity"

# Apply-Schicht.
CONF_PRESET_CATALOG: Final = "preset_catalog_entity"   # sensor mit UUID-Lookup (Attribute)
CONF_GROUP_MAIN: Final = "group_main"                  # Hauptgruppe (light/group entity_id)
CONF_GROUP_CEILING: Final = "group_ceiling"            # Deckenlampe CCT
CONF_GROUP_ALL: Final = "group_all"                    # Hard-Off-Ziel

# Bereichs-Entities (R14–R17).
CONF_HALLWAY_LIGHT: Final = "hallway_light"
CONF_HALLWAY_TRIGGERS: Final = "hallway_trigger_entities"  # list[entity_id] Tür/Bewegung
CONF_BATHROOM_LIGHT: Final = "bathroom_light"
CONF_BATHROOM_VIBRATION: Final = "bathroom_vibration_entity"
CONF_BEDROOM_GROUP: Final = "bedroom_group"
CONF_AWAKE_MINUTES: Final = "awake_minutes_entity"
CONF_RING_TARGET: Final = "ring_target_entity"            # Aqara T1M RGB Ring
CONF_RING_PRESET_MAP: Final = "ring_preset_map"           # dict activity_state -> effect name

# Options.
CONF_APPLY_ENABLED: Final = "apply_enabled"
CONF_STARTUP_BLOCK_SECONDS: Final = "startup_block_seconds"
CONF_CROSSFADE_SECONDS: Final = "crossfade_seconds"
CONF_SCENE_TRANSITION_SECONDS: Final = "scene_transition_seconds"
CONF_SCENE_INTERVAL_SECONDS: Final = "scene_interval_seconds"
CONF_LUX_THRESHOLDS: Final = "lux_thresholds"          # dict season -> {dark, bright}
CONF_BRIGHTNESS: Final = "brightness_profile"          # dict mode/phase -> 0..255

# --------------------------------------------------------------------------- #
# Defaults & Konstanten (Lastenheft §8)
# --------------------------------------------------------------------------- #
DEFAULT_APPLY_ENABLED: Final = False        # Shadow-safe out of the box (Phase-4).
DEFAULT_STARTUP_BLOCK_SECONDS: Final = 15   # HA-Start-Delay.
DEFAULT_CROSSFADE_SECONDS: Final = 30
DEFAULT_SCENE_TRANSITION_SECONDS: Final = 300
DEFAULT_SCENE_INTERVAL_SECONDS: Final = 300

# TMC-Latch (R2): „war es heute schon hell?"
TMC_TRIGGER_LUX: Final = 401          # > 401 lx setzt das Latch
TMC_FALLBACK_HOUR: Final = 9          # 09:00 Fallback wenn User wach

# Wetter-Icons, die (zusammen mit Lux-Drop) wetterbedingte Dunkelheit bedeuten (R10).
WEATHER_DARK_ICONS: Final = frozenset({
    "cloudy", "rainy", "pouring", "lightning", "lightning-rainy",
    "snowy", "snowy-rainy", "hail", "fog",
})
WEATHER_DARK_DROP_RATIO: Final = 0.5  # > 50% Lux-Drop in 10 min
WEATHER_DARK_WINDOW_SECONDS: Final = 600

# master_phase-Werte, die als „Tageszeit" gelten (R10 greift nur dann).
MASTER_PHASE_DAYTIME: Final = frozenset({"morning", "midday"})

# Saisonale Lux-Schwellen (Schmitt-Trigger): {season: (dunkel, hell)}.
DEFAULT_LUX_THRESHOLDS: Final[dict[str, tuple[int, int]]] = {
    SEASON_SPRING: (350, 500),
    SEASON_SUMMER: (400, 550),
    SEASON_AUTUMN: (350, 500),
    SEASON_WINTER: (250, 400),
}

# Brightness pro Phase/Kontext (Lastenheft §7.1).
DEFAULT_BRIGHTNESS: Final[dict[str, int]] = {
    MODE_WAKING: 255,
    PHASE_EARLY_MORNING: 255,
    PHASE_LATE_MORNING: 255,
    PHASE_FORENOON: 255,
    PHASE_AFTERNOON: 255,
    PHASE_EARLY_EVENING: 220,
    PHASE_LATE_EVENING: 200,
    PHASE_EARLY_NIGHT: 150,
    PHASE_LATE_NIGHT: 100,
    MODE_WORK_HOME: 220,
    MODE_PRIVATE_TIME: 80,
}

# Farbtemperaturen (Kelvin) für CCT-getriebene Modi; sonst Preset-getrieben.
COLOR_TEMP_WORK_HOME: Final = 5000
COLOR_TEMP_WAKING: Final = 6500

# Feste Preset-Schlüssel für Sonderkontexte (Lastenheft §7.2).
PRESET_PC_OVERWATCH: Final = "games_overwatch_2"
PRESET_PC_HEARTHSTONE: Final = "games_hearthstone"
PRESET_BEDROOM_BEDTIME: Final = "bedroom_bedtime"

# Bereichs-Konstanten (R14–R17).
HALLWAY_TIMER_SECONDS: Final = 120          # 2-Min-Auto-Off (R14)
HALLWAY_OFF_REPEATS: Final = 3              # 3x Turn-Off mit Abstand (Zigbee)
HALLWAY_OFF_REPEAT_DELAY: Final = 3         # Sekunden zwischen den Off-Befehlen
HALLWAY_COLOR_TEMP: Final = 3000
BATHROOM_TIMEOUT_SECONDS: Final = 3600       # 60-Min-Vergessensschutz (R15)
BEDTIME_AWAKE_THRESHOLD_MINUTES: Final = 840  # 14h (R16)

# Aqara Advanced Lighting — T1M RGB Ring (R17), getrennt von Scene Presets (KH-9).
AQARA_DOMAIN: Final = "aqara_advanced_lighting"
AQARA_SERVICE_SET_EFFECT: Final = "set_dynamic_effect"

# --------------------------------------------------------------------------- #
# Lampengruppen-Bezeichner (logisch; konkrete Entities via Config)
# --------------------------------------------------------------------------- #
GROUP_MAIN: Final = "main"
GROUP_CEILING: Final = "ceiling"
GROUP_ALL: Final = "all"

# --------------------------------------------------------------------------- #
# unique_id-Suffixe der Output-Entities
# --------------------------------------------------------------------------- #
UID_MODE: Final = "living_room_mode"
UID_SCENE_HASH: Final = "living_room_scene_hash"
UID_BRIGHTNESS: Final = "living_room_brightness_target"
UID_COLOR_TEMP: Final = "living_room_color_temp_target"
UID_PRESET_ENUM: Final = "living_room_preset_enum"
UID_PLAN: Final = "living_room_plan"
UID_LUX_GATE: Final = "lux_gate"
UID_DEBUG: Final = "living_room_debug"
UID_APPLY_BLOCKED: Final = "living_room_apply_blocked"
UID_RING_MODE: Final = "ring_mode"
UID_BEDTIME_SIGNAL: Final = "bedroom_bedtime_signal"

# suggested_object_ids — kompatibel zur alten YAML-Welt wo Downstream-Module
# (z.B. Rollo) auf den Namen zugreifen.
OBJID_LUX_GATE: Final = "lights_allowed_combined"
OBJID_MODE: Final = "living_room_mode_combined"
OBJID_PLAN: Final = "living_room_plan_combined"

# --------------------------------------------------------------------------- #
# Services
# --------------------------------------------------------------------------- #
SERVICE_APPLY_NOW: Final = "apply_now"
SERVICE_SET_MANUAL_OFF: Final = "set_manual_off"
SERVICE_CLEAR_MANUAL_OFF: Final = "clear_manual_off"

# Scene-Presets-Integration (extern, eigene Domain).
SCENE_PRESETS_DOMAIN: Final = "scene_presets"
SP_SERVICE_APPLY_PRESET: Final = "apply_preset"
SP_SERVICE_START_DYNAMIC: Final = "start_dynamic_scene"
SP_SERVICE_STOP_FOR_TARGETS: Final = "stop_dynamic_scenes_for_targets"
