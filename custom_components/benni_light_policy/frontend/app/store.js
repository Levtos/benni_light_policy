// Datenschicht: WS-Calls + Coverage. Trennt sauber zwischen
//   policy_key  (interner Schlüssel, z.B. winter_late_evening)
//   look_ref    (was in der Map steht: Slug ODER Name)
//   look        (echtes Objekt aus benni_scene_presets/list_looks: {slug,name,...})
// Coverage wird hier (Client) berechnet — kein Cross-Import, keine Storage-Kopie.

const DOMAIN = "benni_light_policy";

export const PHASE_LABELS = {
  early_morning: "Früh-Morgen", late_morning: "Spät-Morgen", forenoon: "Vormittag",
  afternoon: "Nachmittag", early_evening: "Früh-Abend", late_evening: "Spät-Abend",
  early_night: "Früh-Nacht", late_night: "Spät-Nacht",
};
export const THEME_LABELS = {
  spring: "Frühling", summer: "Sommer", autumn: "Herbst", winter: "Winter",
  christmas: "Weihnachten", easter: "Ostern", halloween: "Halloween",
};
export const MODE_LABELS = {
  cinema: "Cinema", private_time: "Private Time", waking: "Wecklicht", work_home: "Work-Home",
};

export class Store {
  constructor() {
    this.hass = null;
    this.status = null;
    this.catalog = null;
    this.looks = [];
    this._lookBySlug = new Map();
    this._lookByName = new Map();
  }

  _ws(msg) {
    if (!this.hass) return Promise.reject(new Error("no hass"));
    return this.hass.connection.sendMessagePromise(msg);
  }

  async refresh() {
    const [status, catalog, looksRes] = await Promise.all([
      this._ws({ type: `${DOMAIN}/get_status` }).catch((e) => ({ _error: String(e.message || e) })),
      this._ws({ type: `${DOMAIN}/get_look_map` }).catch((e) => ({ _error: String(e.message || e) })),
      this._ws({ type: "benni_scene_presets/list_looks" }).catch(() => null),
    ]);
    this.status = status;
    this.catalog = catalog;
    this.looks = (looksRes && looksRes.looks) || [];
    this._indexLooks();
    return this;
  }

  _indexLooks() {
    this._lookBySlug = new Map();
    this._lookByName = new Map();
    for (const l of this.looks) {
      if (l.slug) this._lookBySlug.set(l.slug, l);
      if (l.name) this._lookByName.set(String(l.name).toLowerCase(), l);
    }
  }

  scenePresetsAvailable() {
    return Array.isArray(this.looks);
  }

  // ----- Look-Map -----
  get lookMap() { return (this.catalog && this.catalog.look_map) || {}; }

  resolveRef(policyKey) {
    const mapped = this.lookMap[policyKey];
    return (mapped && String(mapped).trim()) || policyKey;
  }

  lookFor(ref) {
    if (!ref) return null;
    return this._lookBySlug.get(ref) || this._lookByName.get(String(ref).toLowerCase()) || null;
  }

  // Coverage eines Policy-Keys: {status, ref, look, mapped}
  // status ∈ ok | invalid | missing
  coverage(policyKey) {
    const mapped = this.lookMap[policyKey];
    const ref = this.resolveRef(policyKey);
    const look = this.lookFor(ref);
    if (mapped && String(mapped).trim()) {
      return { status: look ? "ok" : "invalid", ref, look, mapped: true };
    }
    return { status: look ? "ok" : "missing", ref, look, mapped: false };
  }

  coverageSummary(keys) {
    let ok = 0, missing = 0, invalid = 0;
    for (const k of keys) {
      const c = this.coverage(k);
      if (c.status === "ok") ok++;
      else if (c.status === "invalid") invalid++;
      else missing++;
    }
    return { ok, missing, invalid, total: keys.length };
  }

  // Alle Soll-Keys der Policy (feste Modi + Matrix). Subentry-Refs separat.
  policyKeys() {
    const c = this.catalog || {};
    return [...(c.fixed_modes || []), ...(c.matrix_keys || [])];
  }

  async setLookMap(map) {
    const res = await this._ws({ type: `${DOMAIN}/set_look_map`, look_map: map });
    if (this.catalog) this.catalog.look_map = res.look_map || {};
    return res;
  }

  async setSubentryMappings(subentryId, mappings) {
    return this._ws({ type: `${DOMAIN}/set_subentry_mappings`, subentry_id: subentryId, mappings });
  }

  async setApplyEnabled(enabled) {
    return this._ws({ type: `${DOMAIN}/set_apply_enabled`, enabled });
  }

  // Tatsächlich laufender Look-Switch-State (aus den HA-Entities).
  lookSwitchState(look) {
    if (!look || !look.slug || !this.hass) return null;
    const eid = `switch.benni_look_${String(look.slug).replace(/-/g, "_")}`;
    const st = this.hass.states[eid];
    return st ? st.state : null;
  }
}
