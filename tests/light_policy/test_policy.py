"""Pure-engine tests für policy.lux_gate() und policy.decide()."""
from __future__ import annotations

import lp_const as C
import lp_policy as P


def _ctx(**kw):
    return P.Context(**kw)


def _decide(ctx, **kw):
    defaults = dict(
        lux_gate_on=True,
        startup_ready=True,
        apply_enabled=True,
        manual_off_active=False,
    )
    defaults.update(kw)
    return P.decide(ctx, **defaults)


# ---------------------------------------------------------------- lux gate
def test_lux_gate_dark_opens():
    assert P.lux_gate(100, C.SEASON_WINTER, None, day_state_known=True) is True


def test_lux_gate_bright_closes():
    assert P.lux_gate(900, C.SEASON_WINTER, None, day_state_known=True) is False


def test_lux_gate_hysteresis_holds_between_thresholds():
    # Winter: dark=250, bright=400. 300 liegt dazwischen → prev halten.
    assert P.lux_gate(300, C.SEASON_WINTER, True, day_state_known=True) is True
    assert P.lux_gate(300, C.SEASON_WINTER, False, day_state_known=True) is False


def test_lux_gate_day_state_unknown_closes():
    assert P.lux_gate(10, C.SEASON_WINTER, True, day_state_known=False) is False


def test_lux_gate_lux_unavailable_holds_prev():
    assert P.lux_gate(None, C.SEASON_WINTER, True, day_state_known=True) is True
    assert P.lux_gate(None, C.SEASON_WINTER, None, day_state_known=True) is False


def test_lux_gate_seasonal_threshold_differs():
    # Sommer dark=400: 380 → an. Winter dark=250: 380 → (zwischen 250/400) hält prev.
    assert P.lux_gate(380, C.SEASON_SUMMER, None, day_state_known=True) is True
    assert P.lux_gate(380, C.SEASON_WINTER, False, day_state_known=True) is False


def test_lux_gate_without_tmc_no_hysteresis():
    # TMC nicht gesetzt → einfacher Vergleich: zwischen den Schwellen = aus (kein Halten).
    assert P.lux_gate(300, C.SEASON_WINTER, True, day_state_known=True, tmc_set=False) is False
    assert P.lux_gate(200, C.SEASON_WINTER, None, day_state_known=True, tmc_set=False) is True


def test_lux_gate_weather_dark_forces_open():
    # Heller Lux (Gate sonst zu) aber wetterbedingte Dunkelheit → offen.
    assert P.lux_gate(900, C.SEASON_SUMMER, False, day_state_known=True, weather_dark=True) is True


# ---------------------------------------------------------------- weather darkness (R10)
def test_weather_darkness_triggers_on_drop_and_dark_icon():
    assert P.weather_darkness(200, 1000, "rainy", "midday") is True


def test_weather_darkness_needs_daytime():
    assert P.weather_darkness(200, 1000, "rainy", "evening") is False


def test_weather_darkness_needs_dark_icon():
    assert P.weather_darkness(200, 1000, "sunny", "midday") is False


def test_weather_darkness_small_drop_no_trigger():
    assert P.weather_darkness(800, 1000, "cloudy", "morning") is False


# ---------------------------------------------------------------- bedtime / hallway predicates
def test_bedtime_signal_due():
    assert P.bedtime_signal_due("late_night", "awake", 900) is True
    assert P.bedtime_signal_due("late_night", "awake", 800) is False   # < 14h
    assert P.bedtime_signal_due("afternoon", "awake", 900) is False    # falsche Phase
    assert P.bedtime_signal_due("early_night", "sleep", 900) is False  # schläft
    assert P.bedtime_signal_due("late_night", "awake", None) is False


def test_hallway_should_light():
    assert P.hallway_should_light(True, True) is True
    assert P.hallway_should_light(True, False) is False   # zu hell
    assert P.hallway_should_light(False, True) is False   # kein Trigger


# ---------------------------------------------------------------- wake-exit teardown (FLEET-151)
def test_wake_exit_fires_waking_to_awake():
    # Kern-Fall: waking→awake (Tagesphasen-Fallback) → Teardown der Wake-Areas.
    assert P.wake_exit(C.MODE_WAKING, "early_morning") is True


def test_wake_exit_fires_from_work_home():
    # work_home mappt ebenfalls auf Wecklicht → Exit räumt auch hier ab.
    assert P.wake_exit(C.MODE_WORK_HOME, C.MODE_IDLE) is True


def test_wake_exit_no_fire_within_wake():
    # waking↔work_home bleiben Wake → kein Teardown (kein Flicker, Lampen bleiben).
    assert P.wake_exit(C.MODE_WAKING, C.MODE_WORK_HOME) is False
    assert P.wake_exit(C.MODE_WAKING, C.MODE_WAKING) is False


def test_wake_exit_no_fire_when_not_in_wake():
    # Kein vorheriger Wake-Zustand → nie Teardown (auch nach Restart: prev=None).
    assert P.wake_exit(None, "afternoon") is False
    assert P.wake_exit("cinema", C.MODE_IDLE) is False
    assert P.wake_exit("afternoon", C.MODE_WAKING) is False  # Eintritt ≠ Austritt


def test_wake_modes_membership():
    assert C.MODE_WAKING in P.WAKE_MODES
    assert C.MODE_WORK_HOME in P.WAKE_MODES
    assert C.MODE_IDLE not in P.WAKE_MODES


# ---------------------------------------------------------------- decision chain
def test_waking_overrides_everything():
    gaming = P.make_gaming_policy("pc", "1", {"1": "Hearthstone"}, priority=0)
    p = _decide(
        _ctx(
            bio_state=C.BIO_WAKING,
            activity_state=C.ACTIVITY_GAMING,
            day_state="late_night",
            media_device="pc",
        ),
        lux_gate_on=False,
        extra_policies=[gaming],
    )
    assert p.mode == C.MODE_WAKING
    assert p.apply_kind == P.APPLY_CCT
    assert p.color_temp == C.COLOR_TEMP_WAKING
    assert p.preset_enum == C.MODE_WAKING   # Look-Ref → Kelvin-Look "waking"
    assert p.lux_gate_on is False


def test_sleep_hard_off():
    p = _decide(_ctx(bio_state=C.BIO_SLEEP))
    assert p.mode == C.MODE_IDLE
    assert p.apply_kind == P.APPLY_OFF
    assert p.brightness == 0
    assert p.exclusive_off == [C.GROUP_ALL]


def test_lux_gate_off_hard_off():
    p = _decide(_ctx(bio_state=C.BIO_AWAKE, activity_state=C.ACTIVITY_PRIVATE_TIME), lux_gate_on=False)
    assert p.mode == C.MODE_IDLE
    assert p.apply_kind == P.APPLY_OFF
    assert p.exclusive_off == [C.GROUP_ALL]


def test_gaming_source_priority_below_lux_cannot_beat_hard_off():
    ctx = _ctx(
        bio_state=C.BIO_AWAKE,
        activity_state=C.ACTIVITY_GAMING,
        day_state=C.PHASE_LATE_EVENING,
        season=C.SEASON_SUMMER,
        media_device="pc",
    )
    for priority in (0, 1, 2):
        gaming = P.make_gaming_policy("pc", "1", {"1": "Hearthstone"}, priority=priority)
        p = _decide(ctx, lux_gate_on=False, extra_policies=[gaming])
        assert p.mode == C.MODE_IDLE
        assert p.apply_kind == P.APPLY_OFF
        assert p.exclusive_off == [C.GROUP_ALL]
        assert p.lux_gate_on is False


def test_gaming_source_priority_zero_still_fires_when_lux_allows_light():
    gaming = P.make_gaming_policy("pc", "1", {"1": "Hearthstone"}, priority=0)
    p = _decide(
        _ctx(
            activity_state=C.ACTIVITY_GAMING,
            day_state=C.PHASE_LATE_EVENING,
            season=C.SEASON_SUMMER,
            media_device="pc",
        ),
        lux_gate_on=True,
        extra_policies=[gaming],
    )
    assert gaming.priority == P.PRIO_IDLE_LUX
    assert p.mode == "gaming:pc:1"
    assert p.preset_enum == "Hearthstone"
    assert p.apply_kind == P.APPLY_SCENE
    assert p.lux_gate_on is True


def test_sleep_hard_off_remains_above_gaming_priority():
    gaming = P.make_gaming_policy("pc", "1", {"1": "Hearthstone"}, priority=0)
    p = _decide(
        _ctx(
            bio_state=C.BIO_SLEEP,
            activity_state=C.ACTIVITY_GAMING,
            day_state=C.PHASE_LATE_EVENING,
            media_device="pc",
        ),
        lux_gate_on=True,
        extra_policies=[gaming],
    )
    assert p.mode == C.MODE_IDLE
    assert p.apply_kind == P.APPLY_OFF
    assert p.exclusive_off == [C.GROUP_ALL]


def test_hard_off_carries_idle_look_key():
    # FLEET-142: Off-Zustand trägt preset_enum=idle, damit er über die Look-Map
    # auf den all_off-Look auflösbar ist (Warden-Vokabular). Apply selbst bleibt
    # fail-safe direktes turn_off — der Key ändert das nicht.
    sleep = _decide(_ctx(bio_state=C.BIO_SLEEP))
    lux = _decide(_ctx(bio_state=C.BIO_AWAKE, activity_state=C.ACTIVITY_PRIVATE_TIME), lux_gate_on=False)
    assert sleep.preset_enum == C.MODE_IDLE
    assert lux.preset_enum == C.MODE_IDLE
    assert C.MODE_IDLE in C.POLICY_FIXED_MODES


def test_private_time():
    p = _decide(_ctx(activity_state=C.ACTIVITY_PRIVATE_TIME, day_state="late_evening"))
    assert p.mode == C.MODE_PRIVATE_TIME
    assert p.targets == [C.GROUP_MAIN]
    assert C.GROUP_CEILING in p.exclusive_off
    assert p.brightness == 80


def test_work_home_cct():
    p = _decide(_ctx(activity_state=C.ACTIVITY_WORK_HOME))
    assert p.mode == C.MODE_WORK_HOME
    assert p.color_temp == C.COLOR_TEMP_WORK_HOME
    assert p.apply_kind == P.APPLY_CCT
    assert p.preset_enum == C.MODE_WORK_HOME   # Look-Ref → Kelvin-Look "work_home"


def test_household_uses_dayphase_preset():
    p = _decide(_ctx(activity_state=C.ACTIVITY_HOUSEHOLD, day_state="early_evening", season=C.SEASON_AUTUMN))
    assert p.mode == C.MODE_HOUSEHOLD
    assert p.preset_enum == "autumn_early_evening"


def test_presence_sim():
    p = _decide(_ctx(
        presence_personal=C.PRESENCE_AWAY, day_state="late_evening",
        season=C.SEASON_SUMMER, activity_state=C.ACTIVITY_IDLE,
    ))
    assert p.mode == C.MODE_PRESENCE_SIM
    assert p.preset_enum == "summer_late_evening"


def test_presence_sim_suppressed_by_overnight_away():
    p = _decide(_ctx(
        presence_personal=C.PRESENCE_AWAY, day_state="late_evening",
        season=C.SEASON_SUMMER, overnight_away=True,
    ))
    assert p.mode != C.MODE_PRESENCE_SIM


def test_presence_sim_ends_on_coming_home():
    # R12: coming_home beendet die Simulation sofort.
    p = _decide(_ctx(
        presence_personal=C.PRESENCE_AWAY, day_state="late_evening",
        season=C.SEASON_SUMMER, activity_state=C.ACTIVITY_IDLE,
        presence_transition=C.PRESENCE_TRANSITION_COMING_HOME,
    ))
    assert p.mode != C.MODE_PRESENCE_SIM


def test_gaming_requires_subentry_policy():
    # Ohne Gaming-Subentry tut der Title-Classifier nichts (gaming nicht mehr im Kern).
    p = _decide(_ctx(activity_state=C.ACTIVITY_FREE_TIME, day_state="early_night"))
    assert p.mode == "early_night"  # Tagesphase-Fallback, kein gaming


def test_cinema_blocked_by_guest():
    base = dict(entertainment_stable=True, activity_state=C.ACTIVITY_FREE_TIME, day_state="late_evening")
    assert _decide(_ctx(**base)).mode == C.MODE_CINEMA
    assert _decide(_ctx(guest=True, **base)).mode != C.MODE_CINEMA


def test_dayphase_fallback():
    p = _decide(_ctx(activity_state=C.ACTIVITY_FREE_TIME, day_state="late_night", season=C.SEASON_WINTER))
    assert p.mode == "late_night"
    assert p.preset_enum == "winter_late_night"
    assert p.brightness == 100


def test_event_theme_overrides_season():
    p = _decide(_ctx(activity_state=C.ACTIVITY_IDLE, day_state="early_evening", season=C.SEASON_AUTUMN, calendar_theme="weihnachten"))
    assert p.preset_enum == "christmas_early_evening"


def test_carnival_event_theme_overrides_season():
    p = _decide(_ctx(
        activity_state=C.ACTIVITY_IDLE,
        day_state="early_evening",
        season=C.SEASON_AUTUMN,
        calendar_theme="karneval",
    ))
    assert p.preset_enum == "carnival_early_evening"


def test_theme_phase_brightness_overrides_phase_default():
    p = _decide(
        _ctx(activity_state=C.ACTIVITY_IDLE, day_state="late_night", season=C.SEASON_WINTER),
        brightness_profile={"late_night": 100, "winter_late_night": 42},
    )
    assert p.preset_enum == "winter_late_night"
    assert p.brightness == 42


# ---------------------------------------------------------------- gating overlay
def test_apply_disabled_blocks_without_changing_plan():
    p = _decide(_ctx(activity_state=C.ACTIVITY_WORK_HOME), apply_enabled=False)
    assert p.mode == C.MODE_WORK_HOME       # Plan unverändert
    assert p.apply_allowed is False
    assert "apply_disabled" in p.blockers


def test_startup_block():
    p = _decide(_ctx(activity_state=C.ACTIVITY_WORK_HOME), startup_ready=False)
    assert p.mode == C.MODE_WORK_HOME
    assert p.preset_enum is not None
    assert p.brightness is not None
    assert p.lux_gate_on is True
    assert p.apply_allowed is False
    assert "startup_block" in p.blockers


def test_manual_off_hold_wins():
    p = _decide(_ctx(bio_state=C.BIO_SLEEP), manual_off_active=True)
    assert p.mode == C.MODE_IDLE            # Modus weiter berechnet
    assert p.apply_allowed is False         # aber kein Hard-Off
    assert "manual_off" in p.blockers


# ---------------------------------------------------------------- scene hash
def test_scene_hash_stable_and_changes():
    a = _decide(_ctx(activity_state=C.ACTIVITY_FREE_TIME, day_state="late_night", season=C.SEASON_WINTER))
    b = _decide(_ctx(activity_state=C.ACTIVITY_FREE_TIME, day_state="late_night", season=C.SEASON_WINTER))
    assert a.scene_hash == b.scene_hash and len(a.scene_hash) == 16
    c = _decide(_ctx(activity_state=C.ACTIVITY_FREE_TIME, day_state="early_night", season=C.SEASON_WINTER))
    assert c.scene_hash != a.scene_hash


def test_scene_hash_ignores_gating():
    on = _decide(_ctx(activity_state=C.ACTIVITY_WORK_HOME))
    off = _decide(_ctx(activity_state=C.ACTIVITY_WORK_HOME), apply_enabled=False)
    assert on.scene_hash == off.scene_hash


# ---------------------------------------------------------------- policy registry (Phase 1)
def test_registry_priorities_ascending_and_unique():
    prios = [p.priority for p in P.LIVING_ROOM_POLICIES]
    assert prios == sorted(prios)
    assert len(prios) == len(set(prios))


def test_registry_kinds_are_core_only():
    # Kern-Policies (ohne gaming/music_party → die kommen per Subentry).
    assert P.POLICY_KINDS == (
        "waking", "idle_sleep", "idle_lux", "private_time", "work_home",
        "household", "presence_sim", "cinema", "dayphase",
    )


def test_gaming_subentry_policy_wins_over_dayphase():
    # Minihub: source_id="pc" + classifier_value="ow" + Mapping → Preset.
    pol = P.make_gaming_policy("pc", "ow", {"ow": "games_overwatch_2"})
    p = _decide(
        _ctx(activity_state=C.ACTIVITY_FREE_TIME, day_state="early_night",
             season=C.SEASON_WINTER, media_device="pc"),
        extra_policies=[pol],
    )
    assert p.mode == "gaming:pc:ow"
    assert p.preset_enum == "games_overwatch_2"


def test_gaming_brightness_follows_dayphase_profile():
    # Regression: Gaming-Look muss die Tagesphasen-/Theme-Helligkeit nutzen,
    # nicht None (sonst scene_presets-Default 255). Bug 2026-06-09.
    pol = P.make_gaming_policy("pc", "2", {"2": "overwatch"})
    p = _decide(
        _ctx(activity_state=C.ACTIVITY_FREE_TIME, day_state="late_night",
             season=C.SEASON_SUMMER, media_device="pc"),
        extra_policies=[pol],
        brightness_profile={"late_night": 100, "summer_late_night": 80},
    )
    assert p.mode == "gaming:pc:2"
    assert p.preset_enum == "overwatch"
    assert p.brightness == 80  # theme_phase-Override gewinnt; NICHT None/255


def test_gaming_subentry_inactive_when_source_not_active():
    # Gleiche Subentry, aber media_device zeigt nicht auf "pc" → kein Match.
    pol = P.make_gaming_policy("pc", "ow", {"ow": "games_overwatch_2"})
    p = _decide(
        _ctx(activity_state=C.ACTIVITY_FREE_TIME, day_state="early_night",
             season=C.SEASON_WINTER, media_device="none"),
        extra_policies=[pol],
    )
    assert p.mode == "early_night"  # Fallback


def test_gaming_subentry_inactive_when_value_unmapped():
    # PC ist aktive Quelle, aber Classifier-Wert nicht im Mapping → kein Match.
    pol = P.make_gaming_policy("pc", "something_else", {"ow": "games_overwatch_2"})
    p = _decide(
        _ctx(activity_state=C.ACTIVITY_FREE_TIME, day_state="early_night",
             season=C.SEASON_WINTER, media_device="pc"),
        extra_policies=[pol],
    )
    assert p.mode == "early_night"


def test_gaming_subentry_yields_to_higher_priority_core():
    # work_home (Prio 5) schlägt gaming (Prio 9) — auch wenn PC aktiv ist.
    pol = P.make_gaming_policy("pc", "ow", {"ow": "games_overwatch_2"})
    p = _decide(
        _ctx(activity_state=C.ACTIVITY_WORK_HOME, day_state="early_night",
             media_device="pc"),
        extra_policies=[pol],
    )
    assert p.mode == C.MODE_WORK_HOME


def test_multi_source_priority_ps5_beats_pc():
    # Beide Subentries existieren, PS5 hat höhere Prio. media_device steht aber
    # nur auf einer Quelle gleichzeitig — der Test prüft Co-Existenz + dass nur
    # die aktive Quelle matched (kein Crosstalk).
    pc_pol = P.make_gaming_policy("pc", "0", {"0": "uuid-prod"}, priority=12)
    ps5_pol = P.make_gaming_policy("ps5", "0", {"0": "uuid-ps5"}, priority=9)
    # PS5 aktiv → PS5-Plan, PC-Subentry inaktiv weil media_device=ps5
    p = _decide(
        _ctx(activity_state=C.ACTIVITY_FREE_TIME, day_state="early_night",
             season=C.SEASON_WINTER, media_device="ps5"),
        extra_policies=[pc_pol, ps5_pol],
    )
    assert p.preset_enum == "uuid-ps5"


# --- Gaming-Activity-Gate (Fix 2026-08-05) --------------------------------- #
# Regression: Der Activity-State-Vertrag (benni_core_state) liefert bei aktivem
# Spiel `gaming` (nicht mehr `free_time`). Das alte Gate ACTIVITY_PRESET_DRIVING
# blockierte dadurch die Gaming-Policy für JEDES Spiel. Eigenes Gate
# GAMING_ACTIVITY_STATES lässt `gaming` (+ Rückwärtskompat free_time/idle) zu,
# `pc_active` bleibt draußen. Live-Enum→Look (pc): 1=Hearthstone, 2=Overwatch.
_GAMES = {"1": "Hearthstone", "2": "Overwatch"}


def test_gaming_fires_on_gaming_state_enum1_hearthstone():
    pol = P.make_gaming_policy("pc", "1", _GAMES)
    p = _decide(
        _ctx(activity_state=C.ACTIVITY_GAMING, day_state="late_evening",
             season=C.SEASON_SUMMER, media_device="pc"),
        extra_policies=[pol],
    )
    assert p.mode == "gaming:pc:1"
    assert p.preset_enum == "Hearthstone"


def test_gaming_fires_on_gaming_state_enum2_overwatch():
    pol = P.make_gaming_policy("pc", "2", _GAMES)
    p = _decide(
        _ctx(activity_state=C.ACTIVITY_GAMING, day_state="late_evening",
             season=C.SEASON_SUMMER, media_device="pc"),
        extra_policies=[pol],
    )
    assert p.mode == "gaming:pc:2"
    assert p.preset_enum == "Overwatch"


def test_gaming_wrong_source_no_look_while_gaming():
    # Aktives Gaming, aber media_device zeigt nicht auf die Subentry-Quelle.
    pol = P.make_gaming_policy("pc", "1", _GAMES)
    p = _decide(
        _ctx(activity_state=C.ACTIVITY_GAMING, day_state="late_evening",
             season=C.SEASON_SUMMER, media_device="ps5"),
        extra_policies=[pol],
    )
    assert p.mode == "late_evening"  # Tagesphasen-Fallback, kein Gaming-Look


def test_gaming_unknown_mapping_no_look_while_gaming():
    # Aktive Quelle + Gaming, aber Enum-Wert nicht im Mapping.
    pol = P.make_gaming_policy("pc", "3", _GAMES)
    p = _decide(
        _ctx(activity_state=C.ACTIVITY_GAMING, day_state="late_evening",
             season=C.SEASON_SUMMER, media_device="pc"),
        extra_policies=[pol],
    )
    assert p.mode == "late_evening"


def test_gaming_non_string_mapping_no_look_while_gaming():
    pol = P.make_gaming_policy("pc", "1", {"1": 123})
    p = _decide(
        _ctx(activity_state=C.ACTIVITY_GAMING, day_state="late_evening",
             season=C.SEASON_SUMMER, media_device="pc"),
        extra_policies=[pol],
    )
    assert p.mode == "late_evening"


def test_gaming_missing_classifier_value_no_look_while_gaming():
    pol = P.make_gaming_policy("pc", None, {"": "Hearthstone"})
    p = _decide(
        _ctx(activity_state=C.ACTIVITY_GAMING, day_state="late_evening",
             season=C.SEASON_SUMMER, media_device="pc"),
        extra_policies=[pol],
    )
    assert p.mode == "late_evening"


def test_gaming_pc_active_alone_stays_blocked():
    # `pc_active` = nur „PC an" (ohne Gaming-Kontext) → KEIN Gaming-Look, selbst
    # wenn Quelle + Enum-Mapping passen. Bewusst außerhalb GAMING_ACTIVITY_STATES.
    pol = P.make_gaming_policy("pc", "1", _GAMES)
    p = _decide(
        _ctx(activity_state=C.ACTIVITY_PC_ACTIVE, day_state="late_evening",
             season=C.SEASON_SUMMER, media_device="pc"),
        extra_policies=[pol],
    )
    assert p.mode == "late_evening"


def test_gaming_backward_compat_free_time_still_fires():
    # Rückwärtskompatibilität: `free_time` löst die Gaming-Policy weiterhin aus.
    pol = P.make_gaming_policy("pc", "1", _GAMES)
    p = _decide(
        _ctx(activity_state=C.ACTIVITY_FREE_TIME, day_state="late_evening",
             season=C.SEASON_SUMMER, media_device="pc"),
        extra_policies=[pol],
    )
    assert p.mode == "gaming:pc:1"
    assert p.preset_enum == "Hearthstone"


def test_music_gate_unchanged_by_gaming_state():
    # Schutz gegen versehentliche Gate-Verbreiterung: die Musik-Policy nutzt
    # weiterhin ACTIVITY_PRESET_DRIVING, `gaming` darf sie NICHT auslösen —
    # selbst mit passendem Geburtstag + Mapping.
    pol = P.make_music_policy("party", {"party": "disco-uuid"})
    p = _decide(
        _ctx(activity_state=C.ACTIVITY_GAMING, calendar_theme="geburtstag",
             day_state="late_evening"),
        extra_policies=[pol],
    )
    assert p.mode != C.MODE_MUSIC_PARTY


def test_music_subentry_minihub():
    pol = P.make_music_policy("party", {"party": "disco-uuid", "rock": "rock-uuid"})
    base = dict(activity_state=C.ACTIVITY_IDLE, day_state="late_evening")
    # Birthday + Match → music_party.
    plan = _decide(_ctx(calendar_theme="geburtstag", **base), extra_policies=[pol])
    assert plan.mode == C.MODE_MUSIC_PARTY
    assert plan.preset_enum == "disco-uuid"
    # Ohne Birthday → Music inaktiv.
    assert _decide(_ctx(**base), extra_policies=[pol]).mode != C.MODE_MUSIC_PARTY


def test_cinema_requires_tv_media_context():
    base = dict(entertainment_stable=True, activity_state=C.ACTIVITY_FREE_TIME,
                day_state="late_evening")
    # TV → Cinema feuert.
    assert _decide(_ctx(media_context="tv", **base)).mode == C.MODE_CINEMA
    # Gaming-Kontext (PC an, kein Spiel) → kein Cinema mehr.
    assert _decide(_ctx(media_context="gaming", **base)).mode != C.MODE_CINEMA
    # media_context unkonfiguriert (None) → Backward-Compat, alte Regel feuert.
    assert _decide(_ctx(**base)).mode == C.MODE_CINEMA


def test_cinema_not_hijacked_by_gaming_media_device():
    # Regression: media_context (noch) nicht verdrahtet, aber media_device verrät
    # eine Gaming-Quelle → Cinema darf NICHT feuern (sonst kapert PC-Betrieb das
    # Wohnzimmerlicht, weil Cinema-Prio über PC-Gaming liegt).
    base = dict(entertainment_stable=True, activity_state=C.ACTIVITY_FREE_TIME,
                day_state="late_evening")
    assert _decide(_ctx(media_device="pc", **base)).mode != C.MODE_CINEMA
    # media_device meldet TV → positives Signal → Cinema feuert auch ohne media_context.
    assert _decide(_ctx(media_device="tv", **base)).mode == C.MODE_CINEMA


def test_away_is_hard_off_with_open_lux_gate():
    p = _decide(_ctx(
        bio_state=C.BIO_AWAKE,
        presence_personal=C.PRESENCE_AWAY,
        day_state=C.PHASE_AFTERNOON,
        season=C.SEASON_SUMMER,
    ), lux_gate_on=True)
    assert p.mode == C.MODE_IDLE
    assert p.apply_kind == P.APPLY_OFF
    assert "presence_personal away/parents" in p.reason


def test_away_is_hard_off_with_closed_lux_gate():
    p = _decide(_ctx(
        bio_state=C.BIO_AWAKE,
        presence_personal=C.PRESENCE_AWAY,
        day_state=C.PHASE_AFTERNOON,
        season=C.SEASON_SUMMER,
    ), lux_gate_on=False)
    assert p.mode == C.MODE_IDLE
    assert p.apply_kind == P.APPLY_OFF


def test_presence_simulation_remains_the_away_exception():
    p = _decide(_ctx(
        bio_state=C.BIO_AWAKE,
        presence_personal=C.PRESENCE_AWAY,
        activity_state=C.ACTIVITY_IDLE,
        day_state=C.PHASE_LATE_EVENING,
        season=C.SEASON_SUMMER,
    ), lux_gate_on=True)
    assert p.mode == C.MODE_PRESENCE_SIM


def test_new_core_day_phases_are_accepted():
    for phase in C.CORE_DAY_PHASES:
        p = _decide(_ctx(activity_state=C.ACTIVITY_IDLE, day_state=phase))
        assert p.mode == phase
        assert p.preset_enum == f"winter_{phase}"


def test_event_theme_contract_values_override_season():
    for theme in (
        "geburtstag", "silvester", "pride", "advent_1", "advent_2", "advent_3",
        "advent_4", "stpatricks",
    ):
        p = _decide(_ctx(
            activity_state=C.ACTIVITY_IDLE,
            day_state=C.PHASE_EVENING,
            season=C.SEASON_WINTER,
            calendar_theme=theme,
        ))
        assert p.preset_enum == f"{theme}_{C.PHASE_EVENING}"


def test_gaming_invalid_activity_values_are_safe():
    pol = P.make_gaming_policy("pc", "1", {"1": "Hearthstone"})
    for activity in (None, "unknown", "unavailable"):
        p = _decide(_ctx(
            activity_state=activity,
            day_state=C.PHASE_LATE_EVENING,
            media_device="pc",
        ), extra_policies=[pol])
        assert p.mode == C.PHASE_LATE_EVENING


def test_gaming_idle_compatibility_is_preserved():
    pol = P.make_gaming_policy("pc", "1", {"1": "Hearthstone"})
    p = _decide(_ctx(
        activity_state=C.ACTIVITY_IDLE,
        day_state=C.PHASE_LATE_EVENING,
        media_device="pc",
    ), extra_policies=[pol])
    assert p.preset_enum == "Hearthstone"


def test_invalid_thresholds_fall_back_without_crashing():
    invalid = {
        C.SEASON_WINTER: {"dark": 500, "bright": 100},
        C.SEASON_SUMMER: {"dark": "not-a-number"},
    }
    assert P.lux_gate(100, C.SEASON_WINTER, False, day_state_known=True, thresholds=invalid)
    normalized = P.normalize_lux_thresholds(invalid)
    assert normalized[C.SEASON_WINTER] == C.DEFAULT_LUX_THRESHOLDS[C.SEASON_WINTER]
    assert normalized[C.SEASON_SUMMER] == C.DEFAULT_LUX_THRESHOLDS[C.SEASON_SUMMER]


def test_brightness_and_priority_validation_preserve_safe_values():
    assert P.normalize_brightness_profile({"late_night": 400, "bad": "x", "flag": True}) == {
        "late_night": 255,
    }
    assert P.resolve_priority(0, 12) == 0
    assert P.resolve_priority("invalid", 12) == 12


def test_dayphase_policy_is_terminal():
    # Letzte Policy liefert immer einen Plan (kein None).
    last = P.LIVING_ROOM_POLICIES[-1]
    assert last.kind == "dayphase"
    assert last.evaluate(_ctx(day_state="late_night"), True, dict(C.DEFAULT_BRIGHTNESS)) is not None


# ------------------------------------------------ FLEET-74 Cross-Area-Teardown
def test_stranded_wake_up_to_dayphase_turns_off_cross_area():
    # waking→awake: Wecklicht-Lampen (Schlafzimmer/Küche) waren roh an, neuer
    # Wohnzimmer-Look besitzt sie nicht → sie stranden und müssen aus.
    prev = ["light.bedroom_ceiling", "light.kitchen_strip"]
    owned = ["light.living_main"]  # resolved plan.targets des Wohnzimmer-Looks
    assert P.stranded_entities(prev, owned) == [
        "light.bedroom_ceiling", "light.kitchen_strip",
    ]


def test_stranded_wake_up_to_wake_up_keeps_shared_lamp():
    # Geteilte Lampe bleibt an, nur die entfallene strandet.
    prev = ["light.bedroom_ceiling", "light.kitchen_strip"]
    keep = ["light.bedroom_ceiling"]
    assert P.stranded_entities(prev, keep) == ["light.kitchen_strip"]


def test_stranded_empty_when_nothing_commanded():
    # dayphase→dayphase: voriger Apply hatte keine rohen Targets → kein Diff.
    assert P.stranded_entities([], ["light.living_main"]) == []


def test_stranded_hard_off_drops_everything_not_in_group_all():
    # →Hard-Off: owned = GROUP_ALL (Wohnzimmer), Cross-Area-Rest strandet.
    prev = ["light.living_main", "light.bedroom_ceiling"]
    group_all = ["light.living_main", "light.living_ceiling"]
    assert P.stranded_entities(prev, group_all) == ["light.bedroom_ceiling"]


def test_stranded_dedupes_and_preserves_order():
    prev = ["light.b", "light.a", "light.b", "light.c"]
    assert P.stranded_entities(prev, ["light.c"]) == ["light.b", "light.a"]
