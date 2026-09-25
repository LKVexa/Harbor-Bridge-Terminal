# Validation: what ran, what it proves, what did not run

Environment: Linux 6.18.44 x86_64, 2 vCPU, Node v22.22.2, Python 3.11.15, gcc/make/OpenSSL/Java present, Chromium 1194 via Playwright 1.56. Raw TAP log: `e/_runs/full-suite.tap` (**106 tests, 106 pass, 0 fail, 0 skipped**, 86.1 s; the identical suite also passed from a clean unzip of the release archive). Command: `node --test tests/**/**.test.js` with `NODE_PATH` pointing at a global Playwright. All four DF nodes were built first with `DF_Fabric/BUILD` (34 s).

| Suite | Tests | What it exercises |
|---|---:|---|
| `tests/protocol/codec.test.js` | 6 | the series' 17 valid + 18 invalid + 3 raw vectors, size and UTF-8 cases; strict JSON; base64 parity with `Buffer` for every tail length; outbound validation |
| `tests/protocol/bridge.test.js` | 7 | byte-at-a-time, coalesced, zero/oversize from header, truncated EOF, schema/direction/duplicate-key/UTF-8, assembly deadline, stop after fatal |
| `tests/worker/kernel.test.js` | 10 | geometry, close lifecycle, open barrier, exit paths, Ctrl-C cases, type-ahead, capture/seq/regex/line bounds, VFS quotas, command filter |
| `tests/vt/vt.test.js` | 9 | OSC bound + true ST, title hygiene, hostile CSI counts, over-long CSI, **every split point** of a mixed stream, scrollback bounds, geometry clamp, random byte soup |
| `tests/gateway/e2e.test.js` | 4 | vertical slice with ordering assertions; signals/resize/exit codes; health/live/config/static exposure; drain; health latency under bulk output (< 250 ms) |
| `tests/gateway/config.test.js` | 5 | PORT rules, bind/auth constraints, exact-origin parsing (wildcards refused), public-config allowlist, log redaction |
| `tests/gateway/ws-conformance.test.js` | 15 | RFC 6455 handshake and framing negatives/positives with a raw TCP peer |
| `tests/security/authz.test.js` | 9 | identity, Origin, tickets, session ownership and tenant isolation, replay/ordering, capacity, revocation, secret leakage, injection-as-data |
| `tests/fabric/fabric-ws.test.js` | 7 | policy unit; status/topology; **each of the four VM nodes runs a bundle over the socket**; **fabric run reaches `CROSS_NODE_DIFFERENTIAL_AGREEMENT`** with lossless JSON; denials; capability gating; Ctrl-C + lease release |
| `tests/fabric/lease.test.js` | 3 | slot cap, exclusive build without partial holds, abort, stale reclaim |
| `tests/chaos/lifecycle.test.js` | 12 | failure injection and flow control (see `docs/RECOVERY.md`) including real-process `SIGTERM`/repeated-signal tests and an injected hand-off exception |
| `tests/chaos/review-fixes.test.js` | 9 | one regression test per adversarial-review finding (`docs/SECURITY.md`): pause vs bridge deadline, pause budget, DNS-rebinding Host check, per-principal connection cap, ticket limiter, ping flood, `notAfter` fail-closed + capability removal, prototype-named aliases |
| `tests/desktop-ipc/guard.test.js` | 4 | IPC sender/payload/ownership and navigation policy (pure functions) |
| `tests/ui/client-units.test.js` | 5 | backoff bounds, chunking, clamp, IPC open barrier, holding-queue overflow notice |
| `tests/ui/browser.test.js` | 1 | **real Chromium**: CSP, sign-in (bad then good token), no credential in URL/cookie/storage/DOM, typing incl. non-ASCII, Tab completion, Ctrl-C, multi-line paste order, fabric run, resize, transport loss -> fresh-ticket reconnect as a NEW session, a11y regions, zero console errors. Screenshots in `e/I055/`. |

Interoperability: the gateway's hand-written RFC 6455 endpoint was exercised by three independent peers — Node's built-in (undici) WebSocket, Chromium's, and a raw-socket test peer.

## Accessibility (partial)

Implemented: `role=status aria-live=polite` announcements (connection, exit, bell-class events), a `role=log` text mirror of the visible rows, a focusable text-entry surface (IME, dead keys, on-screen keyboards), visible focus rings, `prefers-reduced-motion`, labelled sign-in dialog. **Not done**: testing with a real screen reader, contrast measurement, keyboard-only tab management audit, mobile browsers. I055 stays IN_PROGRESS.

## Not run (and why)

| Item | Reason | Series status |
|---|---|---|
| PowerShell/.NET gateway, HttpListener matrix | no `pwsh`/`dotnet`; registries refused by egress policy; owner chose Node (D-001) | NOT_APPLICABLE for `NODE-WEB` |
| Docker build / image tests | no Docker daemon, no registry access | BLOCKED |
| Render deploy, staging rehearsal, TLS edge, real WAN | no account authorization; nothing was created | BLOCKED |
| Electron GUI, Windows, packaged `.exe`, BrowserView migration | `npm install` blocked; Linux-only environment | BLOCKED |
| Real identity provider | none selected | BLOCKED |
| Independent review of any item | single implementer | every record is `SELF_REVIEWED` |
| Soak, >8 sessions, memory under sustained fabric load | out of time-box; host-specific anyway | OPEN |
