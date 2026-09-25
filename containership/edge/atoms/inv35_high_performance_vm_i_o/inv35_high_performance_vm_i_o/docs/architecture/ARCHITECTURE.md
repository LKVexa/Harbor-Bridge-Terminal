# INV-35 High-performance VM I/O — Architecture (v4.3.0)

| Field | Value |
|---|---|
| Requirement IDs | INV-35-C001–C008 (baseline), **C005**, C009, C010, C021, C032, C046 |
| Owner | accountable_owner (see `governance/OWNERS.json`) |
| Approval state | **PENDING** — requires accountable_owner + security_owner + runtime_platform_owner (`governance/APPROVALS.json`) |
| Normative status | Sections marked **[N]** are normative; **[I]** illustrative; **[X]** executable conformance logic (tests enforce them) |
| Revision history | r1 2026-09-22 — created for v4.3.0 closure pass |

## 1. What this component is  [N]

INV-35 owns the guest/host I/O datapath safety boundary. Its source function is
**separate orchestration and bulk-data channels** (ADR-0001): control operations
(queue registration, lifecycle, configuration, quarantine) and bulk operations
(descriptor submit/complete) travel on distinct interfaces with disjoint
capability actions.

The repository ships three layers:

| Layer | Path | Nature |
|---|---|---|
| Safety core | `io_model.py` | **[X]** reference/conformance model of descriptor validation, bounds, depth and notification liveness. Unchanged semantics since 4.2.0; limits may only be *tightened* (`depth_limit`, `chain_limit`, `byte_limit`). |
| Production-shaped runtime | `runtime/` | **[X]** authentication, capabilities, tenant isolation, quotas, deadlines, idempotency, lifecycle, quarantine, config, telemetry, audit, crash recovery, release gate. Dependency-free Python. |
| Binding | `component.py`, `contract.py` | Optional `pk_core` certification binding (unavailable in this archive ⇒ `VERIFY=PARTIAL`). |

**The Python runtime is not a production virtio/vhost backend.** It defines and
enforces the semantics a production backend (vhost-user, vDPA, in-kernel vhost)
must reproduce; the fixtures under `fixtures/` are the portable conformance oracle.

## 2. Context diagram  [I]

```text
                 ┌──────────────────────── control plane (orchestration) ───────────────────────┐
                 │  INV-25 MicroVM devices ──► which queues exist                                  │
   operator ───► │  controller (epoch-fenced) ──► ControlPlane.register/transition/apply_config    │
                 └──────────────┬──────────────────────────────────────────────────────────────────┘
                                │ capability actions: register_memory, lifecycle, configure,
                                │ quarantine, read_status   (never submit/complete)
                                ▼
 ┌────────────┐   ring writes   ┌──────────────────────── INV-35 ───────────────────────────────┐
 │ guest (VM) │ ──────────────► │  Datapath.submit/complete  ─►  io_model.VirtQueue (validate)   │
 │ INV-24     │ ◄── wakeups ─── │  Runtime: quotas · breaker · idempotency · audit · telemetry   │
 └────────────┘                 └──────────────┬─────────────────────────────────────────────────┘
      untrusted                                │ bulk data (validated chains only)
                                               ▼
                                   PLN-06 data plane / network or storage backend
```

## 3. Data/control flow — orchestration vs bulk  [N]

```text
ORCHESTRATION (low rate, authenticated, audited, journalled)
  controller ─cap(register_memory)─► register_queue ─► Lifecycle CREATED→STARTING→SERVING
  controller ─cap(lifecycle)───────► transition (epoch checked)  ─► journal + audit
  operator   ─cap(configure)───────► apply_config/rollback (validate→digest→atomic swap)
  security   ─cap(quarantine)──────► QUARANTINED / DISABLED (live, immediate)

BULK (high rate, per-call capability check with cached crypto verification)
  vhost worker ─cap(submit)──► lifecycle gate → capability → tenant bind → deadline/cancel
                               → breaker → idempotency → io_model.validate → quota → commit
  vhost worker ─cap(complete)► lifecycle gate → capability → tenant bind → io_model.complete
                               → quota release → stall-progress → notify decision
```

Ordering on the submit path is tested (`tests/security`, `tests/contracts`): no
counter moves before every earlier stage has passed.

## 4. Trust and ownership boundaries  [N]

See `BOUNDARY_INVENTORY.md` for the full inventory. Summary:

| Boundary | Trust | Enforcement point | Failure consequence |
|---|---|---|---|
| Guest ring → datapath | **untrusted** | `io_model.VirtQueue.submit` | refusal INV35-E1xx, audited, no mutation |
| VMM/vhost worker → datapath | authenticated, least privilege | `Authority.authorize(action∈{submit,complete})` | INV35-E30x |
| Controller → control plane | authenticated, epoch-fenced | `Lifecycle.claim/_check_epoch` | INV35-E307 |
| Operator config → runtime | validated, provenance-bound | `config.validate` + digest check | INV35-E500/E501/E504, active config unchanged |
| Key/time services → runtime | required dependency | `KeyRing.available`, `Authority.time_trusted` | fail closed INV35-E306, not ready |
| Release artifact → host | digest-verified | `release.verify_manifest` | promotion refused |

## 5. Environment, runtime, network, storage and control-plane assumptions (C005)  [N]

Every assumption has an enforcement point, a detection mechanism and a defined
behaviour when false. `contract.py::assumptions` are items A1–A3.

| # | Assumption | Enforcement / detection | If false |
|---|---|---|---|
| A1 | A guest can write arbitrary values into its own ring | Every field validated in `io_model` before use; fuzzed (`tests/fuzz`) | n/a — assumed hostile |
| A2 | Chains may loop or be malformed | loop/length/dangling checks; fixtures `adversarial/*` | n/a — assumed hostile |
| A3 | Notification suppression is a correctness hazard | suppression only when drained; `NO_SUPPRESSION` degraded mode; stall detector | stall ⇒ `ready=false`, operator enters `NO_SUPPRESSION` |
| A4 | CPU arch: 64-bit, little-endian; addresses fit in unsigned 64-bit | schema `minimum:0`; fixture `wraparound_length` (2^64) | range refused E105 |
| A5 | Page size/alignment: **no alignment is assumed**; any byte range is checked exactly | range arithmetic on unbounded ints | n/a |
| A6 | IOMMU/translation: guest-physical addresses are validated against *registered* regions; IOVA translation is the backend's job and must be applied **after** INV-35 validation | boundary doc; production backend conformance runs fixtures post-translation | backend non-conformant ⇒ release blocked (C084) |
| A7 | Memory-registration lifetime: regions are immutable for a queue's life; re-registration requires DRAINING→STOPPED and a new queue | `register_queue` refuses duplicates; `MemoryRegion` frozen | refusal E400/E305 |
| A8 | Ring/mapping concurrency: the ring may change concurrently; INV-35 validates a **snapshot** (`dict(chain)` + frozen `Descriptor`) | `test_chain_mapping_is_snapshotted` | production must copy descriptors to host memory before validation (TOCTOU); mandatory in ADR-0001 |
| A9 | Host kernel: vhost/vDPA availability varies per site | `vhost_offload` config flag; profile defaults | fall back to VMM-thread datapath; semantics unchanged |
| A10 | Network/storage backend: ordering, MTU/block size are backend-owned; INV-35 bounds bytes per chain via `max_chain_bytes` | `byte_limit` → E107 | refusal |
| A11 | Interrupt/event delivery may be lost by the host; liveness relies on "pending ⇒ notify" | `complete()` forces notify when pending>0; concurrency test asserts zero lost wakeups | stall detector flags, not-ready |
| A12 | Control plane may be unreachable | datapath safety uses only local state; `control_plane_lost()` offline policy | DEGRADED within grace; freeze/quarantine beyond (config) |
| A13 | Key/attestation/time services may fail | `KeyRing.available`, `time_trusted` | fail closed E306 |
| A14 | Host process may crash | append-only journal; `Runtime.recover` | queues return FROZEN, reservations exact |

## 6. Tenant/workload isolation across execution/state/network/device (C046)  [N]

* **Execution:** each queue belongs to exactly one tenant; every bulk and control
  call re-binds `(capability.tenant, call.tenant, queue.owner)`; mismatch ⇒ E305
  and an `isolation.refused` audit event.
* **State:** per-tenant quota (`QuotaManager`) caps each tenant's share of host
  descriptor capacity and submit rate; idempotency cache is keyed `(tenant,key)`;
  metrics cardinality is capped so one tenant cannot exhaust telemetry.
* **Network/device:** INV-35 does not own backends (A10); it guarantees that only
  validated, tenant-bound chains reach PLN-06.
* **Side channels:** constant-time MAC compare; timing of validation is O(chain)
  and independent of *other* tenants' state (benchmark `scale_tenant_fairness_spread`).
  Microarchitectural mitigations are INV-43's (optional peer).

## 7. Immutable artifact vs mutable configuration/state layout (C032)  [N]

| Class | Paths | Mutability |
|---|---|---|
| Immutable release artifact | `*.py`, `runtime/`, `schemas/`, `fixtures/`, `docs/`, `benchmarks/bench.py`, `release/dependencies.json` | digest-pinned in `release/manifest/MANIFEST.json`; any change ⇒ new version |
| Mutable configuration | operator JSON documents (see `config/examples/`), layered defaults→profile→environment→site | validated + provenance-stamped at activation; rollback via history |
| Runtime state | queues, reservations, quotas, idempotency cache, journal, audit chain | in memory; journal exported for crash recovery; see `docs/operations/STATELESSNESS_DECISION.md` |

## 8. Links

`contract.py` · `CHECKLIST.json` · `AUDIT_MATRIX.json` · `requirements/traceability.json` ·
`docs/adr/ADR-0001-*.md` · `docs/security/THREAT_MODEL.md` · `docs/resilience/FMEA.md`.
