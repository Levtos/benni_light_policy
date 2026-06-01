# UX-Rework Briefing — benni_light_policy ↔ benni_scene_presets

> Stand: 2026-06-01, nach Schritt 1 (Apply-Kanal auf Looks umgestellt).
> Zweck: Grundlage für die Planung des UX-Reworks. Beschreibt den aktuellen
> Integrations-Vertrag, die bestehende Config-Oberfläche und die offenen Punkte.

---

## 1. Architektur in einem Satz

`benni_light_policy` ist das **Gehirn** (entscheidet anhand von Presence/Bio/Day-State/
Media-Context/Lux/Wetter, welcher Lichtmodus wann gilt). `benni_scene_presets` ist die
**Render-Schicht**: ein **Look** ist die deploybare Einheit (trägt Targets, Bindings,
Off-Bindings, Crossfade) und wird per **Name oder Slug** referenziert.

**Kanal (seit Schritt 1):** Pro Entscheidung ruft der Coordinator genau einen Service —
`benni_scene_presets.apply_look {look: <ref>, brightness: <Tagesphase>}`. Targets, das
Ausschalten nicht-genutzter Lampen (Off-Bindings) und der Crossfade (`look_transition`)
liegen vollständig **im Look**. Die Policy liefert nur die **Look-Ref** + die
**Helligkeit aus der Tagesphase**.

```
Context (Sensoren) ─▶ policy.decide() ─▶ Plan{preset_enum, brightness, …}
                                            │ preset_enum = Look-Ref (Name/Slug)
                                            ▼
                         coordinator._apply ─▶ apply_look {look, brightness}
```

Ausnahmen vom Look-Kanal:
- **`wake_up`-Subentry** (frei gewählte `raw_targets`, kein Look) → direkter
  `light.turn_on` mit Kelvin + Helligkeit.
- **Hard-Off** (`APPLY_OFF`: sleep / Lux-Gate zu) → `light.turn_off` auf GROUP_ALL.

---

## 2. Der Look-Vertrag — welche Look-Refs erzeugt die Policy?

Das ist der Kern für die UX: die Policy gibt heute **Strings** aus, die 1:1 als
`look` durchgereicht werden. Damit Apply greift, muss im benni_scene_presets-Panel
ein Look mit passendem **Namen oder Slug** existieren.

### 2a. Feste Modi

| Modus | Look-Ref | Quelle in `policy.py` | Besonderheit |
|---|---|---|---|
| Cinema (TV) | `cinema` | `_eval_cinema` | braucht Off-Binding für die Ceiling |
| Private Time | `private_time` | `_eval_private_time` | braucht Off-Binding für die Ceiling |
| Waking (Wecklicht) | `waking` | `_eval_waking` | Kelvin-Look auf weiße Ceilings |
| Work-Home | `work_home` | `_eval_work_home` | Kelvin-Look (5000K) |

### 2b. Tagesphasen-Matrix (dayphase / household / presence_sim)

Look-Ref = `{theme}_{phase}` (`_phase_preset`).

- **theme** = Event-Thema (gewinnt) **oder** Jahreszeit (Fallback `winter`):
  - Event (`THEME_MAP`): `christmas`, `easter`, `halloween`
  - Jahreszeit: `spring`, `summer`, `autumn`, `winter`
- **phase** (`DAY_PHASES`): `early_morning`, `late_morning`, `forenoon`, `afternoon`,
  `early_evening`, `late_evening`, `early_night`, `late_night`

Beispiele: `winter_early_evening`, `autumn_late_evening`, `christmas_early_night`.

> **Wichtig für die UX:** Das ist eine große Matrix (7 Themes × 8 Phasen = 56 mögliche
> Slugs). Die **Helligkeit** kommt aber separat aus dem Tagesphasen-Profil
> (`DEFAULT_BRIGHTNESS` / `CONF_BRIGHTNESS`) und wird als Override mitgegeben — d.h. **ein**
> Look kann mehrere Phasen bedienen (gleiche Farbe, andere Helligkeit). Die UX sollte daher
> erlauben, **mehrere Modus-Schlüssel auf denselben Look** zu mappen, statt 56 Looks zu erzwingen.

### 2c. Gaming / Musik (Subentry-Mappings)

Pro Subentry ein Classifier (`classifier_value → Look-Ref`) in `CONF_MAPPINGS`
(bis zu 8 Slots). Werte sind **frei vom User vergeben** (heute Strings, früher UUIDs).
Beispiel: `overwatch → ow-talon-look`, `hearthstone → hs-cozy`.

---

## 3. Aktuelle Config-Oberfläche (Hub + Subentries)

**Hub-Entry** (`config_flow.py`, mehrstufig):
- Foundation-Entities (Bio/Day/Activity/Presence/Lux/Wetter/Media …) — breit auto-prefilled
  aus Live-IDs (`ENTITY_PREFILL`).
- **Lampengruppen** als Multi-Light-Listen (`GROUP_MAIN`/`GROUP_CEILING`/`GROUP_ALL`,
  `GROUP_PREFILL`). Werden in `_resolve_targets` geflacht — **nur noch für OFF + wake_up
  relevant** (Look-Modi holen Targets aus dem Look).
- Gates/Apply/Brightness-Profil/Lux-Schwellen.

**Subentries** (`config_subentries`): Gaming, Musik, Notification-RGB, Flur, Bad, Schlafzimmer/Wake-Up.

### Config-Altlasten, die der UX-Rework aufräumen sollte

| Feld / Option | Status | Empfehlung |
|---|---|---|
| `CONF_PRESET_CATALOG` (`preset_catalog_entity`) | **deprecated**, ungenutzt seit Look-Kanal | aus `config_flow.py` (`STEP_LAMPS`) + `strings.json`/`translations` entfernen |
| Mapping-Slot-Labels „Scene-Preset-UUID" | irreführend | → „Look-Slug / -Name"; idealerweise **Selector aus der Look-Liste** statt Freitext |
| `CONF_SCENE_INTERVAL_SECONDS` (`scene_interval_seconds`) | **tot** (Interval lebt im Look/Binding) | aus Options entfernen |
| `CONF_SCENE_TRANSITION_SECONDS` | prüfen — Crossfade liegt jetzt im Look | wahrscheinlich entfernen |
| `CONF_CROSSFADE_SECONDS` | nur noch für wake_up-`turn_on` + Begrenzung genutzt | behalten, aber Wirkungsbereich klarstellen |

---

## 4. Was der UX-Rework adressieren soll

### 4.1 Kern: komfortables Look-Mapping
Heute werden Look-Refs entweder **fest im Code** abgeleitet (Kernmodi → Namenskonvention)
oder als **Freitext** in Subentries getippt. Ziel:
- **Selector statt Freitext.** Die verfügbaren Looks live aus benni_scene_presets ziehen
  (WS-API `benni_scene_presets/list_looks`) und als Dropdown anbieten — pro Modus/Mapping-Slot.
- **Look-Map für Kernmodi** (statt Namenskonvention): konfigurierbares
  `{preset_enum → look_slug}` im Hub, mit sinnvollem Default (= aktueller Konventions-Slug).
  Erlaubt „viele Phasen → ein Look" (s. 2b).
- **waking/work_home konfigurierbar** machen (heute hart `"waking"`/`"work_home"`).

### 4.2 Validierung / Sichtbarkeit
- **Coverage-Check:** zeigt an, welche von der Policy erzeugten Look-Refs aktuell **keinen**
  existierenden Look haben (sonst läuft `apply_look` in `vol.Invalid` → nur Log).
  benni_scene_presets liefert die Look-Liste; die Matrix aus §2 ist die Soll-Seite.
- **Live-Status:** `switch.benni_look_<slug>` zeigt den laufenden Look — in der Policy-UX
  als „aktiver Look" einblendbar.

### 4.3 Config-Hygiene
Die Altlasten aus §3 entfernen/umbenennen.

---

## 5. Bausteine / Schnittstellen für die UX

**benni_scene_presets stellt bereit:**
- Services: `apply_look {look, brightness}`, `stop_look {look}` (+ `apply_preset`,
  `start_dynamic_scene`, `reset_userdata`).
- Look-Datenmodell: `{id, name, slug, transition, bindings:[…]}`; Binding-`kind` ∈
  `scene` | `off` | `aqara` | `effect`; Off-Binding schaltet Lampen gezielt aus,
  `look_transition` = Crossfade.
- `switch.benni_look_<slug>` (läuft/aus), WS-API `list/save/delete_look` + `list_presets`.

**benni_light_policy emittiert (Observability, schon vorhanden):**
- `sensor.*_mode`, `sensor.*_preset_enum` (= Look-Ref!), `sensor.*_scene_hash`,
  `sensor.*_brightness_target` / `_color_temp_target`, `sensor.*_plan` (voller Plan),
  `binary_sensor.*_apply_blocked`, `switch.lights_apply_enabled`, `switch.lights_manual_off_*`.

> `sensor.*_preset_enum` ist faktisch schon die „welcher Look ist gewünscht"-Anzeige —
> ideal als Brücke für eine kombinierte UX (gewünscht vs. tatsächlich laufend).

---

## 6. Offene Design-Entscheidungen (für den Rework zu klären)

1. **Wo lebt die Look-Map-UX?** Im Policy-Hub (Options-Flow) oder im benni_scene_presets-Panel
   (eine „Policy-Bindings"-Ansicht)? Letzteres hätte die Look-Liste schon zur Hand.
2. **Granularität der Tagesphasen-Looks** — pro Phase ein Look, oder wenige Looks +
   Helligkeit aus dem Profil (s. 2b)? Beeinflusst, wie viele Looks der User pflegen muss.
3. **Gaming/Musik vs. Looks mit Aqara-Bindings** — soll ein Game-Look künftig Ceiling-Szene
   + Ring-Effekt **in einem Look** bündeln (statt separatem Ring-Controller in `areas.py`)?
4. **Selector-Quelle** — darf die Policy-Config zur Konfigurationszeit die
   benni_scene_presets-WS-API abfragen (Kopplung), oder bleibt es Freitext mit nachgelagerter
   Validierung?

---

## 7. Verweise
- Apply-Kanal-Details: `CLAUDE.md` → Abschnitt „Apply-Kanal: benni_scene_presets Looks".
- Entscheidungslogik: `custom_components/benni_light_policy/policy.py` (`decide`, `_eval_*`,
  `make_gaming_policy`/`make_music_policy`).
- Apply: `custom_components/benni_light_policy/coordinator.py` (`_apply`).
- Looks/Services Gegenseite: `benni_scene_presets/custom_components/benni_scene_presets/`
  (`__init__.py` `apply_look`/`stop_look`, `services.yaml`, `file_utils.py`).
