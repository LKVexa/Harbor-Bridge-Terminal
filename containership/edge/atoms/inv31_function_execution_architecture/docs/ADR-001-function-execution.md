# ADR-001 — Function execution architecture for INV-31

Status: PROPOSED  
Owner: UNASSIGNED  
Deciders: UNASSIGNED  
Date proposed: 2026-09-22

## Context
INV-31 owns the warm/cold reuse decision for function instances serving HTTP/RPC
pure-compute functions represented as DAGs. The checklist names *Dandelion* as the
technology (C010, C031). No Dandelion artefact, version, or specification was
supplied, and what "Dandelion" denotes (runtime, protocol, library) is not stated
anywhere in the archive (item A03).

## Decision (proposed)
1. Reuse only on exact (tenant, code version) match within `max_age`; cold start is
   always the safe fallback (already implemented, 4.2.0).
2. Every invocation enters through an authenticated, capability-checked `Gateway`
   (4.3.0) with keys supplied by the parent platform; none are built in.
3. Configuration is a declarative, versioned document activated as a whole new pool
   generation, never partially.
4. INV-31 treats the DAG executor (Dandelion or other) as a PLN-04-side concern: it
   receives a (tenant, version) identity and never inspects function code.

## Consequences
* Correctness of the reuse rule does not depend on Dandelion; only C011/C031's DAG
  semantics do, and those stay BLOCKED until A03 is resolved.
* The Gateway serialises admission under one lock (simple, provably quota-safe);
  its measured cost is in `evidence/bench.json`.

## Open — requires a human decision
* Resolve and pin Dandelion (A03). * Approve or reject this ADR (C010).
