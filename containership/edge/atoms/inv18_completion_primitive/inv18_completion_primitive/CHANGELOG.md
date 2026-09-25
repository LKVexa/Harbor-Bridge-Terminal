# Changelog - INV-18

## 4.3.0 - 2026-09-23

Missing-components remediation pass (junkyard chop-shop, `INV18_v4.2.0_missing_components_checklist.md`, 88 items).

### Added
- Governed `Runtime`: resolver/receiver/observer/admin capabilities (128-bit tokens, constant-time checks), tenant binding, process and per-tenant admission limits, writer-drop abandonment via capability finaliser, drain/freeze quarantine, health/stall detection, bounded tombstones so a second receiver still gets `AlreadyTaken` after release.
- `Future.cancel()`, `Future.wait(timeout)`, `Future.state`; `Cancelled` exception; every exception carries a stable `code`.
- Structured error taxonomy `PK_FUTURE_ERROR/1` with categories, retryability, precedence and redaction (`errors.py`).
- Versioned wire contracts + validator, canonical encoding, version negotiation (`wire.py`, `schemas/`), 15 executable fixtures, reference producer/consumer.
- HMAC bearer authentication with rotation/revocation/replay cache, fail-closed outages (`auth.py`); wire endpoint with idempotency keys and epoch fencing (`adapters.py`); bounded retry + circuit breaker (`retry.py`).
- Declarative configuration with fail-closed validation, layering, env allow-list, provenance, atomic activation, rollback (`config.py`, `config/`).
- Metrics, structured logs, W3C trace context, decision records, tamper-evident audit chain, status/explain, SLO report, alert rules and dashboard.
- Fault-injection harness (9 scenarios), benchmark/soak/scaling harness, capacity model, regression gate.
- Requirements (36 SHALL + 100 checklist), RTM generator, release gate with sealed evidence (`certify.py`), deterministic bootstrap, SHA256SUMS/SBOM/verify tooling, CI workflow.
- Governance: OWNERS, CODEOWNERS, ADR-001 (PROPOSED), threat model (20 threats), waiver/debt register, review register, 7 specification documents.

### Fixed (found by this pass's own tests)
- `ErrorRecord.from_dict` accepted non-object `details` (`[]`) and echoed malformed `original_code` from peers.
- After release, a second receiver got `PERMISSION_DENIED` instead of `FUTURE_ALREADY_TAKEN`; a producer resolving a cancelled future got `ALREADY_RESOLVED` instead of `FUTURE_CANCELLED`.
- Wire `fence` did not check tenant ownership (cross-tenant failover possible).
- Wire endpoint kept every future forever (unbounded registry).
- Type-mismatch rejections were not logged.
- `__init__` imported `pk_core` eagerly, so the primitive could not be imported without it.

### Compatibility
- 4.2.0 `Future` API unchanged; `abandon()` now returns a bool (was `None`); exceptions still subclass `RuntimeError`.
- `pk_core` integration unchanged but lazy.

## 4.2.0 - 2026-09-23

Correctness and concurrency hardening pass.

### Primitive hardening

- Extracted the completion state machine to `future.py` so it is independently testable without the external `pk_core` audit framework.
- Serialized resolve, abandon, status, and take transitions with a lock, closing races that could violate at-most-once resolution or single-receiver semantics under concurrency.
- Made abandonment terminal for unresolved writers; late value/error resolution is refused.
- Made abandonment after successful/error resolution a harmless no-op.
- Added constructor validation for the declared payload type and retained strict rejection of `bool` for non-`bool` numeric futures.
- Exported the primitive and its public exceptions from the package root.

### Verification

- Added standalone stdlib tests for success/error resolution, type rejection, abandonment semantics, 16-way concurrent resolution, and 16-way concurrent take.
- Updated integration version pin to 4.2.0.
- Full `pk_core` conformance remains environment-dependent because `pk_core` is not bundled in this repository.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::Future.resolve_error: None silently left future unresolved, '' read as success-ish -> TypeError for non-str/empty
- component.py::Future.resolve: bool accepted for int future -> TypeError

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
