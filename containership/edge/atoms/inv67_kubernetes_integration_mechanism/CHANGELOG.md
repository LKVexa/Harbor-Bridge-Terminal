# Changelog — INV-67

## 4.3.0 — 2026-09-22

Applied `INV67_v4.2.0_MISSING_COMPONENT_IMPLEMENTATION_CHECKLIST.md` (68 components).

### Added
- `plane/`: `WasmWorkload` controller/reconciler with finalizers, generation/attempt tracking, conditions and status subresource writes; `FakeKube` API server and https-only `HttpKubeClient`; `PK_K8S_PLACE/1` downstream adapter with idempotency keys and fencing; lifecycle state machine and stable error taxonomy; config schema with atomic activation, provenance and rollback; secretRef provider; identity mapping; authn/authz policy; artifact registry/digest/attestation verification; GAP-15 certification; constraint precedence; hash-chained audit trail; backoff/retry budget/circuit breaker/admission/freeze/quarantine; lease election with fencing; crash-consistent intent journal; metrics/logs/traces/health endpoints/explain view; capacity model; deterministic bootstrap.
- CRD, RBAC, Deployment, NetworkPolicy, PDB, kustomize overlays (generated, drift-checked).
- Schemas: `PK_K8S_PLACE/1`, `INV67_CONDITION/1`, `INV67_CONFIG/1`, `INV67_EVIDENCE/1`.
- Docs: ownership, ADR-001, 46 SHALL requirements, lifecycle, compatibility, capacity, disconnected mode, precedence, threat model, SLOs, runbooks, incident/vulnerability/review policies, telemetry policy/alerts/dashboard, exceptions ledger, release gate.
- Tests: 102 new (117 total) (unit, contract, integration, security, fuzz, fault, concurrency, performance).
- `governance/`: executable 68-component gate, release manifest/verify, SBOM; `pyproject.toml`; CI workflow; ruff/mypy config.

### Fixed (found by this pass's own tests)
- Retry budget accumulated float drift (0.1 × 10 < 1.0) and refused a retry it had earned — now integer milli-tokens.
- Work queue discarded the requeue delay when a key re-queued itself while being processed, turning backoff into a hot loop (the freeze test hung) — delay now preserved; per-pass cap added.
- Alert/dashboard metrics that had not yet fired were absent series, so `rate()` alerts could never fire — counters are pre-registered at zero.
- `import inv67_kubernetes_integration_mechanism` required `pk_core`; translator/plane now import standalone (pk_core component exported only when present).

### Changed
- `contract.py` imports `pk_core` lazily. README non-goal "operators/controllers" superseded by ADR-001.

## 4.2.0 — 2026-09-22

Second audit, correctness, hardening, and independent re-audit pass.

### Correctness fixes

- Added explicit mapping of resource **limits**; v4.1.0 declared request/limit fidelity but translated only requests.
- Added annotation and namespace preservation; v4.1.0 declared annotation mapping but emitted labels only.
- Preserved the v4.1 `cpu`/`memory` request aliases while adding canonical `requests` and `limits` objects.
- Split pure translation primitives into `translator.py`, removing the `pk_core` dependency from the untrusted-input translation boundary.

### Fail-closed hardening

- Replaced permissive field dropping with a strict supported-subset validator; unknown Pod/spec/container/resource fields are now refused by path.
- Added structured `TranslationError`, `Unsupported`, and `InvalidPod` errors with stable codes and `PK_K8S_REFUSE/1` machine-readable detail.
- Init containers, volumes, non-empty security contexts, host networking, and host PID semantics are now explicitly refused when they cannot be represented.
- Privileged containers and hostPath mounts retain specific security refusal reasons.
- Added type/shape validation, non-empty container validation, duplicate container-name rejection, string-map validation, and input non-mutation tests.
- Reworked Kubernetes quantity parsing around `Decimal`, expanded supported SI/BinarySI/exponent forms, bounded input length/range, and rejected malformed/negative/non-finite values.

### Contracts and tests

- Added JSON Schemas for `PK_K8S_TRANSLATE/1`, `PK_K8S_REFUSE/1`, and `PK_K8S_STATUS/1`.
- Added 12 standalone translator/version/schema unit/security tests that pass under normal and optimized (`python -O`) execution.
- Updated the checklist harness to exercise limits, annotations, namespace-aware translation, and structured security refusals.
- Corrected README claims that previously implied absent master-prompt material was present, and documented the actual supported subset and remaining gate limitations.

### Re-audit

- Added `AUDIT_REPORT.md`, separating fixed implementation defects from remaining production components that are absent or only declarative.

## 4.1.0 — 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- `component.py`: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O`.
- `component.py`: expected-refusal checks fail if the refusal does not happen.
- `tests/test_component.py`: stdlib conformance test added (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- `VERSION` file and `__version__` added.

### Defects fixed

- `component.py::translate`: privileged initContainers were checked; `securityContext: null` tolerated.
- `component.py::quantity`: fractional and decimal-SI quantities no longer crash; negative/NaN rejected.

### Gate

The v4.1.0 changelog stated all 100 requirements were satisfied under Python and `python -O`; the v4.2.0 independent repository re-audit does **not** treat that self-assessment as sufficient production evidence. See `AUDIT_REPORT.md`.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
