# INV-17 Failover / Distributed Disposition

**Controls:** C055, C058 (with C057 crash semantics)
**Disposition:** N/A for failover, replication and distributed consensus — **PROPOSED**; approver UNASSIGNED — owner to fill; review/expiry date: to be set by approver.

## Rationale

- Contract boundary "site": *stream handles are instance-local* (`contract::build`).
- `control::StreamRegistry` is memory-only. Docstring (C057): a process restart loses every stream;
  holders of an old id get `StreamNotFound` ("streams do not survive restart") and must reopen.
  There is no replay or resume.
- Credit is held by the reader in the same process (`Stream.credit`); replicating it would need a
  consensus protocol that the contract lists no owner for, and "Transport encoding" and
  "Scheduling of readers and writers" are in `not_owns`.
- Elements are opaque, in-memory objects (not serialisable in general), so state transfer to a
  standby is not meaningful at this layer.

## What INV-17 does provide to adjacent layers

| Signal | Source | Use by enclosing controller |
|---|---|---|
| `health` / `ready` | `observability::status` (`/healthz`, `/readyz`) | Remove instance from rotation when `ready=false` |
| `disabled` | `inv17_disabled` | Distinguish deliberate disable from failure |
| Drop errors | `EndDropped` to the surviving end | Peer learns the far end is gone; no silent loss |
| Idempotent writes | `Stream.write(idempotency_key=...)` within `idempotency_window` | Safe retries within one stream lifetime only (window is in-memory) |

## Owned by adjacent layers

| Concern | Owner |
|---|---|
| Re-establishing streams after instance loss | Host runtime / INV-15 async ABI caller |
| Retry and end-to-end dedupe across restarts | Application / INV-20 (HTTP semantics) |
| Transport, partitions, reconnect | Transport layer (not in this package) |
| Instance placement and failover | Orchestrator |

## Verification

Planned `tests/test_disaster.py`: restart -> `StreamNotFound`; partition modelled as dropped end ->
`EndDropped`. No drill has been conducted.
