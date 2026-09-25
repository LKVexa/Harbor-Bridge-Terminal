# INV-08 production overlay 1.0.0 — the 66 missing-component checklists applied

**Candidate:** `inv08_dynamic_infrastructure_model` v4.2.0 (hardened). Its 15 original files are **byte-identical**; `ci/run_all.py` re-checks them against the candidate's own `SHA256SUMS`.
**Workflow applied:** *INV-08 v4.2.0 Professional Missing-Component Implementation Checklists*: 66 components × 36 checks = 2,376 checks. A copy is kept in `docs/COMPONENT_CHECKLISTS.md`.
**Distribution version:** `4.3.0.dev1` (`../../pyproject.toml`). The package's own `__version__` stays 4.2.0.
**Verdict:** production exit gate **NO_GO**. This is correct, and it is expected.

## How to run

```text
python -B inv08_dynamic_infrastructure_model/production/ci/run_all.py          # everything; exit 3 = local PASS, gate NO_GO
python -B -m inv08_dynamic_infrastructure_model.production.status               # regenerate CHECK_STATUS.json (runs every listed test)
python -B -m inv08_dynamic_infrastructure_model.production.exitgate             # signed decision -> EXIT_GATE_DECISION.json
```

The code uses only the Python standard library (3.10+). There are 417 overlay tests, and they pass under both `-B` and `-O`. The candidate's own 11 tests still pass; its 2 `pk_core` tests are skipped because `pk_core` is not installed.

## Result

| | LOCALLY_VERIFIED | PARTIAL | BLOCKED |
|---|---|---|---|
| Engineering sub-parts (330) | 238 implemented | 82 | 10 |
| Checks, P0 (1,440) | 587 | 637 | 216 |
| Checks, P1 (864) | 375 | 362 | 127 |
| Checks, P2 (72) | 28 | 33 | 11 |
| **All 2,376 checks** | **990** | **1,032** | **354** |

The acceptance gates for all 66 components are **BLOCKED**. No check is marked COMPLETE, because the ledger has no such state. The checklist's own rules make completion impossible for the builder:

- check 01 needs a named accountable owner, and `ownership.json` has every role UNASSIGNED (25 blockers);
- check 35 needs an approver identity;
- check 36 needs an independent reviewer to reproduce the result from a clean environment.

The exit gate fails on three counts:

- **D1–D3:** 1,342 open P0/P1 checks, with no waivers.
- **D4:** ownership is not assigned.
- **D5:** the evidence is signed under a **NONPRODUCTION** HMAC root. `core.TrustRoot` refuses to hold a production key without a KMS binding.

**Falsifier:** `tests/test_gate.py::test_falsifier_gate_is_a_gate_not_a_wall` gives the gate synthetic all-verified inputs and a synthetic production verifier, and gets **GO**. Removing any single input turns it back to NO_GO. This shows the gate can pass when the evidence is there, and that it fails today because the evidence is missing.

## What is real, and what is a stand-in

It is real and tested locally: the lifecycle state machine with a journal and replay, versioned wire schemas with golden fixtures and negotiation, authn tokens with rotation and revocation, deny-by-default authz, idempotency/retry/backpressure, limits, quota/fair share, partition semantics, constraint precedence, the reconcile controller driving `model.Pool`, the file-backed CAS lease store with fencing, leader election, the WAL with snapshots, config staging and rollback, secret refs and redaction, bootstrap, health, circuit breaker and load shedding, quarantine/freeze/kill switch, fault injection, the hash-chained audit log with signed checkpoints, the threat model as data, artifact and policy verification, key-hierarchy bookkeeping, metrics/logs/traces/explain, the benchmark regression gate, rollout/canary, backup/restore/migration, waivers, the RTM, and the exit gate.

These are doubles, or are marked BLOCKED with the missing input named: every real provider and adjacent layer (INV-06/68/PLN-05/INV-32), replicated consensus, `pk_core` itself, the project licence, MASTER.md, TPM/TEE attestation, OS/hypervisor isolation, mTLS and at-rest encryption, KMS/HSM and asymmetric signing, paging routes, dashboard hosting, live environments, and every human role.

## Defects found in the candidate's `model.py` (reported, not fixed; the candidate is read-only)

1. **Idle-lease churn.** Leases on idle nodes are never renewed. A node the pool still needs is reclaimed when its lease expires and is replaced by a new id in the same tick. Against a real provider that means a delete plus a create every `lease_ttl`. Reproduced independently by three builders.
2. **Node-hours use the pre-tick size.** Added nodes are billed one interval late, and reclaimed nodes are billed for the interval in which they were removed. `elapsed_hours` is also not tied to the `now` delta.
3. **Not thread-safe (lost update).** A `set_busy` call that lands between the copy and the commit inside `tick()` is lost. This is shown deterministically in `test_govops.ConcurrencyTest`. The overlay provides a `LockedPool` wrapper.
4. **Restore loses the time watermark.** `snapshot()` exports `last_now`, but `_last_now` is `init=False`, so a restored pool accepts a `now` that goes backwards.
5. **Lowering `max_nodes` bricks the pool.** Busy nodes are never reclaimed, so every later `tick()` raises `PoolInvariantError`. There is no drain path.
6. **Surplus reclaim order is lexicographic.** Nodes are reclaimed in the order node-1, node-10, node-11, …, node-2, rather than by age.
7. **A stale busy flag keeps a lease forever.** There is no heartbeat or orphan concept in the model. `lifecycle.sweep` provides one, but it is not wired into the model.
8. **No supported API to remove or adopt a node.** Because of this, `controller.py` has to edit `pool.nodes` directly.

The overlay fixed one defect in its own shared code: `audit.read_entries` crashed on non-UTF-8 bytes. The seeded fuzzer in `test_secobs` found it, and it is now a regression test.

## Environment notes

- The wheel builds and installs cleanly in the cloud container (`inv08_dynamic_infrastructure_model-4.3.0.dev1-py3-none-any.whl`, all data files present). This needed `SETUPTOOLS_USE_DISTUTILS=stdlib`, which works around a Debian setuptools `install_layout` quirk. Building the wheel exposed a real packaging defect, since fixed: `fixtures/golden` and `fixtures/dashboards` were missing from package-data.
- Every threshold, SLO and RTO/RPO value is **PROPOSED**, with the approver UNASSIGNED.

## Yard

The chop shop ran in degraded mode. On *moneymoneymoney*, the connected `C:\…\OneDrive\Desktop\GitHub Junkyard` copy has no `_YARDOFFICE`, so there was no ledger recall, map query or `log-job`, and the device has no shell. No donor code was copied: everything is **build-new** (searched: lease, autoscale, capacity, infrastructure, terraform). `THIRD-PARTY-NOTICES.md` records that there are no third-party parts.
