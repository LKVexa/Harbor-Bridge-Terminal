# Security: threat model, controls, evidence

Scope: the WEB profile (gateway + worker + browser client) and the LOCAL desktop IPC surface. Self-reviewed by the implementer; **no independent security review has taken place**.

## Assets and trust boundaries

| Boundary | Untrusted side | Trusted side |
|---|---|---|
| Internet -> gateway | every HTTP request, WebSocket frame, Origin header, cookie | admission logic, identity adapter |
| Browser page -> terminal stream | all `terminal.output` bytes (they come from commands and DF CLIs) | VT parser state, DOM, clipboard, title |
| Gateway -> worker | — (structured records only) | worker entry path, environment allowlist |
| Worker -> DF CLIs | user tokens after `fabric`/`node` | fixed interpreter + script, vetted argv, `DF_ROOT` |
| Electron renderer -> main | IPC payloads, any non-owned frame | kernel, browser pane, window |

Assets: bearer tokens and the principals file; other tenants' workspaces and output; the host filesystem and process table; service availability; the operator's DF containers.

## Controls and where they are proved

| Threat | Control | Evidence (OBSERVED) |
|---|---|---|
| Unauthenticated use | identity before upgrade; no default credential; `none-loopback-dev` refused off-loopback | `authz.test.js` "no credential…" |
| Forged Origin | exact-match allowlist; Origin never substitutes for identity; suffix/`null` refused | "Origin: unlisted…" |
| Credential in URL/logs | header or HttpOnly cookie only; query refused; logger drops secret-like fields and query strings | browser test (URL, `document.cookie`, storage, DOM); "secrets and host details…" |
| Ticket theft/replay | 256-bit, SHA-256 verifier only, 30 s, one use, Origin + principal bound, consumed even on a failed presentation, path-scoped cookie cleared on upgrade | "ticket: issued only…" |
| CSRF on ticket endpoint | credential is a header (not ambient); exact Origin check; CORS allowlist; `SameSite=Strict` | same |
| Cross-tenant session access | per-connection `sid` ownership; identical `FORBIDDEN` for foreign and unknown ids; one kernel per process | "session ids authorize nothing…" (no injected bytes, no shared `/tmp`) |
| Replay / reordering | `rid` window, strict input `seq`, epoch fence | "stale epoch, replayed rid…" |
| Resource exhaustion | caps on message, fragment total, queue, ack window, rate, sessions, VFS bytes/nodes, captures, line, history, `seq`, regex, scrollback, OSC, CSI | `ws-conformance`, `lifecycle`, `kernel`, `vt` tests |
| Non-cooperative CPU (catastrophic RegExp) | supervisor ping; SIGKILL of that worker only | "non-cooperative CPU loop…" contained in < 5 s, other tenant served |
| Command/argument injection into DF CLIs | `spawn(shell:false)`; argv rebuilt from enums/ints/discovered names; host-path options refused | `fabric-ws.test.js` policy unit + "denied…" (no `/tmp/pwn.json`) |
| Shell substitution reaching the host | SPIRAL has no `$(…)`/backtick execution and no OS shell | "terminal-escape and command-injection text is data" |
| Secret leakage into the shell | worker env is an allowlist; kernel env is synthetic; snapshots deny `TOKEN/SECRET/KEY/VWS_/VEC1_` | "secrets and host details…" |
| Host path disclosure | DF root shown as `$DF_ROOT`; CLI output redacted line-wise | fabric tests assert the absolute path never appears |
| Hostile terminal output | bounded parser; only OSC 0/2 (title, stripped, 256 chars); no OSC 52 clipboard, no hyperlinks, no queries answered; count clamps | `vt.test.js` incl. fuzz |
| Static file traversal | exact-key map of served files; nothing computed from the request path | `e2e.test.js` (404 for traversal and for `/gateway/server.js`) |
| Clickjacking / injection in the page | CSP `default-src 'none'`, `script-src 'self'`, `frame-ancestors 'none'`, nosniff, COOP/CORP; no inline script | browser test: zero console/CSP errors |
| Desktop IPC abuse | top-frame + file URL + webContents check, exact payload shapes, session ownership; pane navigation/permissions deny-by-default | `desktop-ipc/guard.test.js` (pure functions; Electron itself not run) |
| Revoked user keeps a session | principals file re-read on change; 30 s sweep ends live sessions (`expired`, 1008) | "revocation ends a live session…" |

## Residual risks (accepted or open)

1. The worker is **not an OS sandbox**. It runs as the gateway's user. A Node or Python vulnerability, or a malicious DF container, reaches that user's privileges. Run the service as an unprivileged user in a container with a read-only root where possible; never enable untrusted plugins.
2. `fabric verify`/`run` write run records under the DF containers' `_runs/` directories and `build` rewrites build products. They are shared by all fabric-capable principals. Grant `fabric` only to operators you would let run those CLIs locally.
3. DF CLI JSON includes host platform, Python version and CPU count (its own provenance block). Visible to fabric-capable principals.
4. `static-file` identity has no MFA, rotation workflow or audit trail. It suits a single operator; it is not a multi-tenant identity provider.
5. TLS is expected from the platform edge. The gateway speaks plain HTTP; `VWS_SECURE_COOKIES=1` (default) requires HTTPS at the browser. Direct exposure without TLS is unsupported.
6. `X-Forwarded-Proto` is trusted for same-origin computation. Behind an edge that does not overwrite it, set `VWS_ALLOWED_ORIGINS` explicitly.
7. Wide/combining characters occupy one cell each; this is a rendering limitation, not a security control.
8. No dependency audit is needed for the hosted build (no dependencies); the desktop build has no lockfile (OPEN).

## Review findings (adversarial pass, same run)

A second, adversarial reviewer (an AI subagent with no authoring role; **not** a human or organisationally independent review) read the network-facing code and ran reproductions. One defect was confirmed by execution, the rest were reasoned. All were fixed and have regression tests in `tests/chaos/review-fixes.test.js`.

| # | Finding | Fix |
|---|---|---|
| C1 (confirmed, medium/high) | Backpressure pause usually lands mid-record; the bridge assembly deadline kept running while the gateway itself had stopped reading, so any consumer slower than 5 s lost its session as a false `worker_failure`. | `FrameDecoder.pause()/resume()`; the deadline only runs while the stream flows. Orderly end while paused resumes the pipe and discards late output. |
| S1 | With `none-loopback-dev`, same-origin was derived from `Host`, so a DNS-rebinding page could be admitted. | In that mode every route and the upgrade require a loopback `Host` literal (421/403 otherwise). |
| S2 | Ticket rate limit counted all POSTs per address before authentication (a shared edge address could lock everyone out) and reset globally at 4096 entries. | Failures per address and issues per principal are limited separately; oldest-entry eviction. |
| S3 | Connection cap was global only. | `VWS_MAX_CONNECTIONS_PER_PRINCIPAL` (4). |
| S4 | Pong replies bypassed the send budget; control frames were not rate limited. | Pongs respect budget + reserve; > 200 control frames/s closes 1008. |
| S5 | Worker supervision was suspended while paused; gateway->worker input was unbounded. | Pause budget `VWS_MAX_PAUSE_MS` (120 s) ends the session with `quota`; `VWS_WORKER_STDIN_BYTES` (1 MiB) bounds queued input. |
| S6 | A snapshot near 60 000 bytes could exceed one bridge record after JSON escaping. | Worker measures the final record; gateway falls back to a clean open. |
| S7 | Malformed `notAfter` parsed to `NaN` and never expired (fail-open); capability removal did not reach live sessions. | Invalid dates reject the file; `stillValid` requires every held capability to still be granted. |
| S8 | Path redaction missed the realpath form and long no-newline output. | Both root forms are redacted; a tail of root length is carried across chunk boundaries. |
| S9 | `aliases` was a plain object; `constructor`/`toString` names could throw inside the input handler and end the worker. | Null-prototype map; the input handler is guarded. |

Reviewer found nothing in: static-file authentication/ticket/Origin bypass, capability bypass or DF argument smuggling (argparse abbreviations, `=` forms, dash-leading values and path-like bundles are all refused), secret leakage to logs/env, snapshot restore abuse, or session state-machine ordering.
