# GAP-04 v4.2.0 Audit Report

Audit date: 2026-09-22  
Input version: 4.1.0  
Output version: 4.2.0

## Executive result

The 4.1.0 package had a compact and understandable reference state machine, but one advertised security fix was ineffective and several lifecycle paths could overstate the safety of the implementation. Version 4.2.0 corrects those defects, adds dependency-free tests and typed interface schemas, and explicitly separates implemented behavior from still-missing production subsystems.

## Defects fixed

1. **Backdated renewal guard was dead code.** `renew()` assigned `granted_at = now` before testing `now < granted_at`, making the comparison impossible to satisfy. The assignment now occurs only after validation.
2. **Renewal could bypass reconciliation.** A reachable control plane could renew/clear partition state while offline decisions remained pending. Renewal now refuses an active/unreconciled partition; `reconnect()` performs reconciliation before renewal.
3. **Offline decisions were accepted while connected.** `decide()` now requires an active partition and raises `NotPartitioned` otherwise.
4. **Policy staleness was observed but not enforced.** Decisions now fail closed with `PolicyStale` after `max_policy_staleness_ticks`.
5. **The decision journal was unbounded.** `max_decisions` provides an explicit memory ceiling and `DecisionJournalFull` failure mode.
6. **Mutable time could rewind across lifecycle operations.** Partition, decision, reconcile, policy-cache refresh, and renewal operations now reject state-changing timestamps older than the last state-changing event.
7. **Backdated reconnect could clear valid evidence.** `reconcile()` now validates lifecycle time before clearing the journal.
8. **External callers could mutate the internal decision list.** `decisions` now returns a defensive deep copy.
9. **Core safety behavior depended on the conformance framework import path.** The state machine now lives in dependency-free `controller.py`; `pk_core` is loaded lazily only for contract/conformance operations.
10. **Core shared state had no synchronization.** An `RLock` now protects state-changing operations and state snapshots inside one process.
11. **Input/configuration validation was incomplete.** Site identifiers, ticks, lease duration, policy staleness limits, and journal capacity are validated at construction/use.
12. **Public interface names existed without local schemas.** Three JSON Schema 2020-12 documents are now included for lease, tier, and reconciliation representations.
13. **Decision explanations were incomplete.** Accepted decisions now carry sequence, partition epoch, lease bounds, policy age, tier, and reason.
14. **README asserted a `MASTER.md` payload that was not present in the archive.** The false claim was removed and the documentation now describes the actual delivered files.
15. **Conformance tests forced the interpretation that all 100 requirements must already pass.** The test now verifies that all 100 are assessed without using that as an independent production-readiness certification.

## Hardening added

- Fail-closed behavior for expired lease, stale policy, disallowed tier action, no active partition, journal exhaustion, unreachable control plane, and invalid lifecycle ordering.
- Reconcile-before-renew lifecycle.
- Bounded in-memory decision journal.
- Locking plus defensive state copies.
- Versioned public representations and local schemas.
- Dependency-free unit test suite, including optimized (`python -O`) execution.
- Integrity manifest for delivered files.

## Verification performed

- Python bytecode compilation for package and tests.
- Dependency-free unit suite under normal interpreter mode.
- Dependency-free unit suite under `python -O`.
- JSON parse validation for `CHECKLIST.json` and all schemas.
- Archive path safety inspection (no absolute paths or `..` traversal entries).
- Source scan for accidental bare `assert` in runtime modules.
- Source scan for `eval`, `exec`, shell invocation, network calls, or unsafe deserialization in runtime modules.

The `pk_core` conformance suite could not execute in this isolated archive because `pk_core` is not bundled/importable here; it remains available and skips cleanly when that dependency is absent.

## Release interpretation

Version 4.2.0 is a materially safer reference/controller package than 4.1.0, but it is **not a complete production disconnected-operation subsystem** by itself. The remaining components are tracked in `MISSING_COMPONENTS.md` and should be treated as release-gate work rather than documentation-only items.


---

## Addendum — 4.3.0 implementation pass (2026-09-22)

The 4.2.0 conclusion ("hardened reference state machine; not a complete control plane until the P0 items are implemented and verified") has been acted on. 4.3.0 implements every P0 component in code with tests, including real process-kill crash qualification; see `CHANGELOG.md` for defects found along the way. It is still **not** production-ready: the exit gate returns NO_GO pending named owners/approvals, real adjacent-layer integration, release CI, hardware-backed keys, and an independent security review (`docs/WAIVERS.md`). Evidence: `evidence/test_results.json`, `evidence/perf_baseline.json`, `evidence/CHECKLIST_STATUS.json`, `evidence/gate_decision.json`.
