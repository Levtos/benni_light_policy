"""Konstanten der Benni-Light-Policy.

Eigenständige HA-Integration (eigene Domain), erstes Aggregat-Modul. Konsumiert
Foundation-Sensoren (benni_core_*, benni_context, benni_media_state) AUSSCHLIESSLICH
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
CONFIG_ENTRY_VERSION: Final[int] = 7

# Datenwurzel in hass.data[DOMAIN].
DATA_COORDINATOR: Final[str] = "coordinator"
DATA_SKIP_RELOAD_COUNT: Final[str] = "skip_reload_count"

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

# Alias explicitly names the phase values that were deployed before Core-State
# introduced its canonical nine-phase contract.
LEGACY_DAY_PHASES: Final = DAY_PHASES

# Core-State PR #30 führt einen neunstufigen Ziel-Contract ein. Die historische
# Acht-Phasen-Menge bleibt für bereits laufende Deployments und bestehende Look-
# Maps erhalten; Policy und Migration akzeptieren beide Generationen.
PHASE_MIDDAY: Final = "midday"
PHASE_LATE_AFTERNOON: Final = "late_afternoon"
PHASE_EVENING: Final = "evening"
CORE_DAY_PHASES: Final = (
    PHASE_EARLY_NIGHT, PHASE_LATE_NIGHT, PHASE_EARLY_MORNING, PHASE_FORENOON,
    PHASE_MIDDAY, PHASE_AFTERNOON, PHASE_LATE_AFTERNOON, PHASE_EVENING,
    PHASE_LATE_EVENING,
)
SUPPORTED_DAY_PHASES: Final = tuple(dict.fromkeys((*CORE_DAY_PHASES, *LEGACY_DAY_PHASES)))

# The primary matrix follows the Core-State contract. Legacy-only values stay
# available for runtime/config compatibility but are not additional primary
# matrix columns.
CANONICAL_MATRIX_PHASES: Final = CORE_DAY_PHASES
LEGACY_MATRIX_PHASES: Final = tuple(
    phase for phase in LEGACY_DAY_PHASES if phase not in CANONICAL_MATRIX_PHASES
)

# Phasen, in denen Anwesenheitssimulation läuft (alte und neue Abend-/Nachtwerte).
PRESENCE_SIM_PHASES: Final = frozenset(
    {
        PHASE_EARLY_EVENING, PHASE_LATE_EVENING, PHASE_EARLY_NIGHT,
        PHASE_EVENING,
    }
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

# Kanonischer Gaming-Zustand (Activity-State-Vertrag von benni_core_state) sowie
# „PC eingeschaltet, aber (noch) kein Spiel".
ACTIVITY_GAMING: Final = "gaming"
ACTIVITY_PC_ACTIVE: Final = "pc_active"

# Eigenes Gate für make_gaming_policy — bewusst GETRENNT von
# ACTIVITY_PRESET_DRIVING (das die Musik-Policy nutzt und hier NICHT verändert
# wird). `gaming` ist der kanonische Gaming-Zustand; `free_time`/`idle` bleiben
# aus Rückwärtskompatibilität erlaubt. `pc_active` ist bewusst NICHT enthalten:
# es bedeutet nur „PC an" und trat in der Recorder-Historie ohne Gaming-Kontext
# auf (media_context≠gaming, title_classifier_pc_enum=0). Echte Gaming-Erkennung
# läuft über `gaming` (zusätzlich abgesichert durch media_device + Enum-Mapping).
GAMING_ACTIVITY_STATES: Final = frozenset(
    {ACTIVITY_GAMING, ACTIVITY_FREE_TIME, ACTIVITY_IDLE}
)

PRESENCE_HOME: Final = "zuhause"
PRESENCE_AWAY: Final = "abwesend"
PRESENCE_PARENTS: Final = "bei_eltern"
PRESENCE_SIM_TRIGGERS: Final = frozenset({PRESENCE_AWAY, PRESENCE_PARENTS})

# Präsenz-Transition (R12 Heimkommen).
PRESENCE_TRANSITION_COMING_HOME: Final = "coming_home"
PRESENCE_TRANSITION_LEAVING: Final = "leaving_home"

SEASON_SPRING: Final = "spring"
SEASON_SUMMER: Final = "summer"
SEASON_AUTUMN: Final = "autumn"
SEASON_WINTER: Final = "winter"
SEASONS: Final = (SEASON_SPRING, SEASON_SUMMER, SEASON_AUTUMN, SEASON_WINTER)

# Event-Themes (THEME_MAP-Ziele) zusätzlich zu den Jahreszeiten — zusammen die
# Zeilen der Tagesphasen-Matrix (Theme × Phase → Look). Die Werte stammen aus
# dem aktuellen Core-State-Kalender-Contract; deutsche Legacy-Namen werden in
# policy.THEME_MAP auf diese Look-Schlüssel normalisiert.
POLICY_EVENT_THEMES: Final = (
    "christmas", "easter", "halloween", "carnival", "geburtstag", "silvester", "pride",
    "advent_1", "advent_2", "advent_3", "advent_4", "stpatricks",
)
POLICY_THEMES: Final = (*SEASONS, *POLICY_EVENT_THEMES)


def matrix_keys(
    themes: list[str] | tuple[str, ...] | None = None,
    phases: list[str] | tuple[str, ...] | None = None,
) -> list[str]:
    """Return ordered Theme × Phase keys for the requested phase generation."""
    return [
        f"{theme}_{phase}"
        for theme in (themes or POLICY_THEMES)
        for phase in (phases if phases is not None else CANONICAL_MATRIX_PHASES)
    ]


# Feste Policy-Modi, die einen Look-Ref brauchen (keine Tagesphasen-Matrix).
# `idle` = Hard-Off-Zustand: bekommt eine eigene Look-Map-Zuordnung (all_off-Look),
# damit der Warden den Off-Zustand über die Look-Ebene durchsetzen kann. Der Apply
# selbst bleibt fail-safe direktes light.turn_off auf GROUP_ALL (APPLY_OFF-Zweig).
POLICY_FIXED_MODES: Final = ("idle", "cinema", "private_time", "waking", "work_home")

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
DEFAULT_SYSTEM_READY_ENTITY: Final = "binary_sensor.benni_core_state_apply_ready"
CONF_WEATHER: Final = "weather_entity"
CONF_PRESENCE_TRANSITION: Final = "presence_transition_entity"
# Spider-web-Konsum aus benni_media_state: welche Quelle ist aktiv (pc/ps5/…)
# und in welchem Modus (gaming/tv/streaming/…). Lebt im Hub, einmal verdrahtet.
CONF_MEDIA_DEVICE: Final = "media_device_entity"
CONF_MEDIA_CONTEXT: Final = "media_context_entity"

# Apply-Schicht.
CONF_GROUP_MAIN: Final = "group_main"                  # Hauptgruppe (light/group entity_id)
CONF_GROUP_CEILING: Final = "group_ceiling"            # Deckenlampe CCT
CONF_GROUP_ALL: Final = "group_all"                    # Hard-Off-Ziel
# Wake-only-Bereichs-Teardown (FLEET-151): Nicht-Wohnzimmer-Areas, die der
# Wecklicht-Look anschaltet (Schlafzimmer-Strips; Küche nur falls real im Look).
# Liste von AREA-IDs — die konkreten Lampen werden zur Laufzeit aus der
# Area-Zugehörigkeit aufgelöst (neue Lampe im Bereich = automatisch drin). Beim
# Verlassen eines Wake-Zustands (waking/work_home → Nicht-Wake) werden diese per
# direktem light.turn_off abgeräumt (formgleich zum GROUP_ALL-Hard-Off, kein Look).
CONF_WAKE_TEARDOWN_AREAS: Final = "wake_teardown_areas"

# Bereichs-Entities (R14–R17).
CONF_HALLWAY_LIGHT: Final = "hallway_light"
CONF_HALLWAY_TRIGGERS: Final = "hallway_trigger_entities"  # list[entity_id] Tür/Bewegung
CONF_BATHROOM_LIGHT: Final = "bathroom_light"
CONF_BATHROOM_VIBRATION: Final = "bathroom_vibration_entity"
CONF_RING_TARGETS: Final = "ring_target_entities"         # Aqara RGB Ringe (mehrere, simultan)
CONF_RING_PRESET_MAP: Final = "ring_preset_map"           # dict activity_state -> effect name

# --------------------------------------------------------------------------- #
# Subentries — typisierte Policies (Hub + Subentries-Architektur, 2026-05-29)
# --------------------------------------------------------------------------- #
SUBENTRY_GAMING: Final = "gaming"
SUBENTRY_MUSIC: Final = "music"
SUBENTRY_NOTIFICATION_RING: Final = "notification_ring"
SUBENTRY_HALLWAY: Final = "hallway"
SUBENTRY_BATHROOM: Final = "bathroom"
SUBENTRY_WAKE_UP: Final = "wake_up"
SUBENTRY_TYPES: Final = (
    SUBENTRY_GAMING, SUBENTRY_MUSIC, SUBENTRY_NOTIFICATION_RING,
    SUBENTRY_HALLWAY, SUBENTRY_BATHROOM, SUBENTRY_WAKE_UP,
)

# Generische Subentry-Config-Keys (je Subentry nur seine eigenen Felder).
CONF_CLASSIFIER_ENTITY: Final = "classifier_entity"   # Gaming/Musik: eigener Title-Classifier
CONF_REQUIRE_BIRTHDAY: Final = "require_birthday"      # Musik: nur bei Kalender-Thema geburtstag
CONF_BATHROOM_TIMEOUT: Final = "bathroom_timeout_seconds"
CONF_WAKE_UP_TARGETS: Final = "wake_up_targets"
# Minihub-Schema: ein Subentry = eine Policy-Kategorie mit interner Mapping-Tabelle.
CONF_SOURCE_ID: Final = "source_id"                   # z.B. "pc"/"ps5" — matched media_device
CONF_SOURCE_PRIORITY: Final = "source_priority"        # numerisch, kleiner = höher
CONF_MAPPINGS: Final = "mappings"                      # dict {classifier_value: preset_uuid}

# Mapping-Slots im Config-Flow (statisches Schema → feste Anzahl Slots).
MAPPING_SLOT_COUNT: Final = 8
MAPPING_VALUE_PREFIX: Final = "mapping_value_"
MAPPING_PRESET_PREFIX: Final = "mapping_preset_"

# Default-Prioritäten pro Quelle (alte Logik: PS5 > Nintendo > Cinema > PC).
GAMING_DEFAULT_PRIORITY: Final[dict[str, int]] = {
    "ps5": 9,
    "nintendo": 10,
    "pc": 12,
    # andere Quellen → 11 (gleich/zwischen Cinema), per Subentry editierbar
}

# Cinema feuert nur, wenn media_context auf TV-artige Kontexte zeigt
# (Spec-Tightening: §4.1 sagt nur entertainment_stable, das war zu lose).
TV_MEDIA_CONTEXTS: Final = frozenset({"tv", "streaming"})
# media_device-Wert, der einen Fernseher als aktive Quelle meldet (AppleTV/Video-Apps
# laufen über media_context = "streaming"). Dient als zweites positives TV-Signal,
# falls media_context (noch) nicht verdrahtet ist.
MEDIA_DEVICE_TV: Final = "tv"

# Foundation-Auto-Prefill: Hub-Felder werden mit den bekannten Core-Devices /
# Custom-Integration-Entity-IDs vorbelegt (falls vorhanden) — der User bestätigt
# nur, statt zu suchen. Geräte-spezifische Felder (Lux/Wetter/…) bleiben leer.
# Einzelwert-Entities. Werden nur vorbelegt, WENN die Entity in HA existiert →
# auf anderen Anlagen schadlos (greift einfach nicht). IDs aus der Live-Anlage
# (einhornzentrale) ermittelt: eindeutige Singletons brauchen kein Raussuchen.
ENTITY_PREFILL: Final[dict[str, str]] = {
    # Core-State PR #25/#31: Clean-IDs sind der kanonische Consumer-Contract.
    CONF_BIO_STATE: "sensor.benni_core_state_bio_state",
    CONF_ACTIVITY_STATE: "sensor.benni_core_state_activity_state",
    CONF_DAY_STATE: "sensor.benni_core_state_day_state",
    CONF_PRESENCE_PERSONAL: "sensor.benni_core_state_presence_personal",
    CONF_PRESENCE_HOUSEHOLD: "sensor.benni_core_state_presence_household",
    CONF_PRESENCE_TRANSITION: "sensor.benni_core_state_presence_transition",
    CONF_CALENDAR_THEME: "sensor.benni_core_state_day_context",
    CONF_LUX: "sensor.benni_device_garden_lux",
    # FLEET-36 Cut-over: Media-Truth kommt jetzt aus benni_media_state (L1-Feeder,
    # B2-Gate-Fix) statt aus dem alten Toolbox-Monolith benni_media_context.
    CONF_ENTERTAINMENT_STABLE: "binary_sensor.benni_media_state_entertainment_active",
    CONF_MEDIA_DEVICE: "sensor.benni_media_state_media_device",
    CONF_MEDIA_CONTEXT: "sensor.benni_media_state_media_context",
    # Parent Issue #33: the process-wide lifecycle gate is owned by Core State.
    # This remains a consumer binding only; Light Policy keeps its local
    # startup_block_seconds staging delay separate from the global timer.
    CONF_SYSTEM_READY: DEFAULT_SYSTEM_READY_ENTITY,
    CONF_SEASON: "sensor.benni_device_weather_season_meteorological",
}

# Lampengruppen sind Mengen von Einzellampen (keine HA-Group-Entity vorhanden).
GROUP_PREFILL: Final[dict[str, list[str]]] = {
    CONF_GROUP_MAIN: [
        "light.living_sideboard_table_lamp",
        "light.living_sofa_table_lamp",
        "light.living_cabinet_wall_strip",
        "light.living_sofa_wall_strip",
        "light.living_desk_strip_stripe",
    ],
    CONF_GROUP_CEILING: ["light.living_ceiling_light_white"],
    CONF_GROUP_ALL: [
        "light.living_sideboard_table_lamp",
        "light.living_sofa_table_lamp",
        "light.living_cabinet_wall_strip",
        "light.living_sofa_wall_strip",
        "light.living_desk_strip_stripe",
        "light.living_ceiling_light_white",
        # RGB-Ring des Deckenlichts: eigene light-Entity, MUSS im Hard-Off-Scope sein
        # (Aqara-Restart-Bug schaltet ihn sonst nach Neustart/idle dauerhaft an).
        "light.living_ceiling_light_rgb",
    ],
}

# Subentry-Felder, die sich eindeutig vorbelegen lassen (aktuell keine —
# Wake-Up-Subentry braucht Light-Liste, die ist installations-spezifisch).
SUBENTRY_PREFILL: Final[dict[str, str]] = {}

# Wake-only-Teardown-Areas — Default + Config-Flow-Prefill. Verifiziert gegen den
# Live-Wecklicht-Look (FLEET-151): nur Schlafzimmer ist aktuell im Look (Küche
# bleibt aus). Greift schadlos auf anderen Anlagen (Area fehlt → leere Auflösung).
DEFAULT_WAKE_TEARDOWN_AREAS: Final[tuple[str, ...]] = ("schlafzimmer",)
AREA_PREFILL: Final[dict[str, list[str]]] = {
    CONF_WAKE_TEARDOWN_AREAS: list(DEFAULT_WAKE_TEARDOWN_AREAS),
}

# Options.
CONF_APPLY_ENABLED: Final = "apply_enabled"
CONF_STARTUP_BLOCK_SECONDS: Final = "startup_block_seconds"
CONF_CROSSFADE_SECONDS: Final = "crossfade_seconds"
CONF_SCENE_INTERVAL_SECONDS: Final = "scene_interval_seconds"
CONF_LUX_THRESHOLDS: Final = "lux_thresholds"          # dict season -> {dark, bright}
CONF_BRIGHTNESS: Final = "brightness_profile"          # dict mode/phase -> 0..255
CONF_CUSTOM_THEMES: Final = "custom_themes"            # list[str] zusätzliche Matrix-Zeilen
# Zentrale Look-Map: policy_key -> Look-Ref (Slug ODER Name aus benni_scene_presets).
# Löst die Tagesphasen-/Modus-Keys (Unterstriche) auf echte Look-Refs auf, statt auf
# harte Namenskonventionen zu vertrauen. Mehrere Keys dürfen denselben Look nutzen.
CONF_LOOK_MAP: Final = "look_map"

# --------------------------------------------------------------------------- #
# Defaults & Konstanten (Lastenheft §8)
# --------------------------------------------------------------------------- #
DEFAULT_APPLY_ENABLED: Final = False        # Shadow-safe out of the box (Phase-4).
DEFAULT_STARTUP_BLOCK_SECONDS: Final = 15   # HA-Start-Delay.
DEFAULT_CROSSFADE_SECONDS: Final = 30
# Reine Brightness-Änderung (selber Look) → kurzer Fade statt Look-Default-Crossfade,
# damit Helligkeits-Edits im UX sofort sichtbar werden (nicht erst nach 60 s).
BRIGHTNESS_CHANGE_TRANSITION_SECONDS: Final = 2
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
    PHASE_MIDDAY: 255,
    PHASE_AFTERNOON: 255,
    PHASE_LATE_AFTERNOON: 220,
    PHASE_EARLY_EVENING: 220,
    PHASE_EVENING: 220,
    PHASE_LATE_EVENING: 200,
    PHASE_EARLY_NIGHT: 150,
    PHASE_LATE_NIGHT: 100,
    MODE_WORK_HOME: 220,
    MODE_PRIVATE_TIME: 80,
}

# Farbtemperaturen (Kelvin) für CCT-getriebene Modi; sonst Preset-getrieben.
COLOR_TEMP_WORK_HOME: Final = 5000
COLOR_TEMP_WAKING: Final = 6500

# Bereichs-Konstanten (R14–R17).
HALLWAY_TIMER_SECONDS: Final = 120          # 2-Min-Auto-Off (R14)
HALLWAY_OFF_REPEATS: Final = 3              # 3x Turn-Off mit Abstand (Zigbee)
HALLWAY_OFF_REPEAT_DELAY: Final = 3         # Sekunden zwischen den Off-Befehlen
HALLWAY_COLOR_TEMP: Final = 3000
BATHROOM_TIMEOUT_SECONDS: Final = 3600       # 60-Min-Vergessensschutz (R15)

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
UID_MANUAL_OFF: Final = "manual_off_living_room"
UID_APPLY_ENABLED: Final = "apply_enabled"

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

# Scene-Presets-Integration (extern, eigene Domain — benni_scene_presets-Fork).
# Apply läuft über die Look-Ebene: ein Look ist die deploybare Einheit (trägt Targets,
# Bindings, Off-Bindings, Crossfade) und wird per Name ODER Slug referenziert. Die Policy
# liefert die Look-Ref (über preset_enum) + Brightness aus der Tagesphase.
SCENE_PRESETS_DOMAIN: Final = "benni_scene_presets"
SP_SERVICE_APPLY_LOOK: Final = "apply_look"
SP_SERVICE_STOP_LOOK: Final = "stop_look"
SP_ATTR_LOOK: Final = "look"          # Service-Feld: Look-Name oder -Slug
SP_ATTR_BRIGHTNESS: Final = "brightness"
SP_ATTR_TRANSITION: Final = "transition"  # First-Paint-Fade-Override (s); leer = Look-Default
# WS-Command des Forks, über das das Panel die echten Looks (Slug+Name) holt.
SP_WS_LIST_LOOKS: Final = "benni_scene_presets/list_looks"

# --------------------------------------------------------------------------- #
# Panel / WebSocket-API (eigenes Dashboard-Frontend)
# --------------------------------------------------------------------------- #
PANEL_URL_PATH: Final = "benni_light_policy"          # Sidebar-Eintrag
PANEL_TITLE: Final = "Light Policy"
PANEL_ICON: Final = "mdi:lightbulb-auto"
FRONTEND_DIR_URL: Final = "/benni_light_policy_app"   # statisch ausgelieferte App
FRONTEND_ENTRY: Final = f"{FRONTEND_DIR_URL}/main.js"
PANEL_ELEMENT: Final = "blp-app"

# WS-Commands (Namespace = Domain).
WS_GET_STATUS: Final = f"{DOMAIN}/get_status"
WS_GET_LOOK_MAP: Final = f"{DOMAIN}/get_look_map"
WS_SET_LOOK_MAP: Final = f"{DOMAIN}/set_look_map"
WS_SET_SUBENTRY_MAPPINGS: Final = f"{DOMAIN}/set_subentry_mappings"
WS_SET_APPLY_ENABLED: Final = f"{DOMAIN}/set_apply_enabled"
WS_SET_BRIGHTNESS_PROFILE: Final = f"{DOMAIN}/set_brightness_profile"
WS_SET_CUSTOM_THEMES: Final = f"{DOMAIN}/set_custom_themes"
