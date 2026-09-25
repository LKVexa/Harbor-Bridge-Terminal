# ADR-0001 — Accelerator requirement matching for hardware-accelerated AI

* **Status:** PROPOSED (approver: pk-architecture-board — UNASSIGNED)
* **Date:** 2026-09-23 · **Component:** INV-72 · **Technologies:** GPU passthrough, local inference
* **Function:** Hardware-accelerated AI (C010)

## Context

Jobs (GAP-11 scheduling, INV-69 model tools) need accelerators. Wrong placement fails expensively
mid-run (too little memory), leaks across tenants (shared slices) or runs slowly (split interconnect).
Devices are exposed to workloads by GPU passthrough (VFIO whole-device) or partitioning (MIG/SR-IOV
slices); inference runs locally on the node. INV-72 sits between discovery (GAP-02) and scheduling.

## Decision

1. INV-72 is a **pure decision component** plus a small reservation store. It owns the requirement
   schema and the fit/isolation decision; it does not touch devices, drivers or hypervisors.
2. **Strict fit**: exact class, minimum memory, exact count, one interconnect group when asked.
3. **Isolation by explicit opt-in**: partitions only for `isolation="shared"`; whole devices are
   exclusive per reservation. Far-edge profiles refuse partition sharing outright.
4. **Discovered inventory is the only source of truth**, authenticated per source.
5. **Fail closed** on any uncertainty: stale inventory (beyond offline grace), unavailable identity,
   stale fence, invalid config.
6. Runtime is **CPython standard library only**; pk_core is used for conformance at gate time only.

## Alternatives considered

* *Let the scheduler (GAP-11) match directly* — rejected: duplicates isolation logic in every
  scheduler and loses one auditable decision point.
* *Trust node labels* — rejected: labels are advertised, not observed (contract source-of-truth).
* *Best-fit memory packing* — deferred: first-fit in deterministic order is explainable; packing is
  INV-68's concern and can feed `allowed_nodes`.

## Consequences

* Passthrough vs partition technology choice and driver/runtime versions remain host decisions
  (W-003); this ADR constrains only how INV-72 treats them.
* Partition memory is not subdivided (TD-2): a shared slice is exclusive to one tenant but not
  apportioned among that tenant's jobs.
