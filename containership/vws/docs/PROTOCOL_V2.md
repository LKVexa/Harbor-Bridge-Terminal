# hermit.vws.v2 — implemented contract

Supersedes v1 (`docs/vws200/PROTOCOL.md` is kept for history). Same RFC 6455 endpoint (`gateway/ws.js`), now with an in-place-unmasking, single-copy frame parser and both text and binary messages.

## Two message classes

| Class | Carrier | Content |
|---|---|---|
| control | WebSocket **text** | strict JSON envelope `{v:2, type, payload, rid?, sid?+epoch?}` validated by `protocol/envelope.schema.json` (15 shapes) and the codec's extra rules (strict UTF-8, duplicate keys, depth, 65 536-byte cap before parse) |
| data | WebSocket **binary** | `byte0 kind (1 = input, 2 = output)` · `bytes1..6 uint48 big-endian seq` · `bytes7.. raw terminal bytes` (input ≤ 8192, output ≤ 16 384; zero-length refused) |

`seq` is a uint48: exactly representable in an ECMAScript Number, and the connection ends before it could wrap. Data messages carry **no sid**: they are bound to the connection that authenticated, so there is nothing to forge.

Kit kinds map as: OPEN `session.open` · INPUT/OUTPUT binary · RESIZE/SIGNAL/CLOSE as before · CREDIT `flow.credit` · ACK `input.ack` (accepted/executed), `request.ack`, `flow.credit.consumedSeq` (consumed) · ERROR `error` · SESSION_RESET `session.reset`.

## Session open and epochs

`hello` carries `serverEpoch` (fresh per process launch), the profile and limits (`maxCreditWindowBytes`). `session.open` carries the initial `creditBytes` and, optionally, `previous {sid, epoch, pendingInputs}` — what the client believes it had before a link loss. The server never revives it; it answers `session.reset {reason: process_restart | session_not_found, outcome: OUTCOME_UNKNOWN | NO_PENDING_INPUT, pendingInputs}` **before** `session.opened`, and nothing is replayed. `epoch` in every session-scoped message must equal the server epoch.

## Acknowledgement levels (kit)

| Level | Field | Meaning |
|---|---|---|
| ACK_ACCEPTED | `input.ack.acceptedSeq` | highest input seq copied into this process's bounded RAM; coalesced (20 ms) |
| ACK_EXECUTED | `input.ack.executedSeq` | highest input seq delivered to the shell when a command line last **completed** in this epoch; sent at once |
| ACK_CONSUMED | `flow.credit.consumedSeq` | highest output seq the client handed to its renderer |

None is a durable commit; a lost connection between accepted and executed is exactly the `OUTCOME_UNKNOWN` case the client reports.

## Credits

`creditBytes` is the cumulative number of output payload bytes the client authorizes. Rules (violations → `error CREDIT_VIOLATION`, close 1008): monotone non-decreasing; `creditBytes − consumedBytes ≤ maxCreditWindowBytes`; `consumedSeq ≤ last sent seq` and non-decreasing; the initial credit ≤ the window. The server sends output only while `sentBytes + next ≤ creditBytes` and fewer than `VWS_MAX_OUTSTANDING_MESSAGES` (1024) messages are unconsumed. Exhausted credit pauses the producer end to end (worker `pause`, kernel `yield()` between `seq` batches, DF child pipes paused); after `VWS_MAX_PAUSE_MS` (120 s) without renewal the session ends with `quota`. Output waiting for credit when the session ends is discarded and counted (`undeliveredOutputBytes`), never silently. **Client requirement:** advance `consumedSeq` as well as `creditBytes` — a client that renews bytes but never reports consumption stalls at 1024 unconsumed messages even with credit remaining (the reference adapter renews every ¼ window *or* 128 messages).

## Ordering and single exit

`session.opened` precedes the first output (worker `opened` record is written before the REPL starts; both travel the same ordered path). Output seq is contiguous from 1. Exactly one `session.exit` per session, after all output already handed to the socket, whichever of socket close / worker exit / local end happens first; every timer and worker callback is fenced by a generation.

## Frame parser guarantees (kit R10, R13)

Message and fragment caps are decided from headers before growth (1009); a frame complete in one socket chunk is unmasked in place and delivered as a view; a frame spanning chunks gets exactly one owned buffer, reserved in the ledger first (`reassembly` bucket, refusal → 1013), rented from the slab pool (size classes 4/16/64 KiB, idle retention capped and visible); a fragmented message is assembled once; an assembly deadline (5 s) covers a stalled peer but not the gateway's own pause; control frames are rate-limited and budgeted; every queued write's lease returns in the socket write callback. 15 raw-socket conformance tests plus Chromium and undici as independent peers.
