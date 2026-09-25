# GAP-01 Threat Model (STRIDE) and Derived Controls

Scope: the supervisor process, its UNIX control socket, loopback probes, state directory, key files, and runtime adapters. Out of scope: kernel, hypervisor and hardware compromise (root on the node defeats every local control; mitigated only by attestation, EXC-002).

| ID | Threat | STRIDE | Control | Test (evidence) |
|---|---|---|---|---|
| T1 | Unauthenticated local process sends lifecycle commands | S | 0600 socket in 0700 dir; per-caller HMAC signature | `test_integration::test_socket_permissions`, `test_controller::test_authn_replay_skew` |
| T2 | Captured request replayed | S/T | nonce window + timestamp skew + `request_id` completion records | `test_authn_replay_skew`, `test_idempotent_request_id` |
| T3 | Health reporter spoofs a signal it does not own / invents signals | S | signal registry + per-signal reporter allow-list | `test_production::HealthTest::test_spoofing_and_limits` |
| T4 | Low-privilege caller escalates (e.g. observer cordons, control plane forces drain) | E | deny-by-default roles; override grants expire | `test_authz_denied_is_audited`, `test_operator_override`, `test_emergency_mode` |
| T5 | Hostile JSON (deep, huge, wrong types, path-like IDs) | T/D | size cap, schema validation before any mutation, ID pattern | `FuzzTest`, `test_schema_rejects_bad_args` |
| T6 | Request flood starves the supervisor | D | per-caller token bucket + in-flight ceiling | `test_rate_limit`, `test_production::test_rate_limiter` |
| T7 | Compromised workload refuses termination to keep node alive / hide | E/D | force-kill at deadline; reclaim proof; node held in draining | `test_deadline_breach_then_force_kill`, `test_unproven_reclaim_never_stops_node`, `test_sigterm_ignoring_process_is_force_killed` |
| T8 | Workload started out-of-band survives as orphan | E | restart reconciliation terminates orphans | `test_orphans_terminated_lost_removed_ready_becomes_cordoned` |
| T9 | State files tampered or corrupted | T | checksummed checkpoint+journal, fail closed, audit hash chain | `StoreTest`, `test_audit_chain_detects_tamper` |
| T10 | Audit trail edited to hide actions | R | hash-chained audit; startup refuses broken chain | `test_audit_chain_detects_tamper` |
| T11 | Malicious config pushed | T | HMAC-signed config, range validation, unknown knobs rejected | `ConfigTest::test_signed_config`, `test_ranges_enforced` |
| T12 | Secrets leak via logs/diagnostics | I | `SecretBoundary` redacted repr; log/diag redaction by key pattern | `test_secret_boundary`, `test_redaction` |
| T13 | Tampered release artifact | T | sha256 manifest + optional HMAC signature; path-escape rejected | `test_artifact_verification` |
| T14 | Control-plane impersonation during partition to uncordon/admit | S/E | partitioned mode refuses admit; heartbeat requires authenticated caller | `test_partitioned_refuses_admit` |
| T15 | Clock manipulation (future/regressing timestamps) | T | monotonic decision clock; regression rejected; future health stale | `test_supervisor::test_future_health_is_not_valid`, `test_time_regression_rejected` |
| T16 | Disk full to force unsafe state | D | persistence errors structured; post-apply failure → emergency | `test_disk_full_is_structured`, `test_persistence_failure_enters_emergency` |
| T17 | Hung supervisor keeps stale "ready" | D | watchdog: liveness fails, emergency, sd_notify WATCHDOG withheld → systemd restart | `test_readiness_liveness_watchdog` |
| T18 | Supervisor process compromise | E | systemd sandbox: non-root user, `CAP_KILL` only, `NoNewPrivileges`, syscall filter, `ProtectSystem=strict` | `deploy/systemd/gap01-supervisor.service` (static review; EXC-005 for runtime seccomp test) |

## Residual risks

- Root on the host (out of scope) — mitigated only by hardware attestation (EXC-002).
- Shared-secret HMAC means a stolen caller key allows impersonation of that caller until rotated (see RUNBOOKS RB-08 rotation).
- Encryption at rest of the state directory is delegated to the host (LUKS/fscrypt); state contains no secrets by design (EXC-007).

## Cryptographic parameters and key lifecycle

| Use | Algorithm | Key | Where verified |
|---|---|---|---|
| Caller request authentication | HMAC-SHA256 over canonical JSON (sorted keys) of caller, request_id, nonce, ts, op, args | per caller, ≥ 16 bytes (32 random bytes recommended), file mode 0600 | `security.Authenticator` (constant-time compare) |
| Config signing | HMAC-SHA256 over canonical config body | `config.key` | `config.load_config` |
| Release manifest | SHA-256 per file; optional HMAC-SHA256 over the file map | `release.key` | `bootstrap` integrity phase |
| Boot attestation | HMAC-SHA256 over phase digest + inventory digest + version + nonce | `node.key` | `NodeIdentity.verify` |
| State/audit integrity | SHA-256 checksums and hash chain (integrity, not authenticity) | none | `StateStore.load`, `AuditLog.verify` |

Algorithm agility: a move to asymmetric signatures (Ed25519) is a `/2` change; `/1` accepts only HMAC-SHA256.
Key lifecycle: provisioning via files at day 0; storage 0600 in a 0700 directory owned by `gap01`; rotation by replacing the file and restarting (RB-08); revocation by removing the caller's `--caller-key`; in-memory zeroization via `SecretBoundary.close`; compromise → break-glass `emergency_enter`, rotate, review audit. Key expiry is not enforced in code (tracked as an open item).
`traceparent` is routing metadata and is intentionally outside the request signature. It can change how requests are correlated in traces, but it cannot change what a request authorizes.
The nonce window is kept in memory. After a restart, a replayed request is still caught by its `request_id` completion record, which is durable, so it never executes twice.
Audit tail truncation (deleting the newest records) can't be detected locally without an external anchor. Operators should export the audit head hash off-node (RB-08, weekly).
