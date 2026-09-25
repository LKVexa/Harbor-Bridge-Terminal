# Changelog - INV-71

## 4.3.0 - 2026-09-23

Production remediation pass against `INV71_v4.2.0_PRODUCTION_REMEDIATION_MASTER_CHECKLIST.md` (90 controls + 7 cross-cutting gaps + 10 global + 10 final = 1,730 lines). This pass ran through the junkyard chop shop with no donor parts.

### Added
- `control/`: a stdlib-only reference control layer with 13 modules (errors/outcomes, lifecycle + fencing, auth, egress DNS binding, resilience, config, artifacts, durable audit, telemetry, compat, qualification, runtime plan, controller).
- v2 session, egress and teardown schemas; error, status and config schemas; a deterministic conformance fixture bundle with fake INV-69/INV-24/INV-26/GAP-09 layers.
- Tools: evidence builder, fail-closed production gate, fuzz harness, reference benchmark and gate, fixture generator, doc renderer, pk_core probe.
- Governance data: 23 SHALL requirements, 16-row failure matrix, PROPOSED perf thresholds, RACI (UNASSIGNED), empty waiver register, review schedule, alert rules, and per-line checklist status.
- Docs: ADR-0001 v2 (still Proposed), ownership, architecture, security design, operations, observability and testing, production boundary, threat-to-test map; ten generated reference docs.
- pyproject.toml (zero dependencies), CI workflow (written, not executed), LICENSE_STATUS.md, THIRD-PARTY-NOTICES.md.

### Defects found and fixed by this pass's own tests and tools
1. `sandbox.canonicalize_host` accepted IPv6 zone IDs with arbitrary scope text (`fe80::1%eth0:`). Found by `tools/fuzz.py`. Zone IDs are now rejected; regression test added.
2. `SandboxController.create` registered and acknowledged a session before its audit record was durable, so an audit-sink outage left an unaudited READY session. Found by `test_audit_outage_fails_create_without_committing`. The audit record is now written first, and on refusal everything is undone.
3. `AuditStream.append` skipped the spool-size check when the file did not exist yet and could exceed its bound by one record. The size check now includes the record being written.
4. `LeaseTable` numbered epochs per sid, so leases could never be released without risking epoch reuse, and the table grew without bound. Found by `tools/bench.py` residual-memory growth. Epochs now come from one table-wide monotonic counter, and leases are released on compaction.
5. `IdempotencyStore` and the token replay cache removed expired entries only at capacity (100k). Found by `tools/bench.py`. Both now sweep periodically and on `compact()`.
- `tools/pk_core_probe.py` (new in this pass) left a probed `pk_core` importable for the rest of the process. It now restores `sys.path` and `sys.modules`.
6. A full token replay cache evicted still-valid nonces, so flooding the cache made replay possible. Found by the adversarial review. The cache now refuses with `CAPACITY.ADMISSION_REJECTED` rather than forget a live nonce.
7. `ConfigStore` stored approvals but never checked them, and never told participants to commit or abort. Found by the adversarial review. Staging now needs a non-author approver, activation is prepare/commit/abort, and rollback re-verifies the signature.
8. An egress capability lived a fixed 30 s whatever the DNS TTL. Found by the adversarial review. It now expires no later than its DNS answer.
9. The gate accepted a waiver whose two approvers were the same person. Found by the adversarial review. Approvers must now be distinct.
10. The first evidence build sealed the manifest before `REPO_AUDIT_RESULTS.json` was rewritten, so a fresh copy failed the integrity check. Found by the adversarial review. The build order is now fixed, and a fresh copy was re-checked.
- CLOSED now needs a typed `TeardownProof` built from reconciliation, not a free-form dict. It is still in-process and unsigned, so the line stays PARTIAL.
- Status corrections after review: DES lines were rescored per dimension, GATE-04 moved to PARTIAL, and C015-IMP-04, C024-IMP-03 and C036-IMP-02 moved to PARTIAL.

### Result
- Production gate: **NO_GO**. See `evidence/gate-result.json` for every blocker.
- `AUDIT_AFTER.json` is regenerated from traceability. See `MISSING_COMPONENTS.md` for the per-control breakdown.

## 4.2.0 - 2026-09-22

Repository audit, correctness fixes, hardening, evidence clarification, and version bump.

### Correctness and security fixes

- Replaced ambiguous filesystem digest serialization with length-prefixed records.
- Made the clean base snapshot immutable.
- Added canonical absolute guest-path validation and traversal/alias rejection.
- Added canonical DNS/IP handling and rejected URL/host:port ambiguity for egress decisions.
- Added validated session identifiers and fail-closed positive-limit validation.
- Added explicit ACTIVE/CLOSED lifecycle behavior and a dedicated SessionClosed failure.
- Teardown now clears guest-visible filesystem, connection/denial history, and egress capability data before reporting verified closure.
- Added bounded connection/denial histories and a bounded hash-chained reference audit log.
- Added method-level locking and atomic candidate-state quota checks.

### Auditability and packaging

- Split dependency-free reference semantics into `sandbox.py`; `pk_core` integration is now lazy.
- Added 12 standalone unit/adversarial tests; the 3 legacy conformance tests remain conditional on external `pk_core`.
- Added JSON Schemas for session, egress, and teardown records.
- Added proposed ADR, threat model, reproducible audit tool, machine-readable 100-control audit, and full missing-components report.
- Corrected README inventory: the uploaded archive did not contain the previously claimed `MASTER.md`.
- Clarified that the Python code is a reference model, not a production Firecracker isolation boundary.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::Session.write: overwriting a file counted old+new size, and overwriting a BASE file was never charged to quota -> exclude the path being replaced, charge modified base files
- component.py::Session.write/connect: worked after teardown (session resurrected with state) -> refuse when not alive
- component.py::Session.write: empty path / non-bytes data accepted -> ValueError

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
