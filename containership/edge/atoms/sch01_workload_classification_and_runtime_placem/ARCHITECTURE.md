# SCH-01 Architecture Note - 4.2.0

## Decision

Keep the scheduler decision engine dependency-independent and treat `pk_core` as a conformance adapter rather than a runtime dependency of classification and placement. Hard constraints are evaluated before deterministic scoring. When the model lacks enough metadata to prove a placement is safe, the engine fails closed.

## Data flow

1. A `Workload` enters with tenant, provenance, latency sensitivity, hardware requirements, and optional site affinity.
2. `classify()` derives the canonical trust class and minimum isolation tier from provenance.
3. `candidates()` validates that the supplied classification exactly matches the canonical classification, then applies hard constraints.
4. `score()` orders viable nodes by weakest sufficient tier, most free slots, and finally node name.
5. `place()` selects one candidate and atomically updates the supplied in-memory `NodeReport` under a process-local lock.
6. Execution-side admission, enforcement, and distributed lease reconciliation are delegated to adjacent planes and are not implemented in this archive.

## Hard-constraint precedence

The engine does not trade the following constraints for a better score: report freshness, thermal exclusion, free capacity, site affinity, hardware capabilities, minimum tier, or tenant isolation. Security/safety constraints therefore precede scoring. Data residency, cost policy, topology cost, and fair-share policy are not yet represented and cannot participate in precedence decisions.

## Trust boundary

`NodeReport` is a data structure, not an attestation verifier. Version 4.2.0 validates shape, supported tier names, clock sanity, and capacity values, but it cannot establish that a report came from an authenticated node or that its claims are cryptographically true. The contract names hardware discovery as the source of truth; cryptographic verification is a required missing integration.

## Concurrency model

A process-local re-entrant lock covers duplicate-lease detection, candidate selection, scoring, and mutation. This closes the in-process oversubscription race. It does not provide distributed consensus, fencing, or split-brain protection across multiple scheduler processes.

## Compatibility

The historical misspelled class name `WorkloadClassificationAndRuntimePlacemenComponent` remains as an alias. The corrected public class name is `WorkloadClassificationAndRuntimePlacementComponent`.
