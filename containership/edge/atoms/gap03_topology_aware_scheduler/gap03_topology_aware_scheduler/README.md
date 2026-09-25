# GAP-03 - Topology-aware scheduler

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 04_Gap_Subsystems  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 audit/control requirements in `CHECKLIST.json`

> `MASTER.md` is referenced by the historical package lineage but is **not present in this archive**. Version 4.2.0 no longer treats that absent file as bundled evidence; it is recorded in `MISSING_COMPONENTS.md`.

## v4.3.0 — control plane + checklist execution

v4.3.0 keeps the v4.2.0 runtime (`scheduler.py`) byte-compatible and adds `controlplane/`, a stdlib-only implementation
of the 46 missing components (MC-001…MC-046) from `docs/GAP03_v4.2.0_Missing_Components_Professional_Checklist.md`:
versioned wire schemas + canonical parser + generated bindings, Ed25519 identity/attestation/provenance, authenticated
topology mutation boundary, entitlement authority, hash-chained WAL stores (topology, ledger, journal, config, controls,
explain, audit), majority-lease fencing, a fenced saga commit protocol, SCH-01/GAP-02/GAP-14/PLN-05 adapters with
fixtures, degraded-mode matrix, freeze/quarantine controls, health endpoints, metrics/logs/traces/explain, alerts as
code, admission/breakers/retries, latency refinement, generation-keyed cache, multi-objective composition, capacity
model, benchmark gate, fault/fuzz harnesses, supply chain (manifest/SBOM/provenance/signing), canary controller,
backup/restore, waivers and the exit gate.

```bash
python -B -m unittest discover -s gap03_topology_aware_scheduler/tests -t .          # 264 tests (3 skipped: pk_core absent)
python -B -m gap03_topology_aware_scheduler.certification.run_checklist --ci          # executes all 1,380 checks -> evidence/
python -B -m gap03_topology_aware_scheduler.benchmarks.harness --gate                 # benchmark matrix vs PROPOSED thresholds
```

Result: see `evidence/CERTIFICATION_REPORT.md` and `MISSING_COMPONENTS.md`. The exit gate is **NO_GO** by design until
the blocked items (owners, real adjacent services, KMS, CI, exercised runbooks, approvals) exist.

The topology-aware scheduler supplies locality scoring, failure-domain spreading, and fair-share admission information without taking ownership of the final placement decision. Version 4.2.0 separates the stdlib-only runtime logic (`scheduler.py`) from the suite conformance adapter (`component.py`).

## Responsibility

Own topology cost and fair-share scoring for placement: rank candidate nodes by locality distance, provide a fairness verdict alongside scoring, and protect each tenant's reserved share from surplus demand.

## Owns

- Declared region/site/rack topology and deterministic distance classes
- Immutable topology snapshots and generation numbers for one scoring pass
- Locality scoring and deterministic tie-breaking
- Requested site-level anti-affinity spreading
- In-process fair-share reservation accounting
- Starvation and oversubscription detection
- Explainable fair-share verdicts and candidate-score records

## Explicitly does not own

- Hard constraint filtering
- Trust classification
- Capacity provisioning or targets
- Node lifecycle
- Data residency policy
- Final placement commit/selection
- Distributed consensus or durable scheduler state (v4.3.0: provided by `controlplane/`, reference lease implementation)

## Runtime API

- `Topology.place(..., replace=False)` — declares a node; conflicting rewrites fail closed unless replacement is explicit.
- `Topology.snapshot()` — immutable point-in-time topology plus generation.
- `Topology.cost(a, b)` — deterministic locality class.
- `rank(...)` — deterministic candidate ordering; `spread_from` makes unused site failure domains strictly preferred.
- `FairShare.verdict(...)` — non-mutating fair-share admission decision with reason and accounting detail.
- `FairShare.claim(...)` / `release(...)` — thread-safe in-process capacity accounting; `claim(..., expected_state_token=...)` can reject a stale score-to-commit transition.
- `score_candidates(...)` — candidate scores plus the required fair-share verdict/state token; does **not** mutate or commit placement.

## Fail-closed behavior added in 4.2.0

- Unknown topology nodes cannot be scored, including `cost(x, x)` for an unknown `x`.
- Topology identifiers must be non-empty canonical strings; region/site/rack labels cannot contain `/`, and control characters are rejected.
- Conflicting node re-parenting requires `replace=True`.
- Duplicate candidate IDs are rejected instead of being ranked twice.
- Anti-affinity spreading is strict across site failure domains when `spread_from` is supplied.
- Invalid, negative, Boolean, or over-capacity accounting is rejected.
- A reservation set whose total exceeds capacity is diagnosable but claims fail closed until corrected.
- Claims are serialized by an in-process re-entrant lock so concurrent threads cannot overcommit local capacity.
- Fair-share verdicts carry a deterministic state token so a later local claim can reject stale scoring state.
- Public-map corruption is revalidated at use time and fails closed instead of being silently trusted.

## Interfaces named by the contract

- `PK_TOPOLOGY/1` — region/site/rack topology
- `PK_LOCALITY_COST/1` — distance/locality score
- `PK_FAIR_SHARE/1` — reservations and fairness verdict

The names above are contract identifiers; this archive still lacks production wire/schema definitions for them. See `MISSING_COMPONENTS.md`.

## Service-level objectives declared by the contract

- **Share enforcement:** zero placements spending another tenant's reserved share (no error budget)
- **Cost determinism:** identical topology and candidates produce identical costs (no error budget)
- **Scoring latency:** p99 under 20 ms for 1,000 candidates (1% may exceed)

The SLOs are declared, not yet backed by a production benchmark/telemetry pipeline in this package.

## Test

Runtime tests require only the Python standard library:

```text
python gap03_topology_aware_scheduler/tests/test_scheduler_runtime.py
python -O gap03_topology_aware_scheduler/tests/test_scheduler_runtime.py
python gap03_topology_aware_scheduler/benchmarks/benchmark_rank.py
```

The benchmark is diagnostic only; its output is not a cross-platform production SLO certification.

Suite conformance tests additionally require `pk_core`:

```text
python gap03_topology_aware_scheduler/tests/test_component.py
# set PK_CORE_PATH if pk_core is elsewhere
```

For the full estate gate:

```text
python -m pk_core list
python -m pk_core run GAP-03 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-03 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

A passing local unit/conformance test is not, by itself, production certification for all 100 controls. Missing production components and evidence are tracked in `MISSING_COMPONENTS.md`. `MANIFEST.sha256` provides an unsigned integrity manifest for the rebuilt archive.

## Day-0 / day-1 / day-2

- **Day 0:** load/validate topology and reservation configuration; run runtime tests and the suite gate where `pk_core` is available; archive the evidence ledger.
- **Day 1:** stage/canary through the owning control plane; do not activate if external interface schemas, identity/authorization, durable state, or distributed coordination are required but unavailable.
- **Day 2:** re-run tests and gate on every contract/runtime change; monitor fairness denials, starvation, topology-generation churn, score latency, and integration health once telemetry components are added.

Rollback is the previous sealed artifact/evidence head in the surrounding suite. This package does not yet contain an independent deployment controller or durable rollback engine.
