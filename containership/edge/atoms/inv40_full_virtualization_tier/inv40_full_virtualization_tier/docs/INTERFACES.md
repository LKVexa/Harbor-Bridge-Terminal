# Boundary inventory (INV-40-C021..C026, C028)

| Boundary | Direction | Schema | AuthN | AuthZ capability | Timeout / retry / idempotency | Limits |
|---|---|---|---|---|---|---|
| `create` | caller → tier | `PK_FULL_VM_CREATE_REQUEST.v1` → `PK_FULL_VM/1` | capability token | `create` on tenant | idempotency key per tenant; replay returns same result | body ≤ 64 KiB, depth ≤ 16, ≤16 extra devices, memory ≤ ceiling |
| `boot` | caller → tier | → `PK_FULL_VM_BOOT/1` | token | `boot` | deadline `op_timeout_ms`; provider launch retried only on retryable codes with full-jitter backoff (≤ `retry_max_attempts`); one boot in flight per guest | admission concurrency/queue |
| `stop` | caller → tier | → `PK_FULL_VM_STATE/1` | token | `stop` | not retried automatically | — |
| `destroy` | caller → tier | → `PK_FULL_VM_STATE/1` | token | `destroy` | idempotent | — |
| `quarantine` | operator → tier | dict | token | `quarantine` (tenant/guest) or human `admin` (tier) | — | — |
| `health` | operator/probe → tier | dict (C071) | local | — | — | — |
| errors | tier → caller | `PK_FULL_VM_ERROR.v1` | — | — | `class`, `retryable` | message ≤ 4096 |
| Hypervisor | tier → QEMU | argv + QMP JSON lines | unix socket in private workdir | process identity | QMP socket wait bounded by `boot_timeout_s` | QMP message ≤ 1 MiB |
| Device | tier → `/dev/kvm` | ioctl (via QEMU) | file mode | tier identity only | — | — |
| Journal / audit / config files | tier → disk | CRC-framed JSON / `PK_FULL_VM_AUDIT.v1` / `PK_FULL_VM_CONFIG.v1` | filesystem perms | tier identity | fsync before ack | journal compaction |
| pk_core integration | pk_core → component | `pk_core` API surface in `fvt/compat.py` | in-process | — | — | — |
| Controller lease | INV-33 → tier | `(controller, epoch)` | token + epoch | mutating ops | lease TTL | — |

No WIT or RPC boundary is exposed by this repository; transport binding (HTTP/gRPC) is upstream and not implemented here.

Backpressure: the queue is bounded; overflow is shed immediately with a retryable code rather than blocking the caller. Cancellation: `Deadline.cancel()` → `PK_FULL_VM_CANCELLED` at the next checkpoint.
