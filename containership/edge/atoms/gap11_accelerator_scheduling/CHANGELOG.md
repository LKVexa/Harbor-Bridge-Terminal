# Changelog - GAP-11

## 4.3.0 - 2026-09-22 (control-plane overlay; v4.2.0 core byte-identical)

Applied the 50-component professional-grade missing-components checklist.

### Added
- `gap11_control/` stdlib-only control plane: durable WAL store with multi-key CAS and storage-side fencing; lease-based leader election; durable controller with TTL, heartbeats, deterministic reconciliation, tenant-scoped idempotency, lifecycle hooks, gang allocation, scrub state machine, operator drain/freeze/quarantine, hot-plug handling and usage accounting; simulated vendor inventory, partition profiles, scrub executor, thermal and RAS adapters; HMAC workload-identity authentication, deny-by-default policy, attestation binding, secret references and redaction; versioned closed request schemas and limits; loopback HTTP transport with bounded in-flight and deadlines; quotas, fair queue, constraint engine, fragmentation and preemption policy; audit ledger, metrics, logs/traces, health, alerts; layered configuration with rollback.
- 92 new tests (111 total with the v4.2.0 suites), golden fixtures, seeded fuzzing and property tests, barrier concurrency tests, crash-point fault matrix, benchmark with PROPOSED thresholds, exit-gate falsifier.
- Governance artifacts: threat model, ADR-001 (PROPOSED), ownership (UNASSIGNED), runbooks (unexercised), exception register (all PROPOSED), MASTER.md disposition, compatibility matrix, dashboards spec, SBOM, pyproject, ci.sh.
- `tools/run_checklist.py` derives all 1,010 statuses and the exit verdict from executed evidence.

### Defects found by this pass's own tests and fixed before delivery
- Concurrent benign requests inside one controller failed with spurious STALE_REVISION (a release racing an allocate on the same device key), leaking the lease to a client that did not retry — found by the soak test; mutations are now serialised per controller process (the store's CAS + fence still guards across controllers).
- Holding that lock across a scrub would stall every other device for the scrub's duration, so scrub was split into begin/execute/end; that split then let `reconcile()` quarantine a scrub that was still running (it cannot tell a live scrub from a crashed one) — found by the barrier test; in-flight scrubs are now tracked and only an orphaned SCRUBBING state is quarantined.
- The service logged the unscoped request id while the controller recorded the tenant-scoped one, breaking correlation — found by the trace-propagation test.
- The test harness acquired leadership inside an `assert`, so under `python -O` every controller test ran leaderless (36 failures) — the same scar the v4.2.0 audit fixed in `component.py`; replaced with a plain call, `registry.py`'s `assert` replaced with a raise, and ci.sh now runs the overlay suite under `-O` too.
- The residue scan caught `__pycache__` twice: once from an ad-hoc import during the build, and once from ci.sh's own compile stage (`python -m py_compile` writes `.pyc` even under `-B`). The compile stage now compiles in memory; ci.sh runs with `PYTHONDONTWRITEBYTECODE=1`.

### Not done (and why) — see GAP11_v4.3.0_CHECKLIST_STATUS.md
- Live hardware, mTLS/attestation service, KMS, replicated store, adjacent-GAP integration, signing, multi-platform install matrix: environments not available.
- Owner, approvals, reviews, runbook drills, threshold approval, MASTER.md: human decisions not given. Production verdict NO_GO.

## 4.2.0 - 2026-09-22

Audit, parse, fix, hardening, and version-bump pass.

### Correctness fixes

- Replaced the single physical-device `holder` model with explicit allocation leases, so multiple declared partitions can be accounted independently without permitting whole-device overlap.
- Added a physical-device tenant security epoch: distinct partitions may be used concurrently only by the same tenant until a successful scrub clears the epoch.
- Added `PartitionSpec` capability attestation. Partition allocations no longer inherit the whole device's memory capacity; unknown partition capacity cannot satisfy a positive memory guarantee.
- Added accelerator-kind matching so GPU/NPU/FPGA inventory can be distinguished instead of being treated as an undifferentiated device pool.
- Added `PK_ACCELERATOR_RELEASE/1` to the contract and made release unambiguous with 128-bit lease IDs.
- Device-only release now fails closed when multiple active partition leases exist instead of risking release of an arbitrary workload.
- Corrected the source-of-truth contract wording to match same-tenant reuse and cross-tenant scrub semantics.
- Corrected README claim that `MASTER.md` was bundled; the supplied archive contains no such file.

### Security and resilience hardening

- Added stable machine-readable error codes and safe details.
- Added validation for device IDs, generations, kinds, memory, features, partition declarations, duplicate devices, duplicate partitions, and impossible declared partition-memory totals.
- Added atomic pool-level locking around allocation, release, scrub, inventory, and allocation snapshots.
- Preserved failed-scrub quarantine; successful scrub is illegal while any lease remains active.
- Allocation marks a physical device dirty immediately and binds it to the requesting tenant's security epoch.
- Inventory omits `security_tenant` by default and exposes it only through an explicit `include_sensitive=True` request.
- Added explicit peer dependencies on GAP-06 device identity/attestation and GAP-09 unified observability.

### Test expansion

- Added `tests/test_allocator.py`, a stdlib-only 16-test suite that does not require `pk_core`.
- Added coverage for best-fit allocation, GPU/NPU/FPGA kind selection, cross-tenant scrub barriers, same-tenant reuse, multi-partition accounting, partition capacity attestation, legacy partition safety, quarantine, held-device scrub refusal, ambiguous release, invalid inventory, structured errors, typed inventory, and a concurrent same-partition race.
- The allocator suite passes under normal and optimized (`python -O`) execution.

### Production-readiness clarification

The in-memory reference allocator is now substantially safer, but it is not by itself a production accelerator control plane. Durable/distributed lease state, fencing, real device adapters, authenticated APIs, authorization, telemetry exporters, HA, benchmarks, fuzzing, and operations/governance artifacts remain open and are enumerated in `MISSING_COMPONENTS.md`.

# Changelog - GAP-11

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::AcceleratorPool.allocate: picked the smallest matching device before checking partition/scrub state, so one dirty or partition-less device caused a refusal even when another eligible device was free -> filter by declared partition and scrub eligibility first, raise only when no eligible device remains
- component.py::Accelerator/allocate: "dirty after release" and "quarantined after failed scrub" were the same flag, so the last_tenant check was dead code and the quarantine message was wrong -> new `quarantined` field; own-tenant residue may be reused, other tenants need a scrub, quarantined refuses everyone
- component.py::Accelerator.scrub: a held device could be "scrubbed" under its running tenant -> ScrubRequired while held
- component.py::AcceleratorPool.release: unknown/unallocated device silently ignored -> KeyError
- component.py::AcceleratorPool.allocate: empty tenant/workload and negative/non-int memory_gb accepted -> ValueError

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
