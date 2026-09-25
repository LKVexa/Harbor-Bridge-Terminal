# Changelog - INV-05

## 4.3.0 - 2026-09-22

Chop-shop implementation pass against the *INV-05 v4.2.0 52-component professional checklist*. Minor bump: large additive API surface; the 4.2.0 `state.py`/`component.py`/`contract.py` APIs are unchanged.

### Added: service implementation
- `store.py` MVCC engine: one revision per transaction, compare/success/failure branches, typed predicates (EXISTS, VALUE, VERSION, CREATE, MOD, LEASE, FENCE), point/range/prefix reads at any retained revision with stable paginated snapshots, explicit deletes + tombstones + prefix delete, leases with TTL/keepalive/expiry and monotonic fencing tokens, protected revisions, idempotent `request_id`s, invariant checker (MC-008..011, 016..019, 026).
- `wal.py`: checksummed WAL frames, fsync-before-ack, group-commit opt-in, atomic snapshots, crash recovery with torn-tail handling, fail-closed corruption handling, AES-256-GCM sealing with a rotatable keyring (MC-006, 024, 025).
- `watch.py`: ordered watch delivery, progress frames, resume points, lossless history fallback for slow consumers, lag cancellation, quotas, drain (MC-014, 015, 017).
- `schema.py`, `errors.py`: versioned JSON wire schemas, strict parsing, negotiation, append-only error catalog with retry semantics (MC-012, 013, 027).
- `security.py`, `audit.py`: SPIFFE mTLS authentication, HMAC tokens, deny-by-default versioned policy with rollback, namespaces, secret refs, redaction, TLS policy checks, HMAC-chained audit log (MC-021..025, 038).
- `service.py`, `server.py`, `client.py`, `serve.py`, `bootstrap.py`, `config.py`: request pipeline, freeze/drain/quarantine/maintenance/break-glass, health/readiness/version, mTLS HTTP + NDJSON watch streaming, reference client with backoff+jitter and the list-then-watch `Mirror`, typed layered configuration, idempotent bootstrap (MC-020, 026, 028..031, 050).
- `observability.py`: metric catalog with cardinality caps + Prometheus exposition, structured logs with stable event ids and storm control, W3C tracing, explain records (MC-032..036).
- `backup.py`, `replication.py`, `backend.py`: signed + encrypted verified backups, restore with compaction fencing, compaction controller, GAP-05 replication contract with epoch fencing, backend adapter boundary that fails closed until a backend is pinned (MC-004, 005, 019, 039..041).
- `linearizability.py`, `bench.py`, `conformance/`: WGL linearizability checker, deterministic benchmark, golden vectors + runner (MC-042, 043, 047).

### Added: verification, supply chain, operations
- 17 test modules / 171 tests (plus subtests): durability crash matrix, chaos schedules, fuzzing, linearizability, end-to-end mTLS with generated PKI, certificate hot rotation, conformance.
- `tools/ci_gate.py` (fails on unapproved skips, runs `-O`, writes digest-bound evidence), `tools/release_gate.py`, `tools/check_compat.py`, `tools/check_master_md.py`, `tools/build_trace.py`, `tools/preflight.py`, `tools/restore_drill.py`, `.github/workflows/ci.yml`.
- Traceability: `traceability/trace_matrix.json` (C001–C100) and `traceability/CHECKLIST_STATUS.json` (all 2 346 sub-items), both machine-checked.
- Docs: architecture, requirements, interfaces, 7 ADRs, threat model, consensus contract, compatibility matrix, capacity, DR plan, rollout, telemetry and security policies, fault catalog, day-0/1/2 and incident runbooks, governance, exceptions register (EX-001..EX-009).
- Deploy: Dockerfile, hardened systemd unit, StatefulSet, NetworkPolicy, config overlays, backend and pk_core pin files; Grafana dashboards and Prometheus alert rules.

### Not closed (owner decisions / external artefacts)
Consensus backend pin + adapter (EX-001), MASTER.md decision (EX-002), pk_core pin (EX-003), adjacent-layer environments (EX-004), target-hardware performance (EX-005), named approvers (EX-006), outbound licence (EX-007), signing identity (EX-008), dependency hashes (EX-009).

## 4.2.0 - 2026-09-22

Audit, parse, fix, harden, and version-bump pass.

### Correctness and concurrency

- Moved the reference control-state implementation into framework-independent `state.py`.
- Made compare-and-swap comparison plus mutation atomic with a re-entrant lock, closing the race where concurrent controllers could evaluate the same stale revision outside a serialization boundary.
- Serialized watch snapshots and compaction against writes so each returned view is internally consistent.
- Added strict validation for keys and non-negative integer revisions; booleans, negative revisions, non-integers, empty keys, and NUL-containing keys fail closed.
- Returned copies from `data` and `history` accessors so callers cannot mutate the store's containers behind the transaction API.
- Added a direct `get()` read primitive for revision-aware local conformance checks.

### Test and dependency integrity

- Fixed the false-positive standalone test posture: version and reference-model tests now execute even when `pk_core` is absent.
- Added six stdlib-only state tests, including a 16-contender CAS race, compaction-gap checks, validation checks, and snapshot-isolation checks.
- Verified the same standalone suite under normal Python and `python -O`; only the two explicit framework conformance tests are skipped without `pk_core`.
- Changed package exports to lazy-load framework-bound objects so version metadata and the reference state model can be imported without `pk_core`.

### Documentation and evidence integrity

- Corrected evidence pointers from `component.py::ControlState.*` to `state.py::ControlState.*`.
- Removed the README claim that `MASTER.md` is bundled; the absent file is now explicitly tracked as a missing component.
- Clarified that the in-memory model is not a persistent/replicated production store and that full 100-item certification requires the external framework.
- Added `AUDIT_REPORT.md`, `MISSING_COMPONENTS.md`, and a SHA-256 integrity manifest.

### Residual gate status

- Standalone reference-model checks: PASS.
- Full 100-item `pk_core` gate: NOT EXECUTED in this isolated archive because `pk_core` is not bundled.
- Production distributed-service readiness: NOT CLAIMED; remaining components are listed in `MISSING_COMPONENTS.md`.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py (systemic): confirmed the former side-effecting assert on txn() now runs inside _verify(...) arguments, so python -O executes it and passes
- component.py::ControlState.compact: compacting to a revision beyond the current one set compacted_at in the future, making changes not yet written permanently unwatchable (breaks "deliver every change after a watch's start") -> reject rev outside [0, revision] with ValueError
- component.py::ControlState.watch: on a never-compacted store watch(0) raised Compacted although no history was discarded; non-int/negative revisions were accepted -> refuse only when a compaction actually happened, validate from_rev

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
