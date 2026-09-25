# Backup / restore / reconstruction decision (items 31, 46; C014, C018, C055-C058, C095)

**Decision:** posture is **not backed up**. It is reconstructed by re-attestation.

Reasoning: a restored posture snapshot is by definition old; restoring it would re-admit state whose freshness cannot be proven. The TTL (≤ 300 s default) is shorter than any realistic restore, so a backup would be refused as stale anyway.

| State | Durable? | Recovery |
|---|---|---|
| Node posture | No | Collectors re-submit; until then `posture_absent` (restart closed) |
| Collector key enrolment | Yes — owned by the platform secret store (external) | re-enrol from secret store; **BLOCKED**: no secret-store integration shipped |
| Last-accepted seq / epoch | No | After restart the first envelope per key is accepted; replay window = envelope expiry (120 s) — documented residual |
| Quarantine / freeze | Yes — audit chain | `PostureRegistry.restore_controls(verify_file(audit, key, expected_head))` |
| Policy / config | Yes — files with digests | reload; digest mismatch refuses start |
| Audit chain | Yes — append-only file, fsync per event | retention/WORM sink external (item 22 residual) |

Split-brain: two registries are not supported. If two run anyway, per-node epochs prevent an old collector generation from overwriting a newer one on either, but they can still disagree on quarantine until audit chains are reconciled — hence "single instance only" in ADR-0001.

Test: `RegistryTest.test_controls_survive_restart_via_audit_chain`.
