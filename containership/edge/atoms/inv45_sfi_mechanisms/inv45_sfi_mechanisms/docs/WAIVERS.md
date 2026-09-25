# Exception, waiver and technical-debt register (C099)

Machine-readable source: `release/waivers.json` (validated by `tools/release.py`). A waiver is **effective
only when `approver` is set and `expires` is in the future**; every waiver below is **PENDING** because no
approver is bound (OWNERSHIP.md). Pending waivers do not satisfy any gate.

| Id | Item | Rationale | Compensating controls | Risk | Expiry / review | Closure criteria | State |
|---|---|---|---|---|---|---|---|
| W-01 | PERF-01: load-bound overhead ≈ 36 % > 15 % SLO | V8 keeps its own bounds checks; masking is additive | compute-mixed ≈ 0 %; overhead measured each release | medium (cost) | 2026-12-31 | loop-invariant mask hoisting (new ADR) or SLO re-scope approved | PENDING |
| W-02 | T18 speculative side channels between partitions in one engine process | SFI masking is architectural only | one process per execution job; tenants needing it run in separate processes/hosts | high | 2026-12-31 | per-tenant process policy enforced or hardware isolation tier integrated | PENDING |
| W-03 | Node permission model does not restrict network in the engine process | upstream limitation | runner exposes no network API to guest; empty env | medium | 2026-12-31 | OS-level network namespace/seccomp profile for engine jobs | PENDING |
| W-04 | U-08 overlapping partitions across service instances not detected | partition assignment is per-instance config | `sfi.check_partitions` refuses overlap incl. guard (adversarial review confirmed the guard is load-bearing); nothing calls it centrally yet | high | 2026-12-31 | central partition allocator with overlap check | PENDING |
| W-05 | A-21 non-atomic network filesystems not detected | cannot probe portably | documented prerequisite | medium | 2026-12-31 | preflight probe for rename atomicity | PENDING |
| W-06 | FM12 stale activation lock needs manual removal | lock owner liveness not tracked | runbook procedure | low | 2026-12-31 | lock with PID + lease | PENDING |
| W-07 | `pk_core` not pinned / gate NOT RUN | no published pk_core version/digest | 100-item gate replaced for now by repository-local RTM + CHECKLIST_AUDIT | high (certification) | 2026-12-31 | A2 closed | PENDING |
| W-08 | Engine-delegated guarantees (pinned base register, W^X/ASLR, return integrity) not independently verified | require native-code inspection of V8 | engine version pinned + preflight; ADR records them as prerequisites | medium | 2026-12-31 | engine attestation / vendor evidence reviewed | PENDING |
| W-09 | No production IdP/KMS/HSM integration (HMAC keys by env/file reference) | no target platform fixed | secret refs, rotation, revocation, freshness | medium | 2026-12-31 | integrate the organisation's KMS/IdP | PENDING |

## Deprecated behaviour

| Item | Since | Removal |
|---|---|---|
| `SfiModule.overhead_percent` in the reference model is caller-supplied metadata, not evidence | 4.2.0 | kept for `PK_SFI_MODULE/1` compatibility; production overhead comes from benchmarks |
| Hard import of `pk_core` in `__init__.py` | removed in 4.3.0 | — |
