# GAP-11 - Accelerator scheduling

**Version:** 4.2.0  
**Group:** 04_Gap_Subsystems  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

> This package is a hardened reference component and contract, not a complete production accelerator control plane. Production gaps are explicitly tracked in `MISSING_COMPONENTS.md`.

## Responsibility

GAP-11 owns accelerator allocation and release for GPU, NPU, FPGA, or other explicitly typed accelerator inventory. It assigns whole devices or hardware-declared partitions, refuses oversubscription, preserves a physical-device tenant security epoch, and requires a completed scrub before a physical accelerator crosses tenant boundaries.

## v4.2.0 hardening model

The previous v4.1.0 implementation represented every physical device with one `holder` tuple. That was insufficient for declared partition scheduling and allowed the whole-device capacity to stand in for a partition's capacity. v4.2.0 moves the allocation state machine into `allocator.py` and introduces:

- explicit lease IDs for unambiguous release;
- multiple non-overlapping partition leases for the same tenant;
- a physical-device security-tenant epoch that forbids cross-tenant co-residency;
- independent `PartitionSpec` memory/feature attestation;
- whole-device versus partition conflict enforcement;
- failed-scrub quarantine and held-device scrub refusal;
- stable structured error codes;
- request and inventory validation;
- pool-level locking for atomic allocation/release/scrub transitions;
- accelerator kind matching (`gpu`, `npu`, `fpga`, or another declared kind);
- secure-default inventory output that omits tenant identity unless explicitly requested.

## Owns

- Accelerator inventory representation and declared partition topology
- Exclusive allocation and lease release
- Physical-device tenant isolation between scrubs
- Scrub/quarantine state used as an allocation gate
- Capability matching for kind, generation, memory, features, and partitions
- Allocation decision state and structured refusal reasons

## Explicitly does not own

- Device drivers or firmware
- Hardware probing itself (GAP-02 supplies discovered capability)
- Power/thermal ceilings (GAP-10 supplies those constraints)
- Workload placement policy outside accelerator eligibility
- Model, kernel, bitstream, or inference execution
- Durable distributed state, HA leader election, or external API transport (still missing; see `MISSING_COMPONENTS.md`)

## Core interfaces

- `inventory` — `PK_ACCELERATOR_INVENTORY/1`
- `allocate` — `PK_ACCELERATOR_ALLOCATION/1`
- `release` — `PK_ACCELERATOR_RELEASE/1`
- `scrub` — `PK_SCRUB/1`

The Python reference API is `AcceleratorPool`. When more than one partition lease exists on a device, callers must release by `lease_id`; device-only release fails closed as ambiguous.

## Partition safety

A partition may only claim positive memory capacity when its `PartitionSpec.memory_gb` is known. Legacy string-only partition names remain accepted for compatibility, but they can satisfy only a zero-memory request because their capacity is unattested. Distinct partitions can be leased concurrently only inside the same physical-device tenant security epoch.

## Scrub state

A successful scrub is permitted only when no active leases remain. Successful scrub clears the physical tenant epoch and quarantine state. A failed scrub quarantines the physical device, refusing allocation even to the previous tenant until a later scrub succeeds.

## Validation

Standalone allocator tests require only the Python standard library:

```text
python gap11_accelerator_scheduling/tests/test_allocator.py
python -O gap11_accelerator_scheduling/tests/test_allocator.py
```

The full 100-item conformance test additionally requires the sibling `pk_core` package:

```text
python gap11_accelerator_scheduling/tests/test_component.py
```

`PK_CORE_PATH` may point to the directory containing `pk_core` when it is not adjacent to this package.

## Day 0 / Day 1 / Day 2

- **Day 0:** validate immutable inventory declarations, run the standalone allocator suite, then run the `pk_core` conformance path when `pk_core` is present.
- **Day 1:** integrate the real hardware-discovery, identity/attestation, thermal-policy, observability, and durable-state adapters before rollout. A reference-only in-memory pool is not a production deployment target.
- **Day 2:** verify lease/scrub/quarantine evidence, watch allocation refusal reasons and saturation, and re-run the gate after contract or allocator changes.

## Audit artifacts

- `AUDIT_REPORT.md` — defects found, fixes applied, hardening decisions, and validation results.
- `MISSING_COMPONENTS.md` — prioritized components still required for a complete production subsystem.
- `MANIFEST.sha256` — package file hashes generated for this audited build.

## Source-series note

The prior README stated that `MASTER.md` was bundled. It is **not present in the supplied archive**. v4.2.0 removes that false claim and tracks the missing source-series/master-workflow artifact in `MISSING_COMPONENTS.md`.


---

## v4.3.0 — control-plane overlay (component checklist applied)

v4.3.0 executes the 50-component / 1,000-check *Professional-Grade Missing-Components Checklist* against this package. It is **additive**: `allocator.py`, `component.py`, `contract.py`, `__init__.py`, `VERSION`, `CHECKLIST.json` and `tests/` are byte-identical to v4.2.0 (see `release/MANIFEST_v4.2.0.sha256`). The new code lives in `gap11_control/` (stdlib only, zero third-party dependencies) and reuses the audited allocator as its placement kernel.

| Layer | Module |
|---|---|
| Durable WAL store, multi-key CAS, storage-side fencing | `gap11_control/store.py` |
| Leader election (epoch = fencing token) | `gap11_control/election.py` |
| Controller: TTL/heartbeat/reconcile, idempotency, lifecycle hooks, gang allocation, scrub, drain/freeze/quarantine, hot-plug, usage | `gap11_control/controller.py` |
| Inventory normalisation, partition profiles, scrub executor, thermal, RAS (simulated providers) | `gap11_control/hardware.py` |
| Authn (HMAC workload identity, nonce window, key rotation), deny-by-default authz, attestation binding, secret refs, redaction | `gap11_control/security.py` |
| Versioned wire schemas + limits + error envelope | `gap11_control/wire.py`, `gap11_control/schemas/` |
| Request pipeline + loopback HTTP binding | `gap11_control/service.py` |
| Quotas, fair queue, constraint engine, topology, fragmentation, preemption | `gap11_control/scheduler.py` |
| Audit ledger, metrics, logs/traces, health, alerts | `gap11_control/observability.py` |
| Layered config with provenance and rollback | `gap11_control/config.py` |

**Run everything:** `sh ci.sh` (or `python3 -B tools/run_checklist.py`). This executes 111 tests (0 failures, 0 errors, 3 skipped — the three v4.2.0 `pk_core` conformance tests) and recomputes every checklist status from the results.

**Result:** 575 evidenced · 231 partial · 112 blocked · 82 open · 0 failed, of 1,000 component checks. **Production verdict: NO_GO** — 0/10 exit gates met. The per-item status with the reason for each mark is in `GAP11_v4.3.0_CHECKLIST_STATUS.md`; the machine-readable bundle is `evidence/EXIT_BUNDLE.json`.

What stops GO is not code that could be written here: no accelerator hardware, no PKI/attestation service, no KMS, no multi-node environment, no adjacent GAP services, no signing keys, and — above all — no named owner, approver or reviewer. The bundle is computed from those facts; `ExitGateFalsifierTests` proves it turns GO when (synthetic) owners, approvals and gates exist, and NO_GO when any single one is removed.
