# INV-37 — Bulk data plane

**Version:** 4.3.0  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements in `CHECKLIST.json`

INV-37 provides a stdlib-only bulk data plane: chunked integrity (manifests, per-chunk and whole-object verification), a **shared-memory zero-copy receive path** (intra-host, cross-process), durable crash-consistent checkpoints with fencing, capability-token authentication/authorization, per-tenant fair admission, a full transfer lifecycle, declarative configuration with atomic activation and rollback, telemetry/explainability, conformance fixtures, benchmarks and a self-contained production gate. It does **not** implement a network transport, host↔guest (VM) shared memory, encryption, mTLS/attestation or a storage backend beyond the local checkpoint directory.

**Production posture: NO_GO.** v4.3.0 executes the v4.2.0 remediation checklist: of the 85 incomplete requirements, 48 are now `IMPLEMENTED_PENDING_REVIEW`, 35 `PARTIAL`, 2 `MISSING`; none is marked PASS because the checklist requires review by an accountable role that has not yet been assigned. See `REMEDIATION_STATUS.json`, `MISSING_COMPONENTS.md` and `artifacts/certification/PRODUCTION_GATE.md`.

## Production responsibility

Own chunked bulk transfer integrity: content chunking, per-chunk digests, an object digest over the ordered chunk list, receiver-side end-to-end verification, resumption metadata, and bounded transfer admission.

### Owns

- Content chunking and manifest construction/validation
- Per-chunk digest and geometry verification
- Whole-object verification against the manifest
- In-memory resumable receiver state and resume tokens
- Fail-closed object/chunk/chunk-count limits
- Process-local bounded concurrent-transfer admission
- Stable machine-readable error codes

- Intra-host shared-memory zero-copy transport (ADR-0001 phase 1)
- Durable local checkpoints, fencing, quarantine
- Capability-token authn/authz, audit chain, tenant quotas and fairness
- Configuration, telemetry, decision records, production gate

### Explicitly does not own

- Control messages or placement decisions
- Remote storage backends
- Encryption and external key custody (fail closed when required)
- Network/RDMA/vsock/virtio host↔guest transports
- Cross-node state replication
- Telemetry backends, dashboard/alert deployment

## Interfaces

- `PK_BULK_MANIFEST/1` — ordered chunk digest list and object digest
- `PK_BULK_CHUNK/1` — chunk envelope schema (transport binding remains external)
- `PK_BULK_RESUME/1` — verified progress/resume metadata

JSON Schemas are under `schemas/`.

## Service API (4.3.0)

```python
from inv37_bulk_data_plane import BulkDataPlane, config as C, security as S, shm_transport, manifest

mgr = C.ConfigManager(probe=shm_transport.probe())
cfg = mgr.build([("site", C.load_file("site.json", layer="site"))], author="ops")
mgr.activate(cfg)                                   # fails closed on fatal findings
ring = S.KeyRing.from_file("/etc/inv37/keys.json")  # mode 0600
dp = BulkDataPlane(cfg, keyring=ring)
dp.recover()                                        # resume durable transfers after restart

tok = S.mint(ring, sub="loader", tenant="acme", actions=["create-transfer", "attach-buffer", "write-chunk", "finalize"])
m = manifest(data, 1 << 20)
d = dp.create_transfer(tok, m, transfer_id="tx-1", transport="shm")
view = dp.region_view(tok, "tx-1"); view[:len(data)] = data   # producer writes in place (or attach() from another process)
for i in range(m["chunk_count"]):
    dp.accept_chunk(tok, "tx-1", i)                 # verified in place, zero data-plane copies
obj = dp.finalize(tok, "tx-1")                      # read-only memoryview, re-verified end to end
consume(obj)
obj.release(); view.release()
dp.close(tok, "tx-1")                               # owner unmaps and unlinks the region
```

The 4.2.0 primitives (`manifest`, `validate_manifest`, `verify_object`, `Receiver`, `BoundedTransferPool`) are unchanged and remain available.

## Security and integrity behavior

- Untrusted manifests are validated before receiver state is allocated.
- Manifest chunk geometry, digest syntax, chunk-list digest, and configured resource ceilings are checked.
- The validated manifest is copied into receiver-owned state to prevent post-validation mutation.
- Chunk index, exact expected length, and SHA-256 digest are checked before acceptance.
- Duplicate delivery of the same verified chunk is idempotent.
- Partial objects are never assembled as complete.
- Final assembly revalidates the full chunk list and object digest.
- Receiver mutation is protected by a lock for parallel distinct-chunk delivery.
- Admission control uses a bounded semaphore and exposes saturation counters.

See `SECURITY.md` for the threat model and remaining security boundaries.

## Tests

From the directory containing this package:

```text
python -m unittest discover -s inv37_bulk_data_plane/tests -v
```

Certification run with machine-readable results bound to the source digest: `python tools/run_certification.py`. Other gates: `python conformance/run.py`, `python benchmarks/bench.py --out cur.json && python tools/perf_gate.py cur.json`, `python tools/check_governance.py`, `python tools/check_pins.py`, `python tools/check_requirements.py`, and the combined `python tools/production_gate.py --run`.

`pk_core` adapter tests are the only tolerated skips and are reported as `NOT_EXECUTED`, never as passing evidence; any skip tagged `REQUIRED-CAPABILITY` fails certification.

## Governance status

Production gate: **NO_GO** (19 criteria: 3 PASS on repository evidence, 16 BLOCKED on governance assignment, ADR approval or external evidence; plus missing approvals and unsigned evidence). Remaining work is listed per requirement in `MISSING_COMPONENTS.md`. The host↔guest part of the zero-copy objective is still unimplemented; the intra-host shared-memory path is implemented and measured (0 data-plane copies vs 2 per object in 4.2.0).

## Runbooks and compatibility

- `RUNBOOK.md` — day-0/day-1/day-2, staged rollout, rollback, and emergency-disable procedure
- `COMPATIBILITY.md` — repository/schema/runtime compatibility statement
- `SECURITY.md` — trust boundaries, implemented controls, and unimplemented controls
- `TECHNICAL_DEBT.md` — known debt and production blockers
- `CHANGELOG.md` — version history
- `REQUIREMENTS.md`, `SEMANTICS.md`, `INTERFACES.md`, `CONFIGURATION.md` — normative specs
- `THREAT_MODEL.md`, `FAILURE_MODES.md`, `PERFORMANCE.md`, `OBSERVABILITY.md`, `OPERATIONS.md`
- `governance/` — owners, CODEOWNERS, waivers, approvals, deprecations
