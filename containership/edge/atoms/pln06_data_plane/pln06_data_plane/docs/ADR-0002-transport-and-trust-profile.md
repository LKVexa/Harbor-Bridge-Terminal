# ADR-0002 — PLN-06 4.3 transport, trust, and state profile

- **Status:** Proposed — awaiting architecture, security, and operations approval (W-002). Supersedes nothing; amends ADR-0001 §Decision 7.
- **Version introduced:** 4.3.0
- **Approvers required:** service owner, technical lead, security contact, SRE (see `OWNERSHIP.json`). An approval is recorded by filling the table at the end and removing W-002.

## Decision

| Concern | Selected (4.3.0, pinned) | Rejected alternatives and why |
|---|---|---|
| In-process calls | Component-Model-style typed interface `pk:data-plane/transfer@1.0.0`; read-only `memoryview` hand-off | Direct function calls with mutable buffers (aliasing bugs); full wasmtime runtime now (heavy dependency — deferred, W-018) |
| Cross-node | `pk06-rpc/1`: length-prefixed frames, JSON headers, 1 MiB chunks, mutual HMAC challenge, optional TLS 1.2+/mTLS, SHA-256 manifest | Upstream wRPC today (no stdlib implementation; W-003); gRPC (dependency weight, no chunk manifest semantics) |
| VM control | vsock `AF_VSOCK`, inline-size control verbs only, locality `vm_control` | Sharing the bulk path for control (starvation, INV-36 violation) |
| Same-node bulk | POSIX shared memory, tenant-namespaced, unlinked in `finally` | Temp files (disk I/O, cleanup races); pipes (extra copies) |
| Remote bulk (fast path) | RDMA probe + explicit fallback | Claiming RDMA without verbs binding (W-004) |
| Identity | HMAC credentials from a rotatable `KeyRing`; KMS/HSM via `KeyProvider` | Bearer tokens without MAC; long-lived static secrets |
| Classification | Signed labels bound to tenant + digest + expiry (GAP-07 equivalent) | Caller-asserted classification (4.2 behaviour) |
| Audit | Hash-chained, MAC-sealed, fsync'd JSONL ledger | Plain logs (not tamper-evident) |
| State | Write-ahead transfer journal + fencing epoch lease; restart reconciles open transfers to `expired` | In-memory only (4.2); resuming in-flight bytes after crash (requires receiver-side resume — future) |
| Config | JSON config + overlays, schema-validated, security floor outside `dev`, durable history with canary/rollback/emergency-disable | Environment variables only (no history/validation) |

Trust boundaries, control/bulk separation and responsibility split: `docs/THREAT_MODEL.md`, `docs/REQUIREMENTS.md` §1–§4. GAP-13 owns policy, GAP-14 owns gravity (advisory), PLN-03 owns execution after hand-off, INV-36 owns control transport, INV-37 owns bulk transport — PLN-06 enforces admission, selection, integrity binding and evidence.

## Supersession and rollback

Any incompatible change to a `PK_*` schema major version, the adapter SPI, the RPC protocol version, the lifecycle state machine, or the trust model requires a new ADR or an amendment approved by the same roles. Rollback of this ADR = deploy 4.2.x runtime (API-compatible; see `docs/VERSIONING.md`).

## Approval record

| Role | Name | Decision | Date |
|---|---|---|---|
| Service owner | | | |
| Technical lead | | | |
| Security | | | |
| SRE | | | |
