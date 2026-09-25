# Changelog - INV-34

## 5.1.0 - 2026-09-22

Chop-shop pass executing `MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md` (74 components, 2,088 items) against 5.0.0.
Additive: the 5.0.0 `expansion.py` policy/state machine is unchanged and remains the single source of expansion rules.

### Added (`production/`, stdlib only)
- Cloud Hypervisor REST adapter (`vm.info` / `vm.resize`), refusing any target below the live count before sending (the donor API also shrinks), five-valued outcomes with UNKNOWN for timeouts/5xx, fencing, rate limit; deterministic fault-injecting emulator for CI.
- Signed, source-bound, fresh, sequence-monotonic guest cpulist observations; explicit stall classification.
- Durable single-host CAS store (atomic write + fsync + digest), durable idempotency, lease/fence tokens, operation journal, crash recovery, digest-verified backup/restore that forces reconciliation.
- Reconciler: live read before any retry, bounded full-jitter backoff, retry budget, circuit breaker tied to degraded mode.
- HMAC caller authentication (skew + replay window, rotation), least-privilege capability policy, tenant/site/fleet quotas with weighted fair share, precedence engine, headroom forecast.
- Stdlib HTTP boundary: expand/status/observe/freeze/explain, health/readiness/version/metrics, protocol negotiation, deadlines, size limits, load shedding.
- Declarative config with atomic activation, provenance, distinct-approver rule in production, rollback.
- Tamper-evident HMAC-chained audit log; structured redacting logs; W3C trace propagation; bounded-label metrics; alert rules.
- 30 SHALL requirements with a generated, link-checked RTM.
- Tooling: CI pipeline, reproducible build + manifest + CycloneDX SBOM, perf baseline + regression gate, pk_core gate (fails closed), runbook automation, checklist executor, exit gate (NO_GO).

### Defects found by this pass's own checks and fixed
- Fuzzing found `submit` indexing durable state with an unvalidated `request_id` (a JSON list raised `TypeError` → 500). Inputs are now validated before any state access.
- `tools/perf.py` found degraded mode never ended: the breaker closed but dependency health stayed `down`. Health now follows the breaker (regression test added).
- The first checklist classifier promoted 614 items to VERIFIED by component; review found over-claims (e.g. encryption at rest, independent security review). Promotion is now by hand-reviewed allowlist only: 87 items.

### Not done (see governance/BLOCKERS.json)
Owner/sign-offs, pk_core, live hypervisor certification, fleet/soak/partition environments, signing/KMS/IdP, licence, threshold approval, replicated store, deployment/pager/dashboard backends, power/thermal hardware.

## 5.0.0 - 2026-09-22

Major corrective audit, hardening and scope-alignment release.

### Critical correction

- Realigned INV-34 with `CHECKLIST.json`: **Conventional VM CPU scaling through ACPI CPU hot-plug**. The previous 4.1.0 code implemented x86 instruction-feature matching, which did not implement the checklist's stated function or technology.
- Removed the misleading x86 feature-level matcher from the INV-34 implementation path rather than certifying the wrong subsystem.

### Hardened control logic

- Added dependency-free `expansion.py` with immutable validated state, monotonic expansion policy, VM/host capacity ceilings, ACPI/guest capability gating, desired-vs-observed convergence semantics, generation checks, structured errors, bounded idempotency replay, and thread-safe state mutation.
- Added explicit observation guards so an accepted request cannot be reported as complete until the backend/guest observation reaches the desired count.
- Added administrative expansion disable semantics and refused CPU hot-unplug through this legacy path.
- Added versioned request/result/status JSON Schemas.

### Testability and packaging

- Package logic now imports and runs without `pk_core`; only the framework adapter requires that external dependency.
- Added standalone stdlib tests covering validation, failure modes, idempotency, concurrency, replay bounds, generation safety, capacity changes and observation convergence.
- Kept framework conformance tests, which run automatically when `pk_core` is available.
- Removed the README claim that a non-existent `MASTER.md` was bundled.

### Documentation and audit evidence

- Added architecture, threat-model, compatibility and operations documents.
- Added `AUDIT_REPORT.md` and an explicit post-fix `MISSING_COMPONENTS.md` rather than treating missing external production infrastructure as satisfied.

## 4.1.0 - 2026-09-22

- Replaced optimization-sensitive bare asserts with explicit behavioural verification in the prior implementation.
- Added initial conformance test, version file and package version pin.

## 4.0.0

- Initial master-applied component.
