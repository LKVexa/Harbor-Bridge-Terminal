# GAP-08 - OTA lifecycle/rollback

**Version:** 4.3.0  
**Group:** 04_Gap_Subsystems  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

GAP-08 owns the control logic for staged over-the-air rollout and rollback. It pins the previous version before mutation, admits only an exact-bundle verification result, progresses through non-decreasing rollout waves, gates every update step, defers offline nodes instead of misreporting them as updated, and automatically rolls back after a failed gate.

## v4.3.0 — missing-components build-out

v4.3.0 executes the *GAP-08 v4.2.0 Missing-Components Professional Checklist* (40 components, 1,286 checkboxes). The v4.2.0 state machine (`rollout.py`) is unchanged and remains the single home of rollout invariants; around it the package now contains a complete, standard-library-only reference control plane:

| Layer | Modules |
|---|---|
| Orchestration | `controller.py` (create / step / gate / retry_deferred / reverify / rollback / pause / resume / cancel / release_quarantine / reconcile / recover / status) |
| Durability & ownership | `store.py` (CAS + fence + backup/restore), `lease.py`, `conflicts.py` |
| Trust boundaries | `artifact.py` (GAP-07), `health.py` (GAP-09), `identity.py` (GAP-06), `transport.py` + `executor.py` (GAP-01), `audit_sink.py` |
| Policy | `topology.py`, `freeze.py`, `authz.py`, `windows.py`, `admission.py`, `dependencies.py`, `compat.py`, `config.py`, `secrets_boundary.py` |
| Node side | `installer.py` (A/B slots, boot-tries auto-revert, power-loss hooks), `distribution.py` |
| Contracts & ops | `schemas/` (14 JSON Schemas + compatibility matrix), `errors.py`, `telemetry.py`, `explain.py`, `docs/` |
| Assurance | `harness.py`, `tests/` (89 tests), `tools/benchmark.py`, `tools/soak.py`, `tools/release_evidence.py`, `tools/checklist_status.py`, `tools/ci.sh` |

**Checklist status:** see `docs/CHECKLIST_STATUS.md` — every checkbox has a status and evidence pointer. The package is **not production-ready**: owners are unnamed, reviews/drills have not happened, sibling services and hardware were only simulated, and the evidence bundle is unsigned.

## Responsibility

Own the OTA update lifecycle: stage a verified bundle across ordered waves, gate each wave on health evidence, and revert touched nodes to the pinned previous version as soon as a gate fails.

## Owns

- rollout waves and their ordering;
- per-wave health-gate orchestration;
- the immutable pinned rollback target;
- automatic and operator-triggered rollback orchestration;
- exact-bundle admission of an upstream verification result;
- deferred-node bookkeeping and gated catch-up;
- local rollout state snapshots and integrity checking;
- explicit quarantine state for rollback failures.

## Explicitly does not own

- building update bundles;
- signing keys or the signature-verification implementation;
- node health measurement itself;
- node drain/restart/install mechanics;
- runtime compatibility certification;
- the contents of the update bundle.

## Core interfaces

- `PK_ROLLOUT/1` — rollout progress/completion response;
- `PK_ROLLOUT_GATE/1` — health verdict for a rollout wave or deferred retry;
- `PK_ROLLBACK/1` — rollback result, including incomplete rollback and quarantine;
- `PK_ROLLOUT_STATE/1` — crash-recoverable state snapshot;
- `PK_ROLLOUT_AUDIT/1` — locally chained transition-integrity record;
- `PK_VERIFICATION/1` — upstream bundle-verification input when supplied by GAP-07.

## Safety invariants

1. No node is touched before a rollback target is pinned.
2. The rollback target cannot be repointed after pinning.
3. A bundle is admitted only when the verifier's subject is the exact rollout bundle.
4. A node can appear in only one declared wave.
5. Wave sizes cannot shrink as rollout progresses.
6. A failed gate closes the rollout and starts rollback immediately.
7. Offline nodes remain on the old version and keep the rollout in a deferred state.
8. Deferred nodes can only catch up through another explicit health gate.
9. Rollback failures are reported and quarantined; they are never counted as reverted.
10. Restored mutable state must pass both snapshot-integrity and audit-chain verification.

## Running tests

From this package directory (standard library only):

```text
tools/ci.sh                                   # everything: compile, suite (+ python -O), evidence, checklist
cd tests && python -m unittest discover -p 'test_*.py'
python tools/benchmark.py --sizes 100 1000     # fleet-scale numbers on this host
python tools/soak.py --cycles 200              # simulated-time soak
GAP08_FUZZ_ITERS=20000 python -m unittest tests/test_property_fuzz.py
```

When the wider `pk_core` framework is available:

```text
python tests/test_component.py
python -m pk_core run GAP-08 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-08 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

`tests/test_component.py` is intentionally skipped when `pk_core` is absent; the safety-critical state machine remains fully testable via `tests/test_rollout.py`.

## Day 0 / Day 1 / Day 2

- **Day 0 — bootstrap:** validate the contract, run the standalone safety suite, create the first sealed evidence baseline, and configure the persistent rollout-state backend supplied by the enclosing platform.
- **Day 1 — deployment:** pin the current version, verify the exact update bundle through GAP-07, run a canary, then progress through larger waves only after healthy gates.
- **Day 2 — operation:** persist every state transition, retry deferred nodes through their own gate, quarantine rollback failures, continuously verify observability and evidence pipelines, and rerun the conformance gate after implementation or contract changes.

## Important limitations

* Signatures use an HMAC `KeyRing` stand-in behind `sign_envelope`/`verify_envelope`; production must use per-trust-domain asymmetric keys (HSM/KMS).
* `FileStateStore`, `LeaseService` and `FileWormSink` are single-host *reference* implementations of the contracts GAP-05, the lease service and the WORM audit service must meet.
* Sibling services (GAP-01/06/07/09/15, topology) are exercised through executable doubles in `harness.py`/`transport.py`.
* See `docs/CHECKLIST_STATUS.md` → *Open items that block production*.
