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

Existing persisted `system_ready_entity` values for the two proven legacy
consumer IDs `binary_sensor.system_apply_ready` and
`binary_sensor.system_benni_context_ready` migrate to the canonical Core-State
entity. Other legacy IDs are not guessed or rewritten. The old YAML entities
remain a separate private-configuration cutover concern until all consumers
have been inventoried and a rollback path is documented.
