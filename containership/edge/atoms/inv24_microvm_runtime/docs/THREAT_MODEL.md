# INV-24 threat model (MC-020)

## Assets
A1 host kernel & other tenants · A2 guest memory/disk of a tenant · A3 capability/audit/snapshot keys · A4 audit log integrity · A5 approved artifacts · A6 control-plane availability

## Trust boundaries
TB1 caller → admission (B1) · TB2 runtime → VMM/jailer (B3–B5) · TB3 guest → VMM devices (B7–B9, B20) · TB4 runtime → host kernel (B6) · TB5 storage (B10, B11, B13) · TB6 operator (B18)

## Scenarios (STRIDE) → mitigations → tests
| ID | Threat | Mitigation | Test evidence | Residual |
|---|---|---|---|---|
| T1 | Device-model expansion via config/API | closed spec set, exact-type check, API field whitelist | `test_firecracker_adapter.PlanTest`, `test_security.AdversarialTest.test_device_spoof_via_subclass_rejected` | Firecracker CVEs in permitted devices |
| T2 | Guest escape through emulated device | jailer chroot/uid/netns/pid-ns, seccomp level 2, cgroups | `test_security.IsolationTest` (policy + negative verification) | real-host proof NOT_TESTED |
| T3 | Replaced/unapproved VMM binary | SHA-256 pin, absolute path, no symlink, not world-writable | `ArtifactGateTest` | pins not yet approved |
| T4 | Token spoofing / replay / privilege escalation | HMAC tokens, audience, TTL≤900 s, nonce cache, capability allowlist | `IdentityTest` | HMAC shared key; asymmetric/mTLS pending (MC-021) |
| T5 | Cross-tenant resource reuse | ownership registry, tenant-bound snapshots, per-instance uid | `DeviceTest.test_cross_tenant_reuse_blocked_and_teardown_frees`, `SnapshotTest` | memory scrub relies on VMM process exit |
| T6 | Boot-budget / admission DoS | bounded queues, per-tenant fairness, quotas, breaker | `AdmissionTest.test_overload_is_bounded_and_fair` | host-level noisy neighbour |
| T7 | Audit tampering | HMAC hash chain, fsync | `AuditTest` | key compromise |
| T8 | Secret leakage via telemetry | redaction on logs/audit/decisions, secret refs in config | `SecretsTest`, `TelemetryTest` | patterns are heuristic |
| T9 | Malicious descriptors (INV-35) | region/descriptor bounds, single-tenant regions | `DatapathTest` | INV-35 implementation itself |
| T10 | Stale controller double-executes | fencing epochs, journal idempotency | `LeaseTest`, `test_idempotent_retry_and_restart` | clock skew bounds lease safety |
| T11 | Side channels (cache/SMT) | `smt: false` in machine config | `PlanTest.test_plan_is_ordered_and_whitelisted` | microarchitectural; host microcode policy |

Review cadence: see `REVIEWS.md`. Owner: UNASSIGNED.
