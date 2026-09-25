# INV-68 — Resource packing

**Version:** 4.3.0  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

Resource packing decides how many workloads fit on how many hosts. Packing well
means fewer hosts for the same work; packing carelessly means one dimension —
usually memory — runs out while CPU sits idle. The packer places across every
supported dimension at once, keeps a headroom reserve, never overcommits memory,
and reports stranded capacity.

## Responsibility

Own multi-dimensional first-fit-decreasing placement, headroom reservation,
per-dimension overcommit policy, lower-bound capacity calculation, fragmentation
reporting, and machine-readable placement explanations.

## Owns

- Multi-dimensional placement for CPU and memory.
- The packing service boundary: authn/authz, tenancy, limits, idempotency, audit, status, explain.
- Its configuration lifecycle (validated, versioned, audited, rollback-able).
- Headroom reservation on every host.
- CPU overcommit policy and strict no-memory-overcommit policy.
- Lower-bound and effective-capacity calculations.
- Fragmentation reporting.
- Deterministic placement/unplaced decision records.

## Explicitly does not own

- Workload classification.
- Host provisioning.
- Thermal policy.
- Accelerator matching.
- Preemption.

## Interfaces

- `PK_PACK/1` — workloads to host assignments and placement decisions.
- `PK_PACK_CAPACITY/1` — per-host capacity/effective-capacity shape.
- `PK_PACK_FRAG/1` — stranded-capacity report.
- 4.3.0: `PK_PACK_SERVICE_RESPONSE/1`, `PK_PACK_ERROR/1`, `PK_PACK_CONFIG/1`,
  `PK_PACK_STATUS/1`, `PK_PACK_EXPLAIN/1`, `PK_PACK_AUDIT/1`.

Versioned JSON Schema 2020-12 contracts are under `schemas/`; request/response
fixtures are under `examples/`.

## Core API (pure engine, stdlib only)

`packing.py` is independent of `pk_core` and of the service layer:

```python
from inv68_resource_packing import pack_detailed, fragmentation, lower_bound

result = pack_detailed(
    [{"name": "api", "cpu": 2, "mem": 8}, {"name": "worker", "cpu": 6, "mem": 12}],
    host_cpu=16, host_mem=64, headroom=0.1, cpu_overcommit=1.5,
)
print(result.assignments, fragmentation(result.hosts))
print(lower_bound(..., placeable_only=True))  # 4.3.0: bound over placeable work
```

`pack(...)` keeps the original `(list[Host], list[str])` shape. 4.2.0 calls work
unchanged; `cpu_overcommit` and `placeable_only` are new optional keywords.

## Service boundary (4.3.0)

`service.PackingService` wraps the engine with what a production caller needs:
authentication and capability authorization (`auth.py`), tenant scope and quotas,
payload/queue/concurrency limits and load shedding (`resilience.py`), deadlines,
cancellation and idempotency, protocol negotiation, a capacity-source circuit
breaker with staleness bounds, an audited and persisted freeze control,
hash-chained audit (`audit.py`), metrics/logs/trace context (`telemetry.py`), a
status/readiness surface and an operator explain view (`explain.py`). Policy lives
in a validated, versioned `PK_PACK_CONFIG/1` document with overlays and a crash-safe,
epoch-fenced activation/rollback store (`config.py`). See `INTERFACES.md`,
`CONFIGURATION.md`, `SECURITY.md`, `FAILURE_MODEL.md`.

## Verification

From the directory containing `inv68_resource_packing`:

```text
python -m unittest discover -s inv68_resource_packing/tests -v        # standalone tests
python -O -m unittest discover -s inv68_resource_packing/tests        # same, optimised
python -m inv68_resource_packing.tools.run_evidence --out evidence    # everything + exit gate
```

`run_evidence` runs tests (normal and `-O`), schema conformance, fuzz/property,
fault injection, race/soak, benchmarks + regression gate, emulated and real
integration, secret scan, source provenance, preflight, drills, SLO report,
governance check, wheel/sdist build, fresh-venv install check, release verification,
the item ledger, and finally `release_gate.py`. Exit: 0 GO, 2 CONDITIONAL_GO, 3 NO_GO.

**Current verdict: NO_GO.** The blockers are named in `evidence/EXIT_GATE.json`; they
are external artifacts (pk_core, MASTER.md, real adjacent components, a managed
signing key, other platforms, production telemetry) and named-human governance
(owners, ADR approval, license, reviews). See `AUDIT_REPORT.md` §4.3.0.

`pk_core` conformance tests still need the external framework (`PK_CORE_PATH`):

```text
python -m pk_core run INV-68 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-68 --out conformance/PK_GATE_RESULTS.json
```

## Service-level objectives

No memory overcommit (no budget); hosts within 10 % of the lower bound in ≥ 95 % of
batches; pack p99 < 100 ms for 1000 workloads. 4.3.0 *measures* all three in the lab
(`evidence/SLO.json`, `BENCHMARKS.md`) — 4.2.0 violated the latency SLO by ~3× — but
production compliance needs live SLIs and a support owner.

## Operations

Day 0/1/2, rollback, emergency disable, incident response: `RUNBOOK.md`,
`INCIDENT_RESPONSE.md`. Backup/restore: `BACKUP_RESTORE.md`. Alerts and dashboards:
`ops/alerts.json`, `dashboards/`, `TELEMETRY_POLICY.md`. Governance: `GOVERNANCE.md`.

## Audit note

The supplied 4.1.0 README claimed that `MASTER.md` was included, but the archive
contained no such file. Version 4.2.0 removes that inaccurate claim. The missing
master source is not reconstructed because its authoritative contents were not
present in the supplied repository.

4.3.0 still does not synthesize it: `provenance/master-source.json` records it as
UNVERIFIED and `tools/source_integrity.py` will enforce presence and digest once the
owner supplies the authoritative bytes (MC-01).

See `AUDIT_REPORT.md` for the audits, `MISSING_COMPONENTS.md` for the gap inventory
and its 4.3.0 status, `REQUIREMENTS_TRACEABILITY.md` for the control matrix, and
`source/INV68_v4.2.0_Missing_Component_Implementation_Checklists.executed.md` for the
item-by-item result of the governing checklist.
