# hermit.vws.v1 — implemented contract

The envelope schema (`protocol/envelope.schema.json`) and direction/cap metadata (`protocol/protocol-meta.json`) are the series files, byte-identical. `protocol/codec.js` (Node + browser) implements what a schema cannot: size cap before parse, strict UTF-8, duplicate-key and non-finite rejection, depth bound, canonical base64, decoded-size caps, direction, `sid`/`epoch` pairing. All 40 series vectors pass (`tests/protocol/codec.test.js`).

## Transport

RFC 6455, subprotocol `hermit.vws.v1` required, version 13 only, no extensions. Text messages only; binary closes 1003; invalid UTF-8 closes 1007; oversize (single or fragmented, decided from headers before buffering) closes 1009; framing violations close 1002; stalled fragment assembly closes 1008 after 5 s. Client frames must be masked. Ping is answered with an identical Pong, including between fragments. Close: peer close is echoed with the same code; our close waits up to 3 s for the peer's Close on the existing receive path, then drops TCP. `gateway/ws.js`, 15 tests in `tests/gateway/ws-conformance.test.js` against a raw-socket peer, and every other gateway test runs against Node's built-in (undici) WebSocket client, an independent implementation; the browser test uses Chromium's.

## Admission order (before upgrade)

exact path `/ws/terminal` -> no query (unless enabled) -> not draining -> Origin policy -> RFC 6455 request validity -> identity (loopback-dev | bearer header with no Origin | one-use ticket cookie bound to Origin) -> connection cap -> `101`. Rejections are ordinary HTTP responses (400/401/403/404/426/503) with `Connection: close`; no upgrade happens.

## Terminal API (TerminalTransport, `client/transport.js`)

`open({cols,rows}) -> {sessionId}` · `start(id)` · `write(id,string)` · `resize(id,cols,rows)` · `signal(id,'SIGINT')` · `close(id)` · `status(id)` · `onData` · `onExit` · `onState` · `capabilities`. The IPC and WebSocket adapters both implement it; the renderer uses nothing else.

## State machine (`gateway/connection.js`)

`CONNECTING -> AUTHENTICATED -> OPENING -> ACTIVE -> DRAINING -> CLOSED`

| Rule | Enforcement |
|---|---|
| `hello` is the first server message; `session.open` must arrive within 10 s | else `error NOT_READY`, close 1008 |
| One session per connection | second `session.open` -> `BAD_MESSAGE` |
| Capacity reserved before a worker is spawned | global `VWS_MAX_SESSIONS`, per principal `VWS_MAX_SESSIONS_PER_PRINCIPAL`; refusal `LIMIT_EXCEEDED`, close 1013 |
| **Open barrier** | worker writes the `opened` record to the ordered pipe, only then starts the REPL; gateway sends `session.opened` on the same ordered queue as output. OBSERVED: `session.opened` index < first `terminal.output` index |
| `sid` = 144 random bits, `epoch` = 1 | a `sid` that is not this connection's -> `FORBIDDEN`, identical for unknown and foreign ids; wrong epoch -> `STALE_EPOCH` |
| Input `seq` must be exactly previous + 1 | else `BAD_MESSAGE`, nothing reaches the worker |
| `rid` replay window of 512 | duplicate -> `BAD_MESSAGE`; OBSERVED: a duplicated input executed once |
| Output `seq` starts at 1, contiguous | client reports any gap visibly |
| `output.ack` within `[acked, produced]` | else `BAD_MESSAGE` |
| Exactly one `session.exit` | one idempotent path for socket close, worker exit, local end; ordered after prior output |
| Every timer/worker callback carries a generation check | incremented on close; late events cannot touch a newer state |
| `session.resume` | `RESUME_UNAVAILABLE` (capability advertised false) |
| Rate limit | token bucket `VWS_MSG_RATE`/s, burst 2x; 20 strikes of invalid/over-rate messages -> close 1008 |

## Errors

Stable codes from the schema: `UNAUTHORIZED FORBIDDEN BAD_MESSAGE LIMIT_EXCEEDED UNSUPPORTED NOT_READY STALE_EPOCH OUTCOME_UNKNOWN RESUME_UNAVAILABLE INTERNAL`. Messages are fixed safe strings (no echoed input, no paths, no stack). `retryable` is true only for rate limiting and not-yet-active. `request.ack` means accepted for delivery to the shell, never "command completed". After a lost connection the client reports unacknowledged inputs as outcome UNKNOWN and re-sends nothing.

## Flow control (end to end)

1. Worker `OutputGate`: <= 16384 raw bytes per record; queue bounded (default 4 MiB). A cooperative producer (the DF CLI pump) pauses its child's pipes; the kernel waits at pipeline boundaries while congested; a producer that still overflows is aborted and the terminal receives an explicit `[output gap …]` line.
2. Gateway: data sends are refused beyond `VWS_SEND_QUEUE_BYTES` (524288); errors, acks, heartbeat and close may use a further 16384 reserved bytes. While data is pending or un-acknowledged bytes exceed `VWS_ACK_WINDOW_BYTES`, the gateway sends `pause` and stops reading the worker pipe.
A pause is bounded: after `VWS_MAX_PAUSE_MS` (120 s) without the consumer catching up the session ends with `error LIMIT_EXCEEDED`, `session.exit{quota}`, close 1008. The bridge assembly deadline is suspended while the gateway itself is not reading.
3. Browser: acknowledges every 64 KiB or 250 ms; `terminal.resize` is coalesced to the newest geometry; keyboard input is never dropped silently (`input-dropped` state when not connected).

OBSERVED: an unacknowledging client and a TCP peer that stops reading both leave the gateway within budget with the worker paused, another tenant unaffected, and 150 000 lines delivered gap-free after catch-up (`tests/chaos/lifecycle.test.js`).

## Local bridge (`protocol/bridge.js`, `protocol/bridge.schema.json`)

`uint32 big-endian length` + that many UTF-8 JSON bytes; 1..65536; zero and oversize rejected from the header before allocation; split headers/bodies and coalesced records handled; 5 s assembly deadline; clean vs truncated EOF distinguished; strict JSON; per-direction record schemas with unknown types and properties rejected. Records: `open input resize signal close pause resume ping snapshot` / `ready opened output exit pong snapshot diag`. stdout carries records only; stderr is drained continuously into a 2 KiB tail.

## Compatibility

`v` is const 1. A binary profile, resume, or extra capabilities require a new negotiated contract; this candidate adds no field to the v1 envelope. The `fabric` capability is therefore advertised in `/config.json`, not in `hello`.
