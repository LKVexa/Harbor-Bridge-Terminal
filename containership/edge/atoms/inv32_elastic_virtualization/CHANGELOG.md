# Changelog - INV-32

## 4.3.0 - 2026-09-22

Execution of the *v4.2.0 Missing Components Implementation Checklist* (20 workstreams, 682 bullets).
See `CHECKLIST_EXECUTION.md` for per-bullet status: 381 implemented, 144 documented, 115 partial, 42 blocked.

### Added
- Production mutation pipeline (`controller.py`): authn/authz → admission → per-guest serialization → live read
  with incarnation/tenant/lifecycle/capability checks → policy on hypervisor-confirmed capacity → fenced,
  journalled provider call → re-read verification → durable audit → response. Unknown outcomes block the guest
  until `recover()` reconciles against live state (never blind replay).
- `adapters/` HypervisorAdapter boundary, deterministic fault-injecting fake, fail-closed HyperFlux shell.
- JSON Schemas for request/result/error/host/audit, hardened decoder, conformance vectors + checker.
- Signed short-lived credentials, revocation, deny-by-default capability policy, break-glass.
- Versioned layered configuration with two-phase activation, rollback, secret references, state-safety validator.
- Durable WAL journal, atomic expected-state snapshot, segmented hash-chained audit with signed heads, external
  anchors, backup/restore with signed manifest.
- Lease/epoch fencing, per-guest locks, growth reservations (closes a concurrent reserve-crossing race found by
  the new overload test), quarantine/emergency disable, watchdog, retry budget, circuit breaker, admission, tenant
  quotas, metrics/logs/traces/explain, bootstrap preflight, benchmark gate, SBOM/SAST/RTM/evidence/exit gate.
- Docs: architecture, 6 ADRs, interfaces, SHALL requirements, failure model, threat model, runbooks,
  observability, performance/capacity, governance/compatibility, testing; ops dashboards/alerts/systemd unit.
- 112 new tests (133 total; 4 skip without `pk_core`).

### Changed
- `__init__` exposes pk_core-bound symbols lazily; the control plane imports without `pk_core`.
- Version 4.3.0 (single source `VERSION`, import-time guard).

### Compatibility
- `model.ElasticHost` API and `PK_RESOURCE_ADJUSTMENT/2` / `PK_HOST_RESOURCES/1` / `PK_RESOURCE_AUDIT/1`
  semantics unchanged (audit events gain optional fields; consumers must ignore unknown fields).
- External requests to the controller are strict (unknown fields rejected); `PK_RESOURCE_ADJUSTMENT/1` accepted
  only as a legacy model revert record, removal planned for 5.0.0.

### Not done (blocked)
- Real HyperFlux integration, hosted CI/provenance signing, named owners/approvals, PKI/mTLS, encryption at rest,
  consensus lease store, real-hardware benchmarks/soak/fleet tests, game-day exercise, license choice.

## 4.2.0 - 2026-09-22

Second-pass audit, correctness hardening, and evidence correction.

### Resource-state hardening

- Split the pure safety-critical state machine into `model.py`, independent of `pk_core`, so it can be tested in isolation.
- Made `Guest` immutable and added strict identifier, integer, boolean, floor/ceiling, vCPU, host-size, and reserve-fraction validation.
- Made host reserve configurable and conservatively rounded upward so integer rounding never reduces the declared reserve.
- Added thread-safe resource mutations, host snapshots, bounded free-page reports, and vCPU history.
- Added replay-safe operation IDs; exact replays return the original result and conflicting re-use is rejected.
- Added stale-adjustment fencing so an old rollback cannot overwrite newer state.
- Fixed rollback type confusion: vCPU adjustment records are now reverted as vCPU state rather than being interpretable as memory records.
- v2 rollback records must exactly match an event in the host's verified audit history; forged records are refused.
- Added structured resource-policy error codes/details and fail-closed state-integrity checks.

### Audit evidence

- Added `PK_RESOURCE_ADJUSTMENT/2`, `PK_HOST_RESOURCES/1`, and `PK_RESOURCE_AUDIT/1` repository-local schema documentation in `SCHEMAS.md`.
- Added SHA-256 hash-chained mutation history and verification; mutations stop if the chain is corrupted.
- Added explicit reason fields and stable host/tenant/guest/operation identifiers to v2 events.

### Verification

- Added 18 stdlib model tests covering bounds, replay, concurrency, rollback freshness, forged records, audit tampering, free-page reports, structured errors, and reserve accounting.
- Corrected the adapter conformance test so it verifies 100 findings are produced without claiming that every checklist requirement has package-local production evidence.
- The archive does not include `pk_core`; adapter tests therefore skip unless a compatible sibling package is supplied with `PK_CORE_PATH`.

### Post-update audit

- Added `AUDIT_REPORT.md` and machine-readable `AUDIT_REPORT.json`.
- Removed the previous README claim that a `MASTER.md` file was carried in this archive; no such file was present.
- Production gaps remain, notably the real HyperFlux/hypervisor integration, formal external schemas, authn/authz, configuration lifecycle, durable audit export, observability stack, performance evidence, fault/security/integration testing, and release/governance controls.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::ElasticHost.revert: restored the old size with no reserve check, so reverting a shrink after other guests grew allocated into the host reserve -> ReserveBreach check on the revert delta
- component.py::ElasticHost.adjust_memory: Guest.cooperative was never consulted, so honoured=True recorded a non-cooperative guest as having returned memory -> honoured = honoured and guest.cooperative
- component.py::ElasticHost.add: duplicate guest name silently replaced the existing guest (and its allocation) -> ValueError
- component.py::ElasticHost (adjust_memory/revert/adjust_vcpus): unknown guest raised bare KeyError -> UnknownGuest(KeyError)
- component.py::Guest.__post_init__: negative floor, empty ids, vcpus outside [1, vcpu_max] accepted -> ValueError
- component.py::assess_resilience (items[4]): claimed idempotence was never exercised -> now re-applies a target and reverts it, and exercises the non-cooperative honoured=True case

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
