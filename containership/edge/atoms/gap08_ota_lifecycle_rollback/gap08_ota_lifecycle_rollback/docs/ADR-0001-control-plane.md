# ADR-0001 — GAP-08 control-plane architecture

* **Status:** Proposed (v4.3.0). Requires approval by the named architecture owner (see `OWNERS.md`, currently unassigned).
* **Date:** 2026-09-22
* **Supersedes:** implicit design of v4.0.0–v4.2.0 (local state machine only).

## Context

v4.2.0 made the rollout state machine strict but left the 40 missing components from its register outside the package. Production needs durable, fenced, authenticated, auditable orchestration without taking ownership of sibling subsystems (GAP-01/05/06/07/09/15, topology discovery).

## Decisions

| # | Decision | Rationale | Rejected alternatives |
|---|---|---|---|
| D1 | Keep `rollout.Rollout` as the only place rollout invariants live; the controller composes it. | Single, fuzzed source of truth for safety rules. | Re-implementing invariants inside the controller (drift risk). |
| D2 | **Storage consistency: linearizable CAS per rollout record** (expected revision + fence), write-ahead intents before any node side effect. | Exactly-one-winner semantics under races; crash recovery without guessing. | Last-writer-wins KV (lost updates); event-sourcing without CAS (needs consensus elsewhere). |
| D3 | **Controller ownership: leases with monotonic fencing tokens enforced downstream** (store and node supervisor). | Leases alone cannot stop a paused holder; fences can. | Leader election without fencing; per-node locks. |
| D4 | Two-phase rollback (intent → commands → outcome) and node-side rollback tombstones. | Found by the v4.3.0 race harness: side effects before CAS left the fleet diverged from the record. | Single-phase rollback. |
| D5 | Unknown command outcome is never success: install→deferred+reconcile, rollback→quarantine. | Honest state under partitions. | Timeouts treated as failures or successes. |
| D6 | External audit in a separate trust domain; full events sealed; forward progress blocked while unsealed events exist; rollback may buffer. | Detects privileged rewrite; recovery never waits for audit. | Local hash chain only (v4.2.0). |
| D7 | Health gates accept only signed GAP-09 evidence bound to rollout + cohort + gate class with freshness/coverage/anti-replay. | Removes caller-supplied booleans from the production path. | Trusting boolean verdicts. |
| D8 | Artifact identity = GAP-07 statement over subject **and** sha256 content; bytes re-hashed at distribution and install. | Closes logical-name-only binding. | Name/tag binding. |
| D9 | Fail-closed dependency table with per-op-class modes; overrides impossible for store/lease/identity/authz. | Predictable degraded behaviour. | Ad-hoc per-call handling. |
| D10 | Standard library only in the package; HMAC `KeyRing` as signature stand-in behind `sign_envelope/verify_envelope`. | Zero supply-chain surface for the reference; swap-in point for Ed25519/HSM. | Bundling crypto libraries in the reference. |
| D11 | Blast radius counts deferred + quarantined nodes as unavailable. | Conservative: an offline node is not a survivor. | Counting only the active wave. |

## Consequences

* The production GAP-05 backend must implement `StateStore` (CAS + fence floor + immutability guards) — the file store is the executable reference.
* Node supervisors (GAP-01) must implement dedup by `command_id`, fence floors, tombstones, deadlines and signed acks (`transport.SimNodeSupervisor` is the contract double).
* Migration: v4.2.0 `PK_ROLLOUT_STATE/1` snapshots are embedded unchanged as `core` inside `PK_CONTROLLER_STATE/1`; importing an existing v4.2.0 snapshot requires wrapping it with controller fields (no data transformation).
* Rollback of this ADR: the package still exposes `Rollout` unchanged; deployments can pin 4.2.0 behaviour by not using `controller.py`.
