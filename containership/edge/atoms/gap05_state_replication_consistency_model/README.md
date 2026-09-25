# GAP-05 - State replication/consistency model

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 04_Gap_Subsystems  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

The state replication and consistency model makes edge divergence explicit. Writes accepted on both sides of a partition are preserved: causally newer writes supersede older writes, genuinely concurrent writes remain unresolved, and bounded conflict overflow is retained in a deterministic quarantine instead of being silently dropped.

## Responsibility

Own replicated-state semantics across sites: converge identical write sets deterministically, represent causal ordering with version vectors, surface genuine concurrency for resolution, and record causal discards.

## Owns

- Causal/version-vector comparison semantics
- Per-key unresolved causal frontier
- Conflict detection and deterministic bounded active conflict sets
- Quarantine of overflow concurrent writes
- Explicit conflict resolution that dominates the full unresolved frontier
- In-memory reason records for duplicates, supersession, and resolution

## Explicitly does not own

- Replication transport between sites
- Durable storage engines/WALs
- Data-residency policy
- Replica-placement policy
- Conflict-resolution policy authorship
- Cryptographic node identity, attestation, or signing

## Core behavior in v4.2.0

- `Write` validates and canonicalizes version vectors at construction.
- `ReplicatedKey.apply()` rejects unknown replicas and key mismatches.
- Equal causal vectors with different content raise `VectorEquivocationError`.
- The unresolved frontier includes both active siblings and quarantine entries.
- If the frontier exceeds `max_siblings`, the active subset is chosen deterministically from the complete frontier; overflow remains live in quarantine.
- Resolution merges the vectors of active **and quarantined** writes, records them as resolved, then clears quarantine.
- Public state-machine operations are protected by an in-process re-entrant lock.
- The core state machine lives in `model.py` and can be imported/tested without `pk_core`.

## Interfaces

The contract names these logical interfaces; production serialization/schema files are still a missing component and are tracked in `MISSING_COMPONENTS.md`.

- `conflicts` - `PK_CONFLICT_SET/1`
- `merge` - `PK_MERGE_RESULT/1`
- `write` - `PK_REPLICATED_WRITE/1`

`conflict_set()` includes the active `siblings`, preserved `quarantined` overflow writes, `open`, and `total_unresolved`.

## Service-level objectives

- **Convergence:** identical write sets converge to identical active/quarantined state regardless of delivery order.
- **Write preservation:** no causal discard is silent; overflow remains unresolved until resolution.
- **Conflict detection:** causally concurrent writes remain represented as unresolved state.

## Running tests

The core tests require only the Python standard library:

```text
python gap05_state_replication_consistency_model/tests/test_model_logic.py
```

The integration/conformance tests additionally require `pk_core`:

```text
python gap05_state_replication_consistency_model/tests/test_component.py
```

If `pk_core` is installed elsewhere, set `PK_CORE_PATH` to the path that makes it importable.

## Operational notes

The current implementation is an in-memory reference state machine, not a complete production replication service. It does not persist its frontier, authenticate declared replicas, allocate trusted monotonic counters, enforce tenant/environment namespaces, transport writes, encrypt data, or export production telemetry. Those gaps are explicitly enumerated in `MISSING_COMPONENTS.md` rather than being treated as implicitly complete.

## Day-0 / day-1 / day-2 integration

- **Day 0:** run the standalone state-machine tests, then run the `pk_core` conformance suite where available.
- **Day 1:** verify the production adapter supplies authenticated replica identity, durable state, schemas, and telemetry before enabling cross-site replication.
- **Day 2:** continuously reconcile replicas, inspect conflict/quarantine pressure, verify audit continuity, and re-run fault/property tests after semantic changes.

Rollback should restore the last compatible durable snapshot/evidence head in the surrounding platform. This package itself does not yet implement durable rollback; that remains a production gap.

## Audit artifacts

- `AUDIT_REPORT.md` - v4.2.0 findings, fixes, verification, and residual risk
- `MISSING_COMPONENTS.md` - prioritized components still required for a production-grade subsystem
- `SHA256SUMS.txt` - hashes of packaged files (generated at release packaging time)

> The source archive's previous README referenced a `MASTER.md`, but that file was not present in the supplied package. v4.2.0 removes the false "carried verbatim" claim and records the missing master-prompt evidence in `MISSING_COMPONENTS.md`.


## v4.3.0 production layer

`production/` implements the 50 components enumerated in `MISSING_COMPONENTS.md` around
the unchanged causal core.  Start with `PRODUCTION.md` (per-component design record),
`RUNBOOKS.md`, and `evidence/CHECKLIST_EVIDENCE.md` (the professional checklist with a
mechanically assigned status on every item - no box is ticked, because no independent
reviewer exists for this build).

```text
pip install cryptography==46.0.7
sh gap05_state_replication_consistency_model/ci.sh           # all gates
python3 -B gap05_state_replication_consistency_model/evidence/run_evidence.py CHECKLIST.md
python3 -m gap05_state_replication_consistency_model.production.cli inspect DATA_DIR
```

Production use remains **NO-GO**: identity is a verification core without mTLS/SPIRE,
keys are not in a KMS, releases are unsigned, no owner/reviewer is assigned, and
`MASTER.md` is an unrecovered evidence gap (`EVIDENCE_GAPS.json`).
