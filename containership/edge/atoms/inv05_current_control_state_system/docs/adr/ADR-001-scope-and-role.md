# ADR-001 — INV-05 scope: control-state model with etcd-equivalent semantics

* Status: **Proposed** — awaiting approval by the accountable owner (see `docs/GOVERNANCE.md`, EX-006)
* Date: 2026-09-22 · Applies to: 4.3.0 · Traceability: C001, C002, C010, MC-052-02

## Context
The checklist names etcd as the technology behind "desired-state persistence for Kubernetes". v4.2.0 shipped only an in-memory reference model.

## Decision
INV-05 owns the *semantics* (revisions, CAS transactions, watches, compaction refusal, leases) and implements them in a dependency-free engine (`store.py`) with a durable single-member path (`wal.py`) and a transport (`server.py`). Consensus, membership and multi-member replication are delegated to an approved external backend reached through `backend.BackendAdapter` (ADR-002). The engine's semantics are defined so that an etcd v3 adapter is a translation, not a redesign (one revision per txn, `create/mod/version/lease` compares, prefix ranges, compaction errors, leases).

## Consequences
+ All semantics are testable in CI without a cluster. − A single member is not highly available; production HA requires ADR-002's backend decision.
