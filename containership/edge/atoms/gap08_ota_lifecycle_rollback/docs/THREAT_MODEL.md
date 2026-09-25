# GAP-08 threat model (v4.3.0)

Method: STRIDE over each trust boundary, plus the checklist's named classes (replay, downgrade, stale-data acceptance, confused deputy, spoofed identity, privilege escalation, tampering, resource exhaustion, malicious-but-well-formed input). **Status: author draft — independent security review is an open item (see `CHECKLIST_STATUS.md`).**

## Trust domains

| Domain | Holds | Controller may |
|---|---|---|
| Controller workload | lease, state-store credentials (by `SecretRef`) | verify every signature below; sign nothing that others trust except commands |
| GAP-07 verifier | artifact signing/verification key | verify statements only |
| GAP-09 observability | evidence signing key | verify evidence only |
| Audit sink | sink key | verify receipts/head only |
| Node (GAP-01/06) | device identity key, measured boot | verify acks only |
| Operators | human identities, roles, environment scopes | call APIs within capabilities |

> The reference build uses one HMAC `KeyRing` for convenience; that is a **test simplification**. Production must use asymmetric keys (or HSM/KMS-held HMAC keys per domain) so the controller holds verification material only.

## Threats and controls

| # | Threat | Boundary | Control (code) | Test |
|---|---|---|---|---|
| T1 | Verification replayed/rebound to another bundle | GAP-07→C | subject + sha256 digest binding, expiry, revocation, algorithm allow-list (`artifact.py`) | `ArtifactVerification` |
| T2 | Algorithm downgrade | GAP-07→C | `allowed_algorithms` | `test_rejections[downgrade]` |
| T3 | Bytes swapped after verification (cache/CDN/peer) | distribution→node | per-chunk + whole digest (`distribution.py`), node re-hash (`installer.stage`) | `Distribution`, `Section06OneByteMutation` |
| T4 | Stale/replayed/mis-scoped health evidence | GAP-09→C | signature, source-key binding, rollout/cohort/gate-class binding, freshness, settle window, coverage, consistency, replay set (`health.py`) | `HealthEvidence` |
| T5 | Raw boolean health injection | API | no production path accepts a bool; `Rollout.run_wave(healthy=…)` is only called with adapter output | `test_controller` |
| T6 | Stale controller after partition/GC pause | C→store/nodes | fencing tokens at store (`fence_check`) and nodes (`_high_fence`) | `FencingRecovery`, `LeaseTest` |
| T7 | Split brain / lost update | C→store | CAS revision; write-ahead intents; two-phase rollback | `Concurrency`, `StoreTest` |
| T8 | Duplicate/reordered commands | C→node | deterministic `command_id` dedup; rollback tombstone | `DeferredAndIdempotency`, `test_step_racing_rollback…` |
| T9 | Spoofed node ack / cross-node replay | node→C | enrolled key per node, single-use nonce bound to node, field binding, measurements, freshness (`identity.py`) | `Identity` |
| T10 | Compromised/replaced device | node | revocation, rotation, generation counter | `test_rotation_and_revocation` |
| T11 | Local history rewrite after incident | store | per-event hash chain + external sealed copy; `verify_against` detects edits with or without re-hashing; `reconstruct` | `Section05TamperDrill` |
| T12 | Privileged rewrite of pinned target | store | `_guard_transition` immutability | `test_pinned_target_and_audit_prefix_immutable` |
| T13 | Confused deputy (tenant triggers OTA) | API | tenant principals always refused (`authz.py`) | `test_authorization_enforced` |
| T14 | Privilege escalation / self-approval | API | explicit capabilities, env scope, two-person approvals, single-use bound approvals | `Section11ScopedAuthorization`, quarantine/unfreeze tests |
| T15 | Wave ordering takes out a site | policy | blast-radius engine counts deferred + quarantined as unavailable | `test_topology_blast_radius…` |
| T16 | Resource exhaustion / retry storms | all | admission limits, token buckets, full-jitter, per-cohort breakers, reserved recovery lane | `RetryBreakerAdmission` |
| T17 | Malicious-but-well-formed input (huge waves, hostile snapshots, Unicode ids) | API/store | strict validation, finite JSON only, id charset for store keys, fuzzing | `test_property_fuzz` |
| T18 | Secrets leaking into state/logs/audit | all sinks | `assert_no_secrets` before persist/seal; `redact` for humans; KeyRing never serialises | `test_secrets_boundary`, `test_rejects_secrets_and_bad_ids` |
| T19 | Dependency outage used to force unsafe progress | deps | policy table; overrides impossible for store/lease/identity/authz | `Section15DependencyMatrix` |
| T20 | Emergency control abuse | freeze | freeze by one, unfreeze needs second person; freeze never blocks rollback | freeze test |

## Residual risks (tracked in `CHECKLIST_STATUS.md`)

* HMAC stand-in for asymmetric signatures; no mTLS/workload identity on transport in this package.
* No encryption at rest in the reference file store (file mode 0600 only).
* Single-host reference store/lease — the distributed GAP-05 backend and lease service must provide the same CAS/fence semantics.
* Clock trust: FakeClock in tests; production needs a bounded-skew time source (dependency `time`).
* Replay caches (evidence, nonces) are in-memory: a controller restart clears them — mitigated by freshness windows (≤ 300 s / 600 s); a durable replay cache is recommended.
