# SCH-01 - Workload Classification and Runtime Placement Engine

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 03_Multi_Runtime_Scheduler  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

SCH-01 classifies workloads by provenance, latency class, and hardware need, then chooses a node and isolation tier without trading away hard constraints. The dependency-independent decision logic is in `engine.py`; `component.py` is the optional `pk_core` conformance adapter.

> Repository integrity note: earlier revisions claimed that `MASTER.md` was carried in this archive. It is not present in the supplied source and was not reconstructed as if it were original evidence. See `MISSING_COMPONENTS.md`.

## Responsibility

Own workload classification and runtime placement: derive a trust class, latency class, and hardware requirement for every workload, and bind it to a node whose reported tiers and capacity satisfy that class, or refuse placement with a machine-readable reason.

## Owns

- Canonical workload classification from provenance
- Candidate filtering against hard constraints
- Weakest-sufficient-tier selection
- Deterministic scoring and tie-breaking
- Process-local atomic placement mutation
- Placement lease issuance metadata
- Fail-closed refusal and aggregate rejection diagnostics

## Explicitly does not own

- Isolation enforcement inside the selected execution tier
- Cryptographic node/workload attestation
- Distributed lease ownership or execution-side lease reclamation
- Node provisioning or replica-count decisions
- Data-residency policy, topology service, or accelerator allocation
- Cross-decision quota/fair-share accounting

## Safety invariants in 4.2.0

- Unknown provenance fails closed with `UNKNOWN_PROVENANCE`.
- Caller-supplied classification cannot override the canonical class derived from the workload.
- Future-dated and stale node reports are excluded.
- Unknown tiers and malformed workload/node data are rejected at construction or call boundaries.
- Cross-tenant co-location fails closed because the current occupancy model does not carry enough tier/trust metadata to prove safe sharing.
- Duplicate workload leases are refused.
- Duplicate node identities in one placement decision are rejected.
- Placement selection and mutable slot/occupant updates are protected by a process-local lock to prevent in-process oversubscription.
- Refusal details expose aggregate reason counts rather than per-node placement state.

## Interfaces

- `classify(workload)` -> `PK_WORKLOAD_CLASS/1`
- `candidates(workload, klass, nodes, now)` -> viable `NodeReport` values
- `rejection_reasons(workload, klass, node, now)` -> stable hard-constraint reason codes
- `place(workload, nodes, now=0, lease_ticks=60)` -> `PK_PLACEMENT/1`
- `Unplaceable.as_dict()` -> `PK_SCHEDULER_ERROR/1`
- `contract.build()` -> external `pk_core` contract adapter (requires `pk_core`)

See `SCHEMAS.md` for the concrete fields currently emitted.

## Running the dependency-independent tests

From the directory containing this package:

```text
python sch01_workload_classification_and_runtime_placem/tests/test_engine.py -v
python -m unittest discover -s sch01_workload_classification_and_runtime_placem/tests -p "test_*.py" -v
```

The engine imports and its standalone tests do **not** require `pk_core`.

## Running the pk_core conformance adapter

If the external `pk_core` framework is installed or available through `PK_CORE_PATH`:

```text
python sch01_workload_classification_and_runtime_placem/tests/test_component.py -v
python -m pk_core list
python -m pk_core run SCH-01 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate SCH-01 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

A skipped `pk_core` test is not certification. This archive does not bundle `pk_core`, `INV-33`, or `GAP-03`.

## Service-level objectives declared by the contract

- **Placement soundness:** zero placements onto a node lacking the required tier.
- **Placement latency:** p99 decision under 100 ms for 1,000 candidate nodes.
- **Determinism:** identical decision inputs produce an identical placement.

The repository still lacks an approved benchmark/regression gate for the p99 objective; that remains listed in `MISSING_COMPONENTS.md`.

## Audit outputs

- `AUDIT_REPORT.md` - what was inspected, changed, and verified in 4.2.0.
- `MISSING_COMPONENTS.md` - complete post-update gap inventory for this standalone archive.
- `CHECKLIST.json` - the original 100 requirement statements.


## 4.3.0 status

The governed service path is `scheduler.Scheduler`. Run `sh ci/ci.sh` for the full evidence pipeline. The production exit gate is **NO_GO** until owners, approvals and the external elements exist. See `EXECUTION_REPORT_4.3.0.md`.
