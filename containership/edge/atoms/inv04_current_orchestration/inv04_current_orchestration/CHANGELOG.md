# Changelog - INV-04

## 4.3.0 - 2026-09-22

Missing-components engineering pass against `INV04_v4.2.0_Missing_Components_Professional_Checklist.md` (80 components). Every component now has executable evidence, a typed port, or a governance artifact, and its state is machine-checked. **No component is marked PASS.** PASS requires green CI evidence on the supported matrix, and this release has not been run in the owner's CI.

### Added: `runtime/` production layer (stdlib only)

- `errors.py`: 26 new stable error codes with retry classification and HTTP / gRPC / Kubernetes-Status mapping (#22, #26, #34).
- `objects.py`: typed immutable Pod/Node/PDB projections and `from_k8s_pod` fail-closed wire conversion (#1).
- `store.py`: `VersionedStore` with compare-and-swap resourceVersion, UID preconditions, generation / observedGeneration, and a durable fsynced JSONL log that tolerates a torn tail. `Informer` provides list/watch, bookmarks, a watch-expiry relist, tombstones, a sync barrier and a staleness guard (#2, #4, #6, #52).
- `workqueue.py`: deduplicating keyed queue with dirty/processing sets, rate-limited requeue, bounded depth and shutdown (#3, #35).
- `lease.py`: CAS leader election with monotonically increasing fencing tokens and `FencingGuard` (#5).
- `journal.py`: hash-chained write-ahead journal, idempotency registry, audit trail and secret redaction (#21, #22, #43, #50).
- `policy.py`: full policy/v1 PDB evaluator (int/percent, min/max, expected scale, unhealthy-pod policy, multiple-PDB refusal); mirror, DaemonSet, Job, unmanaged and local-storage drain classification; StatefulSet ordering and quorum; PV constraints; termination lifecycle; node health and partition semantics (#10–#17).
- `scheduling.py`: capacity, taints/tolerations, selectors, required node affinity, anti-affinity, topology spread, drain capacity plan, and budget-safe preemption (#18–#20).
- `api.py`: `ClusterAPI` port, fail-closed discovery, and an in-memory reference API server with Eviction-subresource semantics and a controller simulator (#1, #9, #54).
- `drain.py`: journaled drain transaction coordinator (preflight → cordon → evict → verify), rollback before the point of no return, `failed_cordoned` after it, and `recover()` after a crash (#7, #8).
- `validation.py`: bounded JSON-Schema runtime validator for the shipped schemas, and revision negotiation (#23, #25).
- `security.py`: HS256 token authn (iss/aud/exp/nbf/TTL/kid), deny-by-default RBAC with cluster-scoped drain, admission windows and freezes, tenant scoping, fair per-tenant queue, and `Secret`/`SecretResolver` (#27, #28, #30–#32, #43).
- `handoff.py`: snapshot identity and digest, change stream with gap detection, ack/resume session, dedupe receiver, and ownership registry (#36–#39).
- `config.py`: typed bounded config with env/site overlays, provenance-recorded activation, health-checked auto-revert and rollback (#40–#42).
- `observability.py`: Prometheus-format metrics with a cardinality cap, redacted JSON logs, W3C trace spans, health/readiness/liveness, convergence SLO engine, and multi-window burn-rate alerts (#44–#49).
- `resilience.py`: deadline/cancellation context, retry with backoff, jitter and budget, token bucket, circuit breaker, and stall detector (#33–#35, #51, #53).
- `service.py`: `Orchestrator` + `Service` HTTP/JSON transport with an ordered trust-boundary pipeline and problem+json errors (#24, #47).

### Schemas and fixtures

- PK_ORCH_DRAIN/1 revision 1.1 (optional `idempotency_key`, `dry_run`, `delete_emptydir_data`, `force_unmanaged`) and PK_ORCH_ERROR/1 revision 1.1 (all codes, optional `details`). Both are additive and negotiated.
- `fixtures/`: 19 positive and negative conformance vectors with digests (#79).

### Tests (106 dependency-free, all green under normal and `-O`)

- New suites: runtime core, policy, drain (including crash recovery and a 60-trial chaos run), interface/security/service, ops, and properties (state machine, fuzz, concurrency, v4.2↔v4.3 parity harness) (#54–#57, #59).
- The parity harness found and fixed a simulator defect: controller templates were derived from live pods, so a workload whose last pod was evicted was never recreated.

### Release engineering and governance

- `pyproject.toml`, `constraints.txt`, `.github/workflows/ci.yml` (3 OS × 4 Python × normal/-O, static, conformance, soak, release).
- `tools/`: `evidence_gate.py` (#76, #77), `sbom.py` (CycloneDX 1.5, #65), `release.py` (deterministic zip, manifest, unsigned SLSA provenance statement, verify, #66, #71), `lint_gate.py` (#67, #70), `pk_core_gate.py` (fails when absent, #78), `bench.py` (#60, #62).
- `docs/`: ADR-0001 (architecture), ADR-0002 (MASTER.md decision, pending owner), THREAT_MODEL, RUNBOOK, OWNERS (roles UNASSIGNED), ROLLBACK, generated TRACEABILITY.
- `COMPONENT_STATUS.json`: machine-readable state of all 80 components.
- `tests/test_component.py`: version pin reads VERSION. `INV04_REQUIRE_PK_CORE=1` turns a missing pk_core into a failure instead of a skip.

### Compatibility

- `model.Cluster` and the PK_ORCH_RECONCILE/INVENTORY schemas are unchanged. See `docs/ROLLBACK.md`.

## 4.2.0 - 2026-09-22

Audit, correctness, hardening, interface-artifact, and testability pass.

### Correctness and atomicity

- Moved the dependency-free orchestration state machine into `model.py`.
- `Cluster.reconcile()` now validates and plans completely before committing changes; an invalid later workload can no longer leave earlier workloads partially mutated.
- `Cluster.drain()` now uses plan-then-commit semantics. A budget refusal or `NoCapacity` failure leaves nodes and pods unchanged.
- Reconciliation order is deterministic across desired-state mapping insertion order.
- Running pods on unknown nodes or for unmanaged workloads now fail closed as state-integrity errors.

### Validation and error hardening

- Reject duplicate/blank nodes, malformed pod tuples, boolean/non-integer/negative counts, orphan disruption budgets, and `min_available > desired`.
- Added stable machine-readable error codes and `as_dict()` envelopes.
- Package initialization is lightweight; the core model remains importable without `pk_core`.

### Interfaces and evidence

- Added JSON Schema 2020-12 artifacts for `PK_ORCH_RECONCILE/1`, `PK_ORCH_DRAIN/1`, `PK_ORCH_INVENTORY/1`, and `PK_ORCH_ERROR/1`.
- Added `AUDIT_REPORT.md` and a prioritized 80-item `MISSING_COMPONENTS.md`.
- Corrected README: removed the false claim that the absent `MASTER.md` prompt corpus was bundled.

### Tests

- Added dependency-free model safety tests, including failed-drain atomicity, failed-reconcile atomicity, deterministic placement, invariant validation, inventory determinism, and stable error codes.
- Added artifact-integrity tests for version synchronization, checklist cardinality, schema parse/version markers, and audit artifacts.
- Core tests pass under normal Python and `python -O`. Estate-level `pk_core` conformance tests remain conditional on the external framework being installed.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::Cluster.drain: unknown node raised a bare ValueError from list.remove -> check first and raise UnknownNode (new LookupError subclass) before any mutation
- component.py::Cluster.drain: budget check iterated a set, so which breaching workload was named was non-deterministic -> iterate sorted workloads
- component.py::Cluster.reconcile: scheduling with no nodes left crashed with min() ValueError; negative desired counts silently removed a pod via running[-1:] -> raise NoCapacity / ValueError
- component.py::Cluster: mandatory "Expose workload inventory for hand-off" had no implementation -> added Cluster.inventory() (workload -> sorted nodes)

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
