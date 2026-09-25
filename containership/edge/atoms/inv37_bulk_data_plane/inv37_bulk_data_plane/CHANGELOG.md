# Changelog — INV-37

## 4.3.0 — 2026-09-22

Execution of `inv37_REMEDIATION_CHECKLIST_v4.2.0.md` (85 incomplete requirements). Posture remains **NO_GO**; see `REMEDIATION_STATUS.json`.

### New runtime modules (stdlib only)
- `outcomes.py` — outcome classes and 25-code error registry; `classify()`.
- `lifecycle.py` — 14-state transfer state machine with exhaustive transition table and idempotent repeats.
- `config.py` — `INV37_CONFIG/1` declarative config, typed units, layered profiles, security invariants, side-effect-free preflight, provenance, atomic activation with automatic/operator rollback.
- `checkpoint.py` — durable crash-consistent checkpoints (data-then-state write ordering, HMAC seal, re-hash on load), fencing epochs, quarantine, GC, storage quota.
- `security.py` — HMAC capability tokens, key ring rotation/revocation, replay cache, deny-by-default authorizer, hash-chained audit log, residency check, fail-closed encryption hook.
- `quota.py` — per-tenant quotas with weighted fair admission, pending bound, freeze.
- `retry.py` — cancel tokens with LIFO unwind and deadlines; registry-driven jittered retry with budget.
- `shm_transport.py` — intra-host zero-copy shared-memory path with HMAC-bound descriptors, revocation, in-place verification, copy counter, capability probe.
- `telemetry.py` — metrics with percentiles, structured redacted logs, W3C trace context, decision log, explain view, release lineage.
- `precedence.py` + `policy/precedence.json` — versioned policy precedence.
- `service.py` — `BulkDataPlane` façade composing all of the above; `negotiate()`; `PK_BULK_RESUME/2`.

### Fixes found during remediation
- Attaching processes no longer register foreign shared-memory segments with their resource tracker (CPython < 3.13 would unlink the owner's region when an attacher exited).
- Independent-review fixes: replay cache never evicts live nonces (fails closed when full); malformed signed claims → `authentication_failed`; node-scoped admin actions require a global admin; cross-process `flock` around lease acquire and check-then-write; bounds-check on checkpoint indices; certification fails on unexpected skips.
- `FairAdmission` grants immediately when capacity exists instead of counting the request against the pending-queue bound.

### Verification, gates and evidence
- Test suite grew from 16 to 150 tests (fuzz, crash-kill subprocesses, cross-process shm, bootstrap, gates, docs).
- `conformance/` — 31 locked fixtures, adapter-based runner, golden artifacts produced by the original 4.2.0 code.
- `benchmarks/bench.py`, `PERF_THRESHOLDS.json`, `tools/perf_gate.py`.
- `tools/run_certification.py`, `tools/production_gate.py` (19 criteria, digest-bound, signed, NO_GO today), `tools/check_governance.py`, `tools/check_pins.py`, `tools/check_requirements.py`, `tools/render_semantics.py`, `tools/render_status.py`, `tools/bootstrap.py`.
- Docs: REQUIREMENTS, SEMANTICS, INTERFACES, CONFIGURATION, THREAT_MODEL, FAILURE_MODES, PERFORMANCE, OBSERVABILITY, OPERATIONS; ADR-0001 rewritten (Proposed); governance/ (OWNERS, CODEOWNERS, WAIVERS, APPROVALS, DEPRECATIONS); new schemas.

### Compatibility
- 4.2.0 API unchanged; `PK_BULK_MANIFEST/1` and `PK_BULK_RESUME/1` still accepted. Build dependency pinned to `setuptools==79.0.1`.

## 4.2.0 — 2026-09-22

Repository audit, integrity hardening, dependency separation, and evidence correction.

### Correctness and security fixes

- Split dependency-free data-plane behavior into `data_plane.py`; package import no longer fails merely because optional `pk_core` is absent.
- Added strict untrusted-manifest validation for schema, algorithm, digest syntax, geometry, chunk count, and resource ceilings.
- Added `TransferLimits` with fail-closed object-size, chunk-size, chunk-count, and concurrent-transfer bounds.
- Receiver now copies/normalizes the validated manifest at initialization to remove a post-validation mutation (TOCTOU) weakness.
- Receiver now validates exact chunk length as well as chunk index and digest.
- Duplicate verified chunks are explicitly idempotent; conflicting duplicates fail closed.
- Receiver mutation is protected for parallel distinct-chunk delivery.
- Partial assembly now raises structured `TransferIncomplete`; closed receivers reject further writes.
- Final object verification compares the complete recomputed chunk list as well as the inherited object digest.
- Digest comparisons use `hmac.compare_digest` where applicable.
- Added a process-local `BoundedTransferPool` with bounded semaphore admission and saturation counters.
- Added stable machine-readable error codes/details in `errors.py`.

### Contract and packaging hardening

- Added JSON Schemas for `PK_BULK_MANIFEST/1`, `PK_BULK_CHUNK/1`, and `PK_BULK_RESUME/1`.
- Added a minimal `pyproject.toml` and package-data declarations.
- Added compatibility, security, operations, architecture-decision, technical-debt, and traceability documents.
- Removed the README's false reference to a nonexistent `MASTER.md`.
- Clarified that no production zero-copy host/guest/shared-memory transport is implemented and that the checklist's zero-copy architecture remains a blocker.

### Test/gate correction

- Added dependency-free unit/security/concurrency tests that always run without `pk_core`.
- Kept `pk_core` governance tests optional and made the skip explicit; absence of `pk_core` is no longer presented as proof that all 100 requirements pass.
- Re-audited all 100 checklist requirements from repository-owned evidence: 15 PASS, 37 PARTIAL, 48 MISSING.
- Added `SELF_AUDIT.json`, `TRACEABILITY.md`, and `MISSING_COMPONENTS.md`; the current self-audit gate is `NO_GO` and `production_ready` is false.

## 4.1.0 — 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- `component.py`: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O`.
- `tests/test_component.py`: stdlib conformance test added.
- `VERSION` file and `__version__` added.

### Defects fixed

- `Receiver.accept`: out-of-range index no longer raises `IndexError` or accepts negative indexing.
- `manifest`: invalid non-positive chunk sizes now fail explicitly.

### Historical gate claim

The 4.1.0 changelog stated that all 100 requirements were satisfied. The 4.2.0 evidence audit found that claim was not supported by repository-owned implementation/evidence and supersedes it.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
