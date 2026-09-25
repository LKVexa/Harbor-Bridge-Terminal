# ADR-0001 — Resource packing: multi-dimensional FFD with headroom, CPU-only overcommit

**Status:** PROPOSED
**Date proposed:** 2026-09-23
**Deciders (required):** accountable_owner, security_owner, service_owner (ops/owners.json)
**Approvers:** none — no named approver exists yet (MC-03). This ADR cannot become ACCEPTED until one signs below.
**Supersedes:** nothing (first ADR). **Superseded by:** —
**Checklist:** INV-68-C010; MC-04.

## Context

INV-68 decides how many workloads fit on how many hosts inside the Post-Kubernetes
series. Upstream INV-67 translates Kubernetes-style requests and SCH-01 asks where a
batch fits; downstream GAP-10 layers power limits; INV-72 owns accelerators. The
series targets Wasm-dense ("hyper-density") execution tiers where many small
workloads share hosts and memory exhaustion is the dominant failure (OOM kills a
co-tenant; CPU contention only slows it).

Constraints: deterministic output (same inputs → same placement, auditable);
p99 < 100 ms for 1000 workloads; zero memory overcommit; a reserve for failover;
explainable refusals; stdlib-only core so the engine embeds in constrained runtimes.

## Decision

1. **Algorithm:** multi-dimensional *first-fit decreasing*, ordering by *dominant
   share* of effective capacity (ties by name), first fit over open hosts. Hosts that
   cannot fit the smallest remaining request in some dimension are closed (4.3.0);
   this never changes a decision (differential test vs the 4.2.0 loop).
2. **Headroom:** a single reserve fraction `h ∈ [0,1)` applied to every dimension on
   every host; default 0.10. Callers may ask for *more* headroom, never less.
3. **Overcommit:** CPU ratio configurable in `[1, 4]` (default 1.5) because CPU
   contention degrades gracefully; **memory ratio fixed at 1.0** and not configurable.
4. **Unplaceable work is reported**, never forced: `request_exceeds_effective_host_capacity`.
5. **Policy lives in `PK_PACK_CONFIG/1`**, activated transactionally and audited.
6. **Homogeneous hosts per request.** Heterogeneous fleets are packed per host class.

## Alternatives considered

| Option | Why not (now) |
|---|---|
| Best-fit decreasing | Marginally denser on some mixes; O(n·h) search per item with no early exit; tie-breaking harder to explain. Revisit with benchmark evidence (MC-22 corpus). |
| Vector bin packing via ILP/CP-SAT | Optimal but non-deterministic runtime, heavy dependency, violates p99 bound at 1000 workloads. |
| Kubernetes scheduler scoring (LeastAllocated/MostAllocated) | Online, one pod at a time; not a batch packer; no lower-bound reporting. |
| Memory overcommit with eviction | Converts density into OOM kills of co-tenants; rejected by the no-overcommit SLO. |
| Per-dimension headroom | More knobs, same failure protection; deferred until a site needs it. |

## Consequences

* (+) Deterministic, explainable, stdlib-only, measured 5.6 ms p50 / 7.7 ms p99 for 1000
  workloads (evidence/PERF.json); within 10% of the lower bound in 99.5% of 200 batches.
* (−) FFD is a heuristic: worst case up to ~11/9·OPT + 6/9 bins in 1-D; multi-dimensional
  gaps can be larger. Efficiency is monitored (alert INV68-A08) not guaranteed.
* (−) Single host class per call pushes heterogeneity to the caller.
* (−) CPU overcommit can raise tail latency of co-located CPU-bound work; GAP-10 and
  site policy must account for it.
* Risk: stale capacity data — mitigated by staleness bound + breaker (MC-18/19).

## Supersession rule

A new ADR that changes any numbered decision above must reference this ADR, be
approved by the same deciders, and ship with a benchmark comparison against
`bench/PERF_BASELINE.json`.

## Sign-off

| Role | Name | Date | Decision |
|---|---|---|---|
| accountable_owner | | | |
| security_owner | | | |
| service_owner | | | |
