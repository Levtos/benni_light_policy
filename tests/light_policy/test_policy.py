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


# ---------------------------------------------------------------- decision chain
def test_waking_overrides_everything():
    p = _decide(_ctx(bio_state=C.BIO_WAKING, day_state="late_night"), lux_gate_on=False)
    assert p.mode == C.MODE_WAKING
    assert p.apply_kind == P.APPLY_CCT
    assert p.color_temp == C.COLOR_TEMP_WAKING
    assert p.preset_enum == C.MODE_WAKING   # Look-Ref → Kelvin-Look "waking"


def test_sleep_hard_off():
    p = _decide(_ctx(bio_state=C.BIO_SLEEP))
    assert p.mode == C.MODE_IDLE
    assert p.apply_kind == P.APPLY_OFF
    assert p.brightness == 0


def test_lux_gate_off_hard_off():
    p = _decide(_ctx(bio_state=C.BIO_AWAKE, activity_state=C.ACTIVITY_PRIVATE_TIME), lux_gate_on=False)
    assert p.mode == C.MODE_IDLE
    assert p.apply_kind == P.APPLY_OFF


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


def test_dayphase_policy_is_terminal():
    # Letzte Policy liefert immer einen Plan (kein None).
    last = P.LIVING_ROOM_POLICIES[-1]
    assert last.kind == "dayphase"
    assert last.evaluate(_ctx(day_state="late_night"), True, dict(C.DEFAULT_BRIGHTNESS)) is not None
