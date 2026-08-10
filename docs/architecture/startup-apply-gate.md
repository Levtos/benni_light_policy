# Light Policy: Startup-/Apply-Gate

Parent: [Core-State Issue #33](https://github.com/Levtos/benni-core-state/issues/33)

Light Policy consumes the read-only Core-State entity
`binary_sensor.benni_core_state_apply_ready`. The entity represents only the
Home Assistant process lifecycle and is not a substitute for
`apply_enabled`, the Lux gate, Manual-Off, source health, or a policy decision.

The policy still computes and publishes its plan while the startup gate is
off. In that state `startup_block` is added to the plan blockers and
`apply_allowed` remains false; look, brightness, Lux-gate and diagnostic plan
values remain observable. The local `startup_block_seconds` option (default 15
seconds) is a deliberate Light-Policy staging delay. It must never create or
reset the Core-State 90-second process timer.

Existing persisted `system_ready_entity` values for the three proven legacy
consumer/registry IDs `binary_sensor.system_apply_ready`,
`binary_sensor.system_benni_context_ready`, and the live-observed
`binary_sensor.system_benni_core_state_apply_ready` migrate to the canonical
Core-State entity. Other legacy IDs are not guessed or rewritten. The old YAML
entities remain a separate private-configuration cutover concern until all
consumers have been inventoried and a rollback path is documented.

## Startup Lux recovery

After the canonical Core-State gate is ready, Light Policy waits for one fresh
Lux sample before it permits the first post-start apply. A sample is fresh only
when its state is numeric, finite, non-negative, not `unknown`/`unavailable`,
not the known reconnect fallback `1 lx`, and its `last_reported` timestamp (with
`last_updated`/`last_changed` compatibility fallbacks) is later than the
Core-State `startup_started_at` reference. A value from before that reference is
diagnosed as stale and cannot complete recovery.

While this sample is missing, the complete plan remains visible but carries the
consumer-local `startup_lux_block`. The first sample that satisfies both
Core-State readiness and Lux freshness clears that block and forces exactly one
deterministic re-apply, including when the scene hash is unchanged. Repeated
state updates do not repeat this startup recovery; an explicit `apply_now`
remains an explicit manual re-apply.

This is a Light-Policy consumer gate, not a second global timer and not a new
Core-State contract. Bedroom and kitchen lights are not added to the normal
living-room startup scope; the existing, separately owned wake-area teardown
remains unchanged.
