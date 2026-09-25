# Changelog - INV-38

## 4.2.0 - 2026-09-22

Second audit, fix, hardening, and evidence-quality pass.

### Data-path hardening

- Extracted the dependency-independent queue model to `transport.py` so its safety properties can be tested without `pk_core`.
- Added strict integer/configuration validation, configurable address-width enforcement, registered-region ceilings, and bounded completion capacity.
- Prevented deregistration of memory regions while descriptors for that key remain in flight.
- Snapshotted mutable bytes-like payloads at post time to prevent post-validation mutation/TOCTOU behaviour in the asynchronous model.
- Added a re-entrant lock around registration, posting, polling, completion consumption, and state gauges.
- Added stable machine-readable error-code attributes to queue exceptions.
- Preserved completion ordering during kernel fallback while making capacity failure lossless.

### Verification and repository integrity

- Added 9 standalone transport safety tests, including range overflow, stale/busy keys, capacity bounds, mutable-payload snapshotting, fallback ordering, and concurrent posting.
- Added repository-integrity tests for checklist cardinality, synchronized version metadata, optimizer-safe production sources, and missing-document references.
- Corrected the README's false claim that `MASTER.md` was included.
- Added `DEPENDENCIES.md` to make the absent external core, sibling integrations, and unpinned hardware/runtime dependencies explicit.
- Made package import degrade explicitly when `pk_core` is absent, allowing standalone tests/transport use while exposing `PK_CORE_AVAILABLE = False` and failing contract construction with `CoreUnavailableError`.
- Added `AUDIT_REPORT.md` with the post-change checklist/evidence gap analysis.

### Gate status

The standalone tests pass in normal and `python -O` modes. The `pk_core`-backed 100-item conformance tests remain non-executable in this archive because `pk_core` is not bundled; they correctly report skips rather than serving as release evidence.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::BypassQueue.post: negative length bypassed bounds check, payload longer than declared length accepted -> both refused as OutOfBounds
- component.py::BypassQueue.register: negative base / non-positive length registered -> OutOfBounds
- component.py::BypassQueue.post: kernel fallback appended completion ahead of still-queued bypass work (out of order) -> drains ring first

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).

## Remediation pass — v4.2.0 missing-components checklist (2026-09-22)
Added repository-owned artifacts, executable model modules and tests for the 50
MISSING requirements (C009…C099). Machine-readable status: `traceability/INV38_RTM.json`;
re-audit: `AUDIT_REMEDIATION_REPORT.md`; release acceptance: `release/PK_ACCEPTANCE.json`.
No requirement dependent on RDMA hardware or `pk_core` is marked DONE from this
archive; those are IN_PROGRESS/BLOCKED with named blockers. No reference-model
behaviour is presented as hardware certification.
