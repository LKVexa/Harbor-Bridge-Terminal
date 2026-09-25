# Security — RAMWS candidate

The v1 threat model and its controls remain in force; see `docs/vws200/SECURITY.md` for the full table and the adversarial-review findings that were fixed there. This page records what changed.

## Changed boundaries

| Area | v1 | v2 / RAMWS | Consequence |
|---|---|---|---|
| Session worker | one OS process per session | one **worker thread** (V8 isolate) per session by default; process backend optional | A thread shares the gateway's address space and OS credentials. The isolate boundary keeps JavaScript state separate and the enforced heap cap contains memory, but a native-level bug in Node would now affect the whole gateway rather than one child. Neither backend was ever an OS sandbox; untrusted plugins remain excluded. Environment allowlisting, the command filter and the DF policy are unchanged. |
| Data messages | JSON + base64, `sid` on every message | binary frames bound to the authenticated connection, no `sid` | Nothing to forge in a data frame; cross-connection session addressing is impossible by construction (`tests/security/authz.test.js`). |
| Flow control | server-side ack window | client byte credits | A client can only *slow* its own session; credit arithmetic is validated and violations close 1008. A credit-starved session ends after `VWS_MAX_PAUSE_MS` so a stalled client cannot hold a session reservation forever. |
| Memory | per-connection budgets | global/tenant/session ledger; admission before allocation | A single principal cannot exhaust service memory: its sessions are refused at admission, and every buffer is charged to its account. `/live` exposes counts, never payloads. |
| Disk | optional workspace snapshots | none for session/payload state (LOCAL_VOLATILE) | No session or payload state reaches disk; nothing user-derived is at rest. The DF fabric lease directory (pid markers only, under `os.tmpdir()`) is the sole disk write and existed in v1 too. Process loss is disclosed with `session.reset`. |
| Epoch | integer 1 | random per launch | Stale handles and cached plans from a previous process cannot match; policy changes bump the plan identity immediately. |

## Retained residual risks

1. Worker isolates run in-process (above). For hostile multi-tenant use prefer `VWS_WORKER_BACKEND=process` and a container per gateway.
2. `heapCap: UNENFORCED` (process-wide `--max-old-space-size`) removes the per-session memory cap; the gateway refuses to start in that state unless explicitly overridden, and says so in `/live`.
3. Telemetry in `/live` is unauthenticated (as `/health` was). It contains limits, counters and byte totals, no identities or payloads. Restrict it at the edge if counts are sensitive.
4. No independent (human) security review has taken place. Two adversarial AI review passes were run (v1, then this v2 candidate); findings and fixes are below.

## Second review (v2 candidate) — findings and fixes

| ID | Severity | Finding | Fix | Regression test |
|---|---|---|---|---|
| R2-1 | HIGH (confirmed: 473 MB held) | The thread link kept output that arrived while the session was paused in a JavaScript queue outside the ledger — a slow client with a fast producer could grow the gateway heap without bound, defeating the Budget invariant the candidate claims. | The held queue is gone. The worker's `OutputGate` now owns exact-size chunks and counts bytes **in flight** to the gateway; it pauses the producer when in-flight bytes exceed half of `VWS_WORKER_PENDING_BYTES`; the gateway reports consumption back (`consumed` records, coalesced per event-loop turn) only after the chunk has been handed to the socket and charged to the connection's `queued_out` bucket. Every byte in transit is therefore either in a ledgered lease or inside the worker's bounded window. The kernel's `yield()` became a macrotask so a paused worker actually stops producing. | `tests/chaos/review-fixes.test.js` R2-1: a non-crediting client against a `yes`-style producer; gateway RSS growth bounded, `/live` in-flight ≤ window |
| R2-2 | LOW | Output discarded at session end (refused, or waiting for credit) was released to the ledger but not counted, so `undeliveredOutputBytes` under-reported. | Counted at every discard site (`_output` refusal, `_finalExit`, socket close). | R2-2: counter equals bytes cut |
| R2-3 | LOW | Input was copied twice on the thread backend (once into an owned buffer, once by `postMessage`). | The owned buffer is transferred, exactly sized (`allocUnsafeSlow`, then transfer). | `bridge_in_transfer` in `/live` traffic; e2e ledger-returns-to-zero |
| R2-4 | INFO | Diagnostics from a worker could not be correlated with a connection in logs. | Worker env carries `VWS_W_CONN`, echoed in `diag` records. | — |
| R2-5 | SUSPECTED, not confirmed | `VWS_MAX_OUTSTANDING_MESSAGES` (1024) can stall a client whose renderer consumes slowly but whose credits are byte-based only; the reference adapter credits by count as well. Third-party clients must renew `consumedSeq`, not only `creditBytes`. | Documented in `docs/PROTOCOL_V2.md`; no code change. | — |

Cost: the R2-1 fix is why W1 in `docs/EXPERIMENT.md` fell from 46 % to 42 % (and why the process-backend ablation is now worse than v1 for keystrokes). The bound was kept; the number was re-measured, not kept.
