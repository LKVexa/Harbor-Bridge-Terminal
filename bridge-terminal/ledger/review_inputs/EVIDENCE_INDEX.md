# Evidence index (generated) — hermit-ramws

## Tests — file -> test names (all passing in e/full-suite.tap: 125/125)

### tests/chaos/lifecycle.test.js
- worker killed (-9) -> exactly one session.exit{worker_failure} -> close 1011; capacity released
- [${backend}] non-cooperative CPU loop (catastrophic RegExp) cannot be cancelled in-process: the supervisor terminates only that worker; the other tenant is unaffected
- abrupt TCP loss: worker is stopped, session released, no orphan process
- application heartbeat: a peer that never answers is closed 1008 within interval + window; an answering peer stays
- no session.open within the open deadline -> NOT_READY + 1008; idle session expires
- slow consumer (no credit): worker paused, gateway memory bounded by the ledger, a fast tenant unaffected, catch-up is lossless
- peer that stops reading its TCP socket: gateway send queue stays within budget and the connection is contained
- real process: SIGTERM drains within budget, notifies the client, exits 0; malformed PORT refuses to start (78)
- exception during hand-off after the 101 is contained: socket released, no capacity leak, next client served, error logged
- repeated and mixed termination signals run shutdown exactly once and exit 0; a signal before handlers exist terminates by default action

### tests/chaos/review-fixes.test.js
- C1 unit: a record cut in half by OUR pause does not trip the assembly deadline; a genuinely stalled peer still does
- C1 e2e: a consumer slower than the bridge assembly deadline keeps its session and later receives everything, gap-free
- S5: a consumer that never catches up is ended with an explicit quota exit after the pause budget
- S1: with open loopback-dev identity, a non-loopback Host (DNS rebinding) is refused on every route
- S3: one principal cannot hold every connection slot; others are still admitted
- S2: failed ticket attempts are limited per address without blocking a valid principal
- S4: a ping flood is closed 1008
- S7: a malformed notAfter rejects the principals file (never fail-open); removing a capability ends sessions that hold it
- S9: aliases named after Object.prototype members are ordinary keys; Tab completion on them does not end the session

### tests/desktop-ipc/guard.test.js
- sender: only the top-level frame of our window, loaded from our renderer file
- payload shapes: geometry, ids, input size, signals, dock bounds, unknown channels
- ownership: a renderer can only address sessions it opened; teardown releases them
- navigation policy: deny by default

### tests/fabric/fabric-ws.test.js
- policy unit: argv is rebuilt from validated parts only
- fabric status/topology/nodes/bundles render over the socket with host paths hidden
- each VM node executes a bundle through the WebSocket and returns a witness
- fabric run: four nodes reach CROSS_NODE_DIFFERENTIAL_AGREEMENT over the socket; byte stream is lossless
- denied: host-path options, unknown bundles, df use, build (operator-disabled), photon/browser absent
- principal without the fabric capability has no fabric commands at all
- Ctrl-C stops a running fabric job (exit 130) and the capacity slot is released

### tests/fabric/lease.test.js
- N slots admit N holders; the next waits, then times out as busy; release admits it
- build is exclusive and never holds a partial set while waiting
- abort while waiting rejects promptly; stale slot of a dead pid is reclaimed

### tests/gateway/config.test.js
- PORT: absent -> 10000; valid kept; malformed or out-of-range PRESENT value is an error, never defaulted
- bind address defaults to all interfaces; loopback-dev auth is refused off loopback; static-file needs a principals file
- origins must be bare exact origins; booleans and integers are strict; dependent settings are checked
- public configuration is an explicit allowlist (no paths, files, limits internals or environment)
- logger: single-line JSON, secret-like fields dropped, newlines neutralised, query strings removed from paths

### tests/gateway/e2e.test.js
- vertical slice: hello -> open -> opened precedes output -> input -> output -> close -> single exit
- exit command -> session.exit{logout, code}; Ctrl-C signal; resize validation
- health / live / config expose no secrets; health flips to 503 while draining
- health stays responsive (< 250 ms) while a session streams bulk output and large inbound messages arrive

### tests/gateway/ws-conformance.test.js
- handshake: 101 with subprotocol; wrong subprotocol/version/key/path are refused without upgrade
- unmasked client frame -> 1002
- reserved bit -> 1002
- unknown opcode -> 1002
- binary message with an unknown data kind -> application error, connection stays (binary is the v2 data plane)
- invalid UTF-8 text -> 1007
- declared 64-bit length over the cap -> 1009 from the header alone (no payload sent)
- fragmented message over the cap -> 1009 before buffering the offending fragment
- continuation without start -> 1002; new text inside a fragmented message -> 1002
- fragmented control frame / oversize control -> 1002
- ping is answered with an identical pong, interleaved inside a fragmented text message that still assembles
- split UTF-8 character across fragments is reassembled before strict decoding
- stalled fragment assembly hits the deadline -> 1008
- close handshake: peer close is echoed with the same code; invalid close code -> 1002; 1-byte close payload -> 1002
- data after our close is ignored; abrupt TCP loss releases the connection

### tests/protocol/bridge.test.js
- byte-at-a-time delivery (split header + split body)
- many records in one read
- zero-length and oversize are rejected from the header alone
- truncated record is distinguished from clean EOF
- unknown type / unknown property / wrong direction / duplicate key / bad utf8 rejected
- assembly deadline fires for a stalled partial record
- decoder stops after a fatal error

### tests/protocol/codec.test.js
- v2 valid control vectors are accepted (16); invalid (15) and raw-invalid (3) are rejected; wire size and UTF-8
- strict JSON: nested duplicate key, __proto__, depth, trailing data, non-finite, leading zero
- binary data frames: header round-trip for every uint48 boundary, no payload copy, caps and direction enforced
- base64 helpers still round-trip (used by the process backend bridge only)
- encode refuses invalid outbound envelopes

### tests/ram/descriptor.test.js
- kit fixtures: all 13 descriptor cases give the verdict the kit expects (parsed strictly, so 2^63 is refused rather than rounded)
- lifecycle: admit -> execute -> complete releases the lease exactly once; illegal transitions throw
- Ownership/Validity: another principal, another session, stale epoch, stale plan (policy revoked), stale or foreign lease are all REJECTED with a reason
- state gating and formats: input only while ACTIVE; resize carries no payload; extents must lie inside the live lease; budget must equal lease capacity
- plan identity changes with every bound input and refuses missing parts

### tests/ram/ledger.test.js
- admission is all-or-nothing across session/tenant/global and names the refusing scope
- leases: capacity (not logical length) is charged; bucket, session caps; exhaustion and oversize are refused before allocation
- Lifetime: capacity returns only after the LAST consumer; duplicate release is counted, never refunded twice
- Aliasing: a view adds a reference, not capacity; a non-physical capacity reservation adds quota but no physical bytes
- Validity: stale generation and foreign handles are refused and counted
- close: refuses new leases at once, returns the admission reservation exactly once and only after in-flight leases settle
- randomized acquire/retain/release/close never breaks reconciliation and ends at zero
- slab pool: actual capacity >= request, idle retention capped and visible, zero-fill on return, double/foreign return counted, oversize refused

### tests/ram/v2-e2e.test.js
- [${backend}] vertical slice: hello(epoch) -> open -> opened before output -> binary input/output -> executed ack -> close -> single exit; ledger returns to zero
- credits: the server never sends beyond the granted window; output resumes exactly on credit; violations close 1008
- SESSION_RESET: a client presenting state from another epoch gets session.reset with OUTCOME_UNKNOWN (pending) or NO_PENDING_INPUT, then a fresh session; nothing is replayed
- binary data discipline: zero-length payload, unknown kind, output kind from the client, wrong seq, oversize input are rejected; a 8192-byte input is accepted in one message
- memory admission: sessions are refused (503 / LIMIT_EXCEEDED) when the ledger allowance is exhausted; no worker is created; capacity returns on close
- worker heap cap: a session that allocates without bound is ended with LIMIT_EXCEEDED/quota; the gateway and another tenant continue

### tests/security/authz.test.js
- no credential / wrong credential / malformed header -> 401 before upgrade
- Origin: unlisted -> 403 even with a valid credential; listed origin + bearer header is NOT accepted (browser path needs a ticket)
- ticket: issued only to an authenticated POST from an allowed origin; HttpOnly+SameSite=Strict+path-scoped; single use; origin-bound; expires
- session ids authorize nothing: another connection cannot address a live sid; unknown and foreign sids are indistinguishable
- stale epoch, replayed rid, duplicated input seq, client-forged server message, second session.open
- capacity: per-principal and global caps; refused before a worker is spawned; released on close
- revocation ends a live session; revoked token cannot reconnect
- secrets and host details never reach the shell, the protocol, or the logs
- terminal-escape and command-injection text is data: no host effect

### tests/ui/browser.test.js
- web client in Chromium: sign-in -> terminal -> commands -> fabric run -> reconnect as NEW session

### tests/ui/client-units.test.js
- full-jitter backoff stays within [0, min(30 s, 0.5 s * 2^attempt)) and uses the supplied randomness
- binary input header writer agrees with the codec for boundary seqs
- input chunking: <= limit per chunk, byte-exact reassembly even when a multi-byte character straddles chunks
- geometry clamp: finite integers inside policy for any input
- IPC adapter open barrier: output that overtakes the open reply is held, delivered in order after start(), never before
- holding queue is bounded and overflow is announced, not silent

### tests/vt/vt.test.js
- F06 unterminated OSC retention is bounded and a truncated string is never dispatched
- F07 OSC: BEL and ESC \\ terminate; ESC + other byte aborts WITHOUT dispatch and the new sequence still executes
- titles are capped and stripped of control characters; OSC 52/8 are not implemented
- hostile CSI counts terminate immediately (renderer DoS): 999999999 for @ P L M S T X
- over-long CSI parameters / intermediates abort and recover; ESC inside CSI restarts; C0 executes inside CSI
- parser state persists across arbitrary chunk boundaries (every split point of a mixed stream)
- F08 scrollback bound holds on the resize path and the scroll path; total-cell budget holds for wide screens
- geometry is clamped before allocation (constructor and resize)
- random byte soup never throws and never escapes bounds

### tests/worker/kernel.test.js
- F05 geometry: invalid open throws, invalid resize is refused and never stored
- F04 close settles the active reader and emits exactly one exit
- close during a running command aborts it; still one exit; no late output
- F10 open barrier: deferStart emits nothing until startSession
- exit command and Ctrl-D report logout once
- Ctrl-C at prompt, during command, and SIGINT signal are distinct and non-fatal
- type-ahead: pasted multi-line input executes every line in order
- F17 bounds: capture limit, seq limit, regex length, input line length
- VFS quota surfaces as a command error, not a crash
- commandFilter removes commands from the registry

## Measurements

- e/R28/experiment.frozen.json (preregistration, frozen before data) · e/R28/result.json (main: v1/process baseline vs v2/thread candidate, 3 launches x 10 runs) · e/R28/result.process-backend.json (ablation: v2 with process backend) · e/R28/raw*.jsonl (every run) · e/R28/pre-optimisation/ (first run, before the descriptor optimisation) · docs/EXPERIMENT.md (analysis)
- docs/vws200/RESOURCE_MODEL.md (v1 loopback numbers, historical)

## Documents

### docs/OPERATIONS.md
- Operator guide — RAMWS candidate
- Configuration (all environment; malformed values stop startup with exit 78)
- Sizing
- Telemetry
- Restart semantics

### docs/PROTOCOL_V2.md
- hermit.vws.v2 — implemented contract
- Two message classes
- Session open and epochs
- Acknowledgement levels (kit)
- Credits
- Ordering and single exit
- Frame parser guarantees (kit R10, R13)

### docs/RAMWS.md
- RAMWS candidate — what "RAM-resident virtual WebSocket" means here
- The claim, and what it is not
- Decisions (approved by the owner on 2026-09-21)
- Eight descriptor fields and six invariants — where each lives
- Memory plan (kit R06) — enforced, not just planned
- What crosses which boundary (kit R08, R18)
- Not done / not claimed

### docs/SECURITY.md
- Security — RAMWS candidate
- Changed boundaries
- Retained residual risks

### docs/vws200/*.md — the previous (v1) candidate documents, kept for history; cite only where still true

## Code

- ram/ledger.js — Ledger (admit/reconcile/snapshot, global+tenant+session scopes, rejects/violations counters), SessionAccount (acquire/reserveCapacity/resolve/close, bucket caps), Lease (retain/release/generation/state), SlabPool (size classes, idle cap, zero-fill, double/foreign return counters)
- ram/descriptor.js — eight-field descriptors from server state, validateShape (kit schema + arithmetic), planIdentity, createAdmission (admit/execute/complete, state gating, ownership/epoch/plan/lease/extent/budget checks, stats), Operation lifecycle
- ram/allowance.js — detectBoundary (cgroup v2/v1/explicit/weak), sessionReservation, plan (L F G H s ceiling)
- ram/residency.js — /proc RSS/swap/faults per pid, interval observer (UNKNOWN when unavailable)
- ram/traffic.js — software copy/transfer ledger per stage
- gateway/ws.js — RFC 6455 endpoint: in-place unmask, single-copy reassembly with ledger+pool, binary + text, leases released in write callbacks, control budget/rate, close handshake
- gateway/connection.js — v2 state machine: hello(epoch), session.open/reset, admission per operation, credits, input/executed acks, pause budget, worker link supervision, single exit, telemetry()
- gateway/worker-link.js — ThreadLink (resourceLimits heap cap, transferred buffers, terminate) and ProcessLink (framed pipe, --max-old-space-size)
- gateway/server.js — memory plan at startup, ledger/pool/traffic wiring, admission before upgrade, /live telemetry, heap-cap probe (EHEAPCAP), drain
- gateway/config.js — RAMWS settings, profile/snapshot/backend refusals, publicConfig
- worker/core.js — transport-neutral session (open barrier, executed events, usage), worker/thread.js, worker/host.js, worker/output-gate.js (owned chunks, overflow marker)
- protocol/codec.js — strict JSON, v2 schema validation, decodeData/writeDataHeader (uint48, no-copy views), protocol/envelope.schema.json (15 shapes), protocol/protocol-meta.json (binary layout, credit rules, ack semantics), protocol/bridge.js (+ bridge.schema.json)
- src/main/spiral/kernel.js (command-complete event, yield(), bounded captures/history/lines), line-reader.js (batched printable runs), commands/coreutils.js (streaming seq), vfs.js (quotas)
- client/ws-adapter.js — browser v2 client: binary I/O, credits, session.reset reporting, reconnect with previous state, no replay
- tests/helpers.js — v2 test client and raw-socket peer
- config/limits.json, deploy/* (AUTHORED, NEVER EXECUTED)
