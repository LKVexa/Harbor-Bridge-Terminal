# Changelog - INV-63

## 4.3.0 - 2026-09-23

Comprehensive remediation pass: executes `inv63_wasm_deployment_manager_v4.2.0_COMPREHENSIVE_REMEDIATION_CHECKLIST.md`
(92 work packages). Everything that can be built and proven inside the repository is in this release. Items that need
people, live infrastructure or hardware are tracked as external evidence and keep the gate at BLOCKED; see
`MISSING_COMPONENTS.md`.

### New runtime (all stdlib plus pinned `cryptography==46.0.7`)

- `service.py` — `DeploymentService`, the production layer around `Manager`. It adds typed requests, authentication
  and capability authorization, tenant namespacing, admission and quotas, idempotency keys and deadlines. It also adds a
  lifecycle state machine and a journal that is durable, fenced and encrypted. Reconciliation starts new instances
  before stopping old ones, with retry and a circuit breaker. Rollouts can use a canary, stay within `max_unavailable`
  and roll back automatically. Operators can also trigger a rollback. When the control plane is unreachable the
  service keeps working in a degraded offline mode and resyncs later. It adds freeze, quarantine, host quarantine and
  emergency disable, applies the precedence rules, and exposes status and explain views, plus snapshot compaction.
- `errors.py` (outcome semantics and error codes), `lifecycle.py`, `schema.py` + `schemas/*.json` (9 versioned
  contracts, strict validator, version negotiation), `security.py` (HMAC tokens with replay protection, roles and
  capabilities, Ed25519 artifact verification, AES-256-GCM `Sealer`, secret refs and redaction), `store.py`
  (fsync'd hash-chained journal, torn-tail recovery, epoch fencing, backup/restore, compaction), `resilience.py`,
  `config.py` (secure defaults, overlays, secret scan, atomic activation and rollback with provenance),
  `observability.py` (Prometheus metrics, structured logs, W3C trace context, decision log and explain view,
  alert classes), `preflight.py`, `adapter.py` (`InMemoryLattice` fixture and `WadmAdapter` that renders OAM
  manifests and implements the full adapter protocol over an injected transport).
- `audit.py` (executable audit: regenerates `AUDIT_RESULTS.json`, `MISSING_COMPONENTS.md` and the
  traceability matrix from test results and approvals), `gate.py` (signed production exit gate: PASS, FAIL,
  BLOCKED, SKIPPED, NOT_RUN, WAIVED), `evidence.py`, `perf/bench.py` (reproducible benchmarks plus a regression gate),
  `tools/bootstrap.py`, `tools/gen_fixtures.py`.

### Changed (backward compatible)

- `Manager.diff` accepts an optional `eligible_hosts` argument (residency and quarantine). Host placement now uses
  per-zone heaps: the cold 1000-instance diff dropped from about 29 ms to about 2.7 ms p50. A 300-case randomized
  test proves it picks the same hosts as the old algorithm.
- Version 4.2.0 → 4.3.0 (additive).

### Defects found and fixed during the pass

- Config: a secret embedded in a malformed value was reported as a schema error (and could be echoed back).
  Secrets are now checked first.
- Trace context: the inbound parent span id was dropped. Spans are now also recorded for failed requests.
- Journal: a second writer handle could append over a stale view. Concurrent writes are now detected (`CONFLICT`).
- Internal review regressions: operator rollback could bypass a freeze or emergency disable. Operator controls
  accepted a free-text actor with no authorization. Encryption at rest was not enforced. The FAILED and DELETED states
  could not be reached. The offline autonomy window used the wall clock. `status()` computed the config digest
  differently from `config.config_digest`.

### Evidence

- 100+ tests, each tagged with the INV-63 C-IDs it evidences, cover adversarial, fuzz, concurrency, fault injection,
  crash replay, gate and bootstrap cases.
- The final verdict is **BLOCKED**, as it should be. It does not certify production until the owners supply the
  external evidence listed in `governance/EXTERNAL_EVIDENCE.json`.

## 4.2.0 - 2026-09-22

Standalone audit and hardening pass.

### Core hardening

- Extracted the reconciliation engine into dependency-light `manager.py`, so deployment behavior can be tested even when the inventory-wide `pk_core` framework is not installed.
- Added strict validation for identifiers, hosts, desired state, diffs, spread flags, counts, and rollout bounds.
- `Manager.apply` now validates the complete diff and next state before commit, preserving transactional/no-partial-mutation behavior on invalid input.
- Runtime state is revalidated before decisions and mutations; instances on unknown hosts now fail closed instead of being silently retained.
- Placement is deterministic and balances both spread labels and per-host replica counts.
- Added explicit in-memory desired-state storage and `reconcile()` for convergent reconciliation.
- Added hash-chained audit records for desired-state changes, reconciliation plans, applied diffs, and rollout batches, plus chain verification.
- Package-level imports are lazy so core manager tests are not blocked by the optional external audit framework.

### Test hardening

- Added self-contained unit tests for convergence, deterministic spreading, bounded rollout, transactional apply, hostile/malformed inputs, unknown-host state, audit-chain tamper detection, checklist integrity, and optimized-mode execution.
- Updated the inventory-framework conformance test version pin to 4.2.0 and clarified that framework conformance is skipped when `pk_core` is unavailable rather than treating that skip as standalone production proof.

### Audit correction

- Removed the README claim that `MASTER.md` is included; the source archive does not contain that file.
- The standalone post-update audit does **not** treat the historical 4.1.0 statement “all 100 requirements satisfied” as sufficient evidence. Remaining production gaps are listed in `MISSING_COMPONENTS.md` and `AUDIT_REPORT.md`.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::Manager.rollout: max_unavailable < 1 sliced to [] and returned (0, 0) as if rollout had finished while old versions kept running -> ValueError
- component.py::Manager.diff: negative count accepted; empty host map crashed in min()/index; instances on unknown hosts raised KeyError -> validation + hosts.get
- component.py::Manager.apply: stop of a non-running instance raised mid-loop after partial mutation -> checked up front, LookupError, no partial apply

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
