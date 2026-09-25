# GAP-14 - Data-gravity manager

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 04_Gap_Subsystems  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`  
**Master prompts:** `MASTER.md`  
**Residual gaps:** `MISSING_COMPONENTS.md`  
**Certification status:** `CERTIFICATION_MANIFEST.json` (all 1,831 items of the v4.2.0 missing-components checklist, with evidence)  
**Design / operations / runbooks:** `docs/`

The data-gravity manager decides whether computation moves to data or data moves to computation. Residency/capability constraints are applied before cost comparison; if a legal candidate cannot be honestly costed, the engine fails closed instead of inventing a route cost.

## v4.3.0: estate-integrated decision service

v4.3.0 wraps the unchanged v4.2.0 engine in a production decision path (`service.DecisionService`):

- **Signed, fresh, request-bound inputs** from GAP-13 (residency verdicts), GAP-03 (topology/cost snapshot), GAP-05 (convergence proof) and SCH-01 (placement snapshot); missing, stale, future-dated, tampered, rolled-back or mis-bound inputs fail closed with stable reason codes (`errors.py`).
- **Identity:** capability tokens (scope + tenant + audience + bounded lifetime); tenant/workload identity carried through request, provenance, audit and handoff; cross-tenant requests refused.
- **Evidence:** signed decision envelope with full provenance (`PK_GRAVITY_DECISION/2`), hash-chained MAC'd audit log (no audit, no decision), explain view, independent `verify-audit` CLI.
- **Operability:** deadlines/cancellation, idempotent-only retries, circuit breakers, admission control with per-tenant fairness, readiness/drain, bounded-cardinality metrics, redacted structured logs, W3C trace context, signed transactional config with rollback.
- **PLN-06 handoff:** signed, idempotent, expiring; only production data-movement decisions can execute.
- **Planner (P2):** partial/shard movement, repeated-job amortisation, replication as a third option, DAG placement, carbon/power/thermal, transfer time with congestion, storage/IOPS with minimum charges and rounding, architecture/runtime compatibility, quota; calibration/drift detection, shadow and canary models, non-executable what-if simulation. Without a workload profile the planner is exactly the v4.2.0 engine (property-tested).

```text
python -m unittest discover -s gap14_data_gravity_manager/tests -t .      # full suite (stdlib only)
python gap14_data_gravity_manager/tools/bench.py --n 5000 --threads 1      # latency benchmark
python gap14_data_gravity_manager/tools/release_evidence.py                # SBOM, manifest, test report
python -m gap14_data_gravity_manager handshake | knobs | reason-codes | verify-audit | validate
```

What v4.3.0 does **not** prove: live-estate behaviour (fixtures only), a certified `pk_core` run, Windows/3.12/3.13 runs, signed release artifacts, named owners and human exercises. These are tracked as `external` in `CERTIFICATION_MANIFEST.json`; production certification remains **NO-GO** until they close.

## Responsibility

Own the move-compute-or-move-data decision: cost both directions against size, locality and egress, eliminate options residency forbids, and recommend the cheaper legal option or none at all.

## Owns

- Dataset location, size, classification, and convergence facts used by the decision
- Cost model for moving data versus moving compute
- Residency-legal option filtering
- The gravity recommendation, stable reason code, eliminated options, and cost breakdown
- Refusal when no legal option exists or a legal candidate cannot be honestly costed

## Explicitly does not own

- Executing the move
- Residency policy authorship
- Transport
- Placement execution
- Storage engines

## Interfaces

- `cost` - `PK_MOVE_COST/1` - per-direction cost breakdown (`schemas/PK_MOVE_COST-1.schema.json`)
- `datasets` - `PK_DATASET/1` - dataset location, size, classification, convergence (`schemas/PK_DATASET-1.schema.json`)
- `recommend` - `PK_GRAVITY_RECOMMENDATION/1` - move-data, move-compute, or none (`schemas/PK_GRAVITY_RECOMMENDATION-1.schema.json`)

The v4.2.0 response preserves the existing `direction`, `to`, `cost`, `options`, and `eliminated` fields and adds `cost_breakdown`, `reason_code`, and structured `elimination_details`.

## Hardening behavior

- Cross-site locality multipliers are explicit. A missing route model raises `CostModelError`; it no longer silently defaults to `1.0`.
- Dataset and cost inputs reject booleans, negative values, NaN, infinity, empty identifiers, and malformed route keys.
- Configuration is copied and frozen at manager construction so caller mutation cannot change an in-flight policy/cost snapshot.
- Exact cost ties prefer moving compute, keeping data resident.
- A co-located dataset whose current site is not legal for its classification is refused rather than reported as a healthy no-op.
- Production decision logic lives in `engine.py` and has no `pk_core` dependency.

## Service-level objectives

- **legality** - zero recommendations violating residency (error budget: no budget)
- **completeness** - every successful recommendation carries a cost breakdown (error budget: no budget)
- **decision latency** - p99 recommendation under 50ms (error budget: 1% may exceed; estate benchmark still required)

## Running it

From the folder containing `gap14_data_gravity_manager`:

```text
python -m unittest discover -s gap14_data_gravity_manager/tests -t .
```

`test_engine.py` is standalone. `test_component.py` always runs package-integrity checks; the conformance tests additionally require `pk_core` (set `PK_CORE_PATH` when it lives elsewhere).

When the full estate is available:

```text
python -m pk_core list
python -m pk_core run GAP-14 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-14 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

## Day-0 / day-1 / day-2

- **Day 0:** validate configuration, run standalone tests, run `pk_core run GAP-14`, and archive the emitted evidence ledger baseline.
- **Day 1:** run `pk_core gate GAP-14`; `NO_GO` blocks rollout and any conditional acceptance must be explicitly recorded.
- **Day 2:** re-run the gate on every contract/configuration/implementation change and verify the evidence chain against the previous sealed head.

Rollback is the previous known-good immutable artifact/configuration pair and evidence head. Emergency disable remains an estate-level registry/rollout operation; this component does not execute movement itself.
