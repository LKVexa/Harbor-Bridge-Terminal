# Changelog — PLN-04

## 4.3.0 — 2026-09-23

Missing-component remediation pass (M01–M48 from the 4.2.0 audit), chop-shop work order `PLN04-20260923-missing-components`.

### Added

- `plane.py`: the integrated admission and lifecycle facade.
  - No `active` state until the provider confirms creation.
  - Failed starts are compensated.
  - Teardown requires a verified zeroization receipt.
  - Also: recovery, reaper, drain, auto-rollback and an explain view.
- `providers.py`: provider contract, lifecycle state machine, registry, stale-epoch fencing and pending-start tracking. Implementations:
  - a real POSIX `ProcessProvider`
  - the `WasmProvider` binding
  - a JSON-stdio `CommandProvider` for unikernel, microVM and VM drivers
  - a `ReferenceProvider` for tests
- `security.py`:
  - signed envelopes (HS256 reference)
  - actor authentication and capability authorisation
  - signed classification
  - artifact allowlist, provenance and revocation
  - attestation verification with nonce, freshness, replay protection and trusted time
  - capability discovery
  - secret providers and redaction
- `store.py`:
  - checksummed WAL and snapshot store with CAS versions and a single-writer lock
  - torn-write vs corruption detection
  - leases with global monotonic fencing epochs
  - backup, restore and migration
- `resilience.py`: full-jitter retry, circuit breaker, weighted fair share with headroom, and a bounded per-tenant-fair admission queue.
- `observability.py`:
  - durable hash-chained audit sink with anchors and truncation detection
  - at-least-once event outbox
  - Prometheus metrics, JSON logs, W3C trace context
  - telemetry privacy policy and latency SLO evaluation
- `policy.py`: declarative config (`PK_PLANE_CONFIG/1`), residency, co-residency and staged rollout with a kill switch.
- `transport.py`: HTTP/JSON handlers with canonical error mapping and `Retry-After`.
- `errors.py`: the `PLN04-*` error taxonomy.
- `validation.py`: a strict, bounded runtime schema validator.
- Schemas: `PK_PROVIDER_REQUEST/1` and `PK_PLANE_CONFIG/1` are new. `PK_ADMISSION/1` and `PK_TIER_LIFECYCLE/1` gained fields and events (additive only).
- Governance and evidence:
  - `MASTER.md` (a labelled replacement), the ADR, the RTM, runbook, threat model, compatibility matrix, telemetry doc and patch/EOL policy
  - `ops/` registries, `pyproject.toml`, `requirements.lock`, `ci/pipeline.yml`
  - `tools/` for the release gate (with falsifier), SBOM, build info, fuzz, perf and RTM

### Fixed (defects found in this pass)

- **Unbounded in-memory audit list** in the 4.2.0 `Node`. It is now a bounded ring with a verification base, so `verify_audit_chain` still covers every retained event.
- Provider idempotency keys were shorter than the provider schema allows (found by schema enforcement).
- A controller crash inside a provider start left an **invisible provider instance** that the reaper could not see. Pending starts are now tracked, and stop, zeroize and reap cover them.
- A crash (`SystemExit`) during start was being "compensated" as if it were an ordinary error. Only `Exception` is compensated now; a crash is left for `recover()` and `reap()`.
- The fair-share model let a lone tenant consume the headroom reserved for others. The guaranteed share is now computed within `(1 - headroom)`.
- **Unbounded growth under workload churn** (found by soak), from three sources:
  - per-workload lease records, now deleted on release thanks to global epochs
  - per-workload lock objects, now striped
  - per-workload provider epoch maps, now pruned behind a fence floor

  Idempotency records now expire.
- Non-UTF-8 bytes in the WAL raised `UnicodeDecodeError` instead of `PLN04-STATE-003` (found by fuzzing).
- A corrupt but *complete* final WAL record was silently discarded as a torn write. Only an unterminated tail counts as torn now.

### Validation

- 76 tests pass, both normally and under `-O`, with 3 declared skips.
- Fuzz on the final code: 5,000 iterations per target for seeds 1–6 and 20260923, all PASS.
- Perf quick gate: PASS against PROPOSED thresholds.
- Release gate: **NO_GO (exit 3)** on human and external blockers only.

## 4.2.0 — 2026-09-22

Second audit, correctness repair, hardening, and truthful-certification pass.

### Critical correctness/security fixes

- Split dependency-free execution logic into `runtime.py`; the package can now exercise core behavior without `pk_core`.
- Removed false-positive checklist evidence mappings where admission behavior had been used to satisfy configuration-provenance requirements and teardown behavior had been used to satisfy crash-consistency requirements.
- Prevented `restore_attestation()` from creating/activating a tier that was never configured on the node.
- Quarantined resident workloads immediately when their execution tier loses attestation.
- Prevented quarantined workloads from silently resuming after attestation restoration.
- Refused cross-tenant workload takeover and tenant-mismatched teardown.
- Required explicit `privileged=True` for control-plane teardown without tenant identity.
- Prevented live re-admission from silently moving to another tier or weakening an already-stronger trust classification.
- Added same-node locking to remove duplicate-ownership races.
- Added bounded node/per-tenant admission ceilings.
- Added strict boolean tier-state validation and bounded/control-character-safe identifiers.

### Audit and interface hardening

- Added SHA-256 hash-chained in-memory audit events.
- Added versioned JSON Schemas for `PK_ADMISSION/1`, `PK_TIER_CATALOGUE/1`, and `PK_TIER_LIFECYCLE/1`.
- Added dependency-free tests for admission, quarantine, ownership, quotas, concurrency, audit-chain integrity, strict input validation, optimized mode, and version consistency.
- Corrected a missing `else` branch in the GAP-06 expected-refusal probe so a non-refusal can no longer pass by accident.
- Corrected README claims about the absent `MASTER.md` artifact and documented the actual standalone-package boundary.
- Added `docs/SECURITY.md` and `AUDIT_REPORT.md`.

### Validation

- 13 dependency-free tests pass under the available interpreter.
- 2 `pk_core` certification tests are present but skip because `pk_core` is not included in the supplied archive/environment.
- `compileall` passes.
- All shipped JSON files parse successfully.

## 4.1.0 — 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- `component.py`: bare `assert` checks were replaced by `_verify()` so behavioral checks survive `python -O`.
- Expected-refusal checks were generally hardened with explicit failure paths.
- Added stdlib conformance tests and version pins.

### Defects fixed

- Re-admitting an existing workload id under a different tenant was refused.
- Empty/non-string workload or tenant values were refused.
- Unknown tier names passed to `fail_attestation` were refused.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
