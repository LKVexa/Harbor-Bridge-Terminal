# INV-32 - Elastic virtualization

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

Elastic virtualization is the live adjustment of guest memory and vCPU allocation while the guest remains running. The reference model implements bounded memory growth/reclaim, vCPU hot-plug, free-page reporting, replay-safe operations, validated rollback, and host-reserve protection.

## v4.3.0 — production control plane (reference provider)

v4.3.0 executes the *INV-32 v4.2.0 Missing Components Implementation Checklist*. Status per bullet:
`CHECKLIST_EXECUTION.md` (human) / `RTM.json` (machine). **Production exit gate: FAIL** — honest blockers are
the missing HyperFlux spec, named owners, hosted CI/provenance, PKI, and real hardware
(`evidence/exit_gate.json`). The package must not control a real hypervisor until the gate passes.

| Area | Module | Doc |
|---|---|---|
| Mutation pipeline, recovery, health, explain | `controller.py` | `docs/ARCHITECTURE.md` |
| Hypervisor boundary, fake/reference, fail-closed HyperFlux shell | `adapters/` | `docs/adr/ADR-0001-hyperflux-provider.md` |
| External schemas, decoder, conformance vectors | `validation.py`, `schemas/`, `conformance/` | `docs/INTERFACES.md` |
| AuthN/AuthZ | `authz.py` | `docs/THREAT_MODEL.md` |
| Config lifecycle | `config.py` | `ops/site.example.json` |
| Durable journal / signed audit / anchors / backup | `store.py` | `docs/FAILURE_MODEL.md` |
| Leases & fencing | `fencing.py` | ADR-0003 |
| Health, watchdog, quarantine | `health.py` | `docs/RUNBOOKS.md` |
| Retry/circuit/admission | `resilience.py` | `docs/INTERFACES.md` |
| Tenant quota & fairness | `quota.py` | `docs/REQUIREMENTS.md` |
| Metrics/logs/traces/redaction | `telemetry.py` | `docs/OBSERVABILITY.md`, `ops/` |
| Bootstrap preflight | `bootstrap.py` | `docs/RUNBOOKS.md` Day-0 |
| Benchmarks & regression gate | `bench.py` | `docs/PERFORMANCE.md` |
| SBOM, SAST, RTM check, evidence, exit gate | `release.py` | `../RELEASE.md` |

Quick start (stdlib only, Python ≥ 3.10):

```bash
python -m unittest discover -s inv32_elastic_virtualization/tests -t inv32_elastic_virtualization/tests
python -m inv32_elastic_virtualization.bootstrap --check --state-dir /tmp/inv32
python -m inv32_elastic_virtualization.conformance_check
python -m inv32_elastic_virtualization.release rtm-check
```

## Responsibility

Own live resource adjustment for running guests: grow and shrink guest memory and vCPUs within declared floors and ceilings, never reclaim below a guest's working-set floor, and refuse an adjustment that would oversubscribe the host past its reserve.

## Hardened reference model

`model.py` is deliberately independent of `pk_core` so the safety-critical state machine can be tested on its own. Version 4.2.0 adds:

- immutable guest allocation objects and strict type/range validation;
- configurable host reserve with conservative upward rounding;
- thread-safe guest/resource mutations;
- replay-safe `operation_id` handling and conflicting-replay rejection;
- stale rollback fencing;
- rollback type discrimination so vCPU records cannot mutate memory;
- exact-origin validation for v2 rollback records;
- hash-chained mutation evidence with fail-closed corruption detection;
- bounded free-page reports that do not silently change allocation;
- structured error codes/details for resource-policy failures;
- host resource snapshots with an audit-chain head.

## Owns

- Live memory reclaim and growth per guest
- vCPU hot-plug within declared guest bounds
- The configurable host reserve that is never allocated
- Guest working-set floors and ceilings
- Refusal of oversubscription past the reserve
- Local tamper-evident mutation history for reference-model operations

## Explicitly does not own

- Capacity targets
- Placement
- Guest applications
- The hypervisor's allocator
- Thermal ceilings

## Non-goals

- Deciding capacity targets
- Placing guests
- Guaranteeing a guest cooperates
- Overcommitting past the host reserve

## Interfaces

- `PK_RESOURCE_ADJUSTMENT/2` - replay-safe memory/vCPU adjustment plus validated rollback
- `PK_HOST_RESOURCES/1` - total, reserved, allocated, free, guest count, and audit head
- `PK_RESOURCE_AUDIT/1` - local SHA-256 hash-chained mutation evidence

See `SCHEMAS.md` for the repository-local mapping contracts and legacy v1 compatibility rules.

## Service-level objectives represented by the contract

- **reserve** - zero allocations into the host reserve (error budget: no budget)
- **floors** - zero guests reclaimed below their working-set floor (error budget: no budget)
- **reversibility** - 100% of non-stale applied adjustments reversible to the prior value (error budget: no budget)
- **audit-integrity** - zero accepted mutations after local audit-chain corruption (error budget: no budget)

These contract SLOs are invariants of the reference model, not a substitute for measured production latency/availability objectives. Performance and operational SLO evidence is listed as missing in `AUDIT_REPORT.md`.

## Validation

Run the standalone safety tests from this directory:

```text
python tests/test_model.py
python tests/test_component.py
```

`tests/test_model.py` is stdlib-only and exercises the resource state machine directly. `tests/test_component.py` always checks package-version consistency; its inventory/checklist adapter tests additionally require the sibling `pk_core` package. This archive does not bundle `pk_core`, so those adapter tests skip unless `PK_CORE_PATH` points to a compatible copy.

In the complete inventory repository, the expected adapter commands remain:

```text
python -m pk_core list
python -m pk_core run INV-32 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-32 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

## Production-readiness status

This package is a hardened reference component, not a standalone production-complete virtualization subsystem. The post-update audit does **not** treat generic checklist findings from an external framework as proof that implementation-specific production evidence exists here. See `AUDIT_REPORT.md` and `AUDIT_REPORT.json` for the complete repository-local gap matrix and missing-component inventory.

## Day-0 / day-1 / day-2 baseline

- **Day 0:** run the standalone model tests, resolve the external `pk_core` dependency, then capture the first complete evidence/gate outputs.
- **Day 1:** integrate the real hypervisor/control-plane adapter, formal schemas, authentication/authorization, configuration, observability, and release controls identified in the audit.
- **Day 2:** continuously re-run safety, integration, compatibility, security, fault, performance, and release-gate suites and retain externally anchored audit/evidence history.
