# INV-07 Audit Report — v4.2.0

## Audit scope

Static and executable review of the uploaded `inv07_gitops_transition_layer` archive. The audit examined package structure, version consistency, checklist metadata, reference GitOps behavior, tests, and documentation claims. No network access or external `pk_core` package was assumed.

## Key findings fixed in 4.2.0

- Replaced Python-`repr` state signing with canonical JSON serialization so signatures are deterministic across dictionary insertion order and reject unsupported/non-finite values.
- Replaced truncated SHA-1 commit identifiers with full SHA-256 commit identifiers over a deterministic commit envelope.
- Deep-copied retained desired state so nested caller mutations cannot silently rewrite commit history after creation.
- Serialized controller mutations with `threading.RLock` to remove obvious same-process races in the reference model.
- Made same-head synchronization idempotent in applied history while preserving drift detection and reconciliation reporting.
- Enriched drift reports with both the commit against which drift was detected and the commit to which reconciliation converged.
- Added a secret-free `status()` snapshot and an explicit `verify_head()` operation.
- Split the dependency-free GitOps model into `gitops_model.py`, leaving the `pk_core` component adapter in `component.py`.
- Added nine standalone unit tests that run even when `pk_core` is absent.
- Corrected documentation that previously implied `MASTER.md` was bundled when it is not.
- Corrected conformance language: the external 100-item `pk_core` gate cannot be reproduced from this archive alone because `pk_core` is not included.
- Added `MISSING_COMPONENTS.md` with prioritized production gaps.

## Residual limitations

The HMAC signing helper remains intentionally a dependency-free test primitive and is not a production substitute for protected Git refs plus asymmetric signature/provenance verification. The archive still lacks the real Git/controller adapters, durable state, authorization, telemetry, interface schemas, integration tests, deployment artifacts, and other items listed in `MISSING_COMPONENTS.md`.

## Validation performed

- Python bytecode compilation for all Python sources.
- JSON parse validation for `CHECKLIST.json`.
- Dependency-free unit test execution in normal interpreter mode.
- Dependency-free unit test execution with `python -O`.
- Static scan for legacy SHA-1/`repr` signing use, `eval`/`exec`, `shell=True`, unsafe pickle/YAML use, and implementation bare assertions.
- Archive path-safety check before extraction.

The `pk_core` conformance tests remain skipped in this isolated archive because `pk_core` is not present. That condition is now reported as a dependency limitation rather than treated as evidence of successful execution.
