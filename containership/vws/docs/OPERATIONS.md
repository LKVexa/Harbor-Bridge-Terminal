# Operator guide — RAMWS candidate

Everything in `docs/vws200/OPERATIONS.md` still applies (launcher, principals, health, deployment files that were authored but never executed). Additions and changes:

## Configuration (all environment; malformed values stop startup with exit 78)

| Variable | Default | Meaning |
|---|---|---|
| `VWS_PROFILE` | `LOCAL_VOLATILE` | the only implemented storage promise; any other value refuses to start |
| `VWS_WORKER_BACKEND` | `thread` | `thread` (worker_threads, transferred buffers, enforced V8 cap) or `process` (child process, framed pipe) |
| `VWS_WORKER_HEAP_BYTES` | 48 MiB | per-session V8 old-generation cap (thread: `resourceLimits`; process: `--max-old-space-size`) |
| `VWS_WORKER_OVERHEAD_BYTES` / `VWS_WORKER_PROCESS_BYTES` | 12 MiB / 64 MiB | runtime overhead charged per session beyond the heap cap (measured on the development host; re-measure on the target) |
| `VWS_MEMORY_LIMIT_BYTES` | 0 = detect | boundary `L`; detection prefers cgroup v2 `memory.max`, then cgroup v1; installed RAM is a labelled weak fallback |
| `VWS_FIXED_BASELINE_BYTES` | 0 = measure | `F`, the gateway's own RSS at startup |
| `VWS_POOL_IDLE_BYTES` / `VWS_HEADROOM_BYTES` | 1 MiB / 64 MiB | `G` and `H` |
| `VWS_TENANT_BYTES` | = global | per-tenant allowance |
| `VWS_CREDIT_WINDOW_BYTES` | 1 MiB | maximum un-consumed output a client may authorize |
| `VWS_MAX_OUTSTANDING_MESSAGES` | 1024 | output messages sent but not yet consumed |
| `VWS_ACK_COALESCE_MS` | 20 | `input.ack` batching for accepted seq (executed acks are immediate) |
| `VWS_REQUIRE_HEAP_CAP` | 1 | refuse to start when the per-session heap cap is provably unenforced |
| `VWS_VFS_BYTES` / `VWS_CAPTURE_BYTES` / `VWS_HISTORY_ENTRIES` / `VWS_WORKER_PENDING_BYTES` | 4 MiB / 1 MiB / 500 / 2 MiB | session quotas beneath the heap cap |

Removed: `VWS_SNAPSHOTS`, `VWS_SNAPSHOT_DIR`, `VWS_SNAPSHOT_TTL_MS`, `VWS_ACK_WINDOW_BYTES` (setting the first two is an error).

## Sizing

At startup the log line `ram.plan` shows `L F G H s`, the memory-only ceiling and the admitted session cap; `/live` shows the same plus the live ledger. Do not run with `NODE_OPTIONS=--max-old-space-size=…` on the thread backend (the cap becomes unenforceable). Re-measure `s` on the target image (`e/R28/result.json` shows the development host's numbers) before raising `VWS_MAX_SESSIONS`.

## Telemetry

`GET /live` (unauthenticated, no payloads or identities): ledger snapshot with high-water marks, per-scope rejection counts and violation counters (duplicate release, stale handle), pool idle bytes, software copy/transfer estimates per stage, `sessionResets`, `workerHeapCapHits`, `undeliveredOutputBytes`, `memoryRefusals`, gateway RSS/swap/major faults (labelled as overlapping views), `heapCap` status and `reconcile: true|false` (the ledger re-derived from leaf leases). `reconcile: false` is a bug report, not a metric.

## Restart semantics

A restart changes the server epoch. Reconnecting clients get `session.reset` naming the number of inputs whose outcome is unknown; nothing is replayed. There is no session persistence to migrate. Draining (`SIGTERM`) works as before: admission off, `service.draining`, workers stopped, listener closed, exit 0 inside `VWS_SHUTDOWN_MS`.
