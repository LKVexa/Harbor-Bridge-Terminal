# What v4.3.0 is and is not (INV71-X003, X002, X005, performance C061-C070)

## What exists

| Area | Where | Kind |
|---|---|---|
| guest-semantics model | `sandbox.py` | executable reference (4.2.0, one defect fixed in 4.3.0) |
| control plane semantics | `control/controller.py` + primitives | executable reference |
| Firecracker/jailer/cgroup/nftables launch plan | `control/runtime_plan.py` | **rendered, never executed** |
| teardown reconciliation | `runtime_plan.reconcile` | executable against *supplied* host inventories |
| node qualification | `control/qualify.py` | executable; this container qualifies as REJECT (no KVM) |
| evidence, traceability, gate | `tools/build_evidence.py`, `tools/production_gate.py` | executable; gate returns NO_GO |

## What does not exist (and why this is not a production sandbox)

- No node agent that executes the plan, and no Firecracker, jailer, kernel, rootfs or snapshot bytes. The approved manifest is `UNPINNED`.
- No run on a KVM host. Nothing here proves the microVM boundary isolates anything.
- No PKI, attestation, KMS/HSM, WORM sink, CMDB, paging system or CI runner. The reference mechanisms use HMAC keys supplied in-process.
- No accountable owners, approvals, drills or game days.
- `pk_core` is not supplied (INV71-X001). Its lock is UNPINNED and the probe reports NOT_RUN.

## Performance (C061-C070)

`tools/bench.py` measures only the Python control layer, with an environment fingerprint, p50/p95/p99/max/stdev, burst-create and teardown storms, per-session control-plane bytes, and residual bytes after churn. It gates against PROPOSED thresholds in `governance/perf_thresholds.json`. Every microVM metric (cold boot, restore, first exec, VMM RSS/PSS, density, block and network throughput, edge power and thermal) is reported `NOT_MEASURED` with a reason, so the gate verdict is `INCOMPLETE`, never `PASS`. The capacity model, overhead attribution, profiling of copies and hops, locality and zero-copy optimizations, and edge power envelopes all need the real runtime. They are BLOCKED rather than estimated.

Bench findings in this pass: lease-table growth that was never released, and expired idempotency and replay entries that were swept only at capacity. Both are fixed. Residual memory after churn is now bounded by peak live concurrency (dict capacity) and fixed-size logs, not by churn count.

## Historical `MASTER.md` (INV71-X002)

Search scope for this pass: the uploaded 4.2.0 archive (20 files) and the owner's GitHub Junkyard office on device "moneymoneymoney" (`_YARDOFFICE/work-orders`, where the sibling INV work orders say the same corpus was never supplied). It was not found. **Declared unavailable.** The authoritative replacement artifacts are `CHECKLIST.json` (100 controls), `contract.py`, `governance/requirements.json`, ADR-0001 v2 and the production remediation checklist (sha256 recorded in `evidence/release-manifest.json`). Nothing was reconstructed or labelled historical. `tests/test_governance.py::InventoryTest` fails if any document claims a bundled file that is absent.

## Licence (INV71-X005)

No licence has been chosen. Choosing one is the owner's legal decision, and this pass does not invent one. `LICENSE_STATUS.md` records that. `THIRD-PARTY-NOTICES.md` records that nothing third-party is vendored, and the gate fails while no LICENSE exists.
