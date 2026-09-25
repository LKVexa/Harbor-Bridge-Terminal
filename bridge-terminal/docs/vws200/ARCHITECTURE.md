# HERMIT virtual WebSocket — candidate architecture

Candidate `1.1.0-vws.1`, derived from the supplied `hermit-spiral-terminal_3.zip` (35 files, hashes in `ledger/source.json`) by applying the VWS200 v2.0.0 master prompt and workflow series. Protocol: `hermit.vws.v1`. Evidence classes follow the series: SOURCE, DOCUMENTED, OBSERVED, PROPOSED, UNVERIFIED. Everything in this document that is marked OBSERVED was run in the authoring environment (Linux 6.18, Node v22.22.2, Python 3.11.15, Chromium 1194); nothing here is a production attestation.

## 1. What "virtual WebSocket" means here

An authenticated, bounded, full-duplex terminal carried over standard RFC 6455 WebSockets. The preserved HERMIT VT parser, Screen and CanvasRenderer draw it; the preserved SPIRAL registry, VFS, pipeline and line editor execute it; the attached DF node VMs (`DF_Small`, `DF_Medium`, `DF_Large`, `DF_Xtra_Large`) and `DF_Fabric` are driven through it under an allowlist. It is not a new wire protocol, not an OS PTY and not an arbitrary shell.

## 2. Recorded decisions

| ID | Decision | Owner / date | Consequence |
|---|---|---|---|
| D-001 | **The public gateway host is Node, not PowerShell.** The series baseline is a `pwsh`/HttpListener gateway. The authoring environment had no `pwsh`, `dotnet` or Docker daemon and its egress policy refused `packages.microsoft.com`, `mcr.microsoft.com`, `api.nuget.org` and the npm registry (403), so the I008 HttpListener feasibility gate could not be run. The owner selected "Node only" on 2026-09-21. | D. P. Russell, 2026-09-21 | Protocol, bridge framing, admission order, limits and lifecycle are implemented exactly as specified so a PowerShell gateway can be added later with parity. PowerShell/.NET-specific source components are dispositioned NOT_APPLICABLE for profile `NODE-WEB` (see `ledger/dispositions.jsonl`); they are not deleted or rewritten. ALT01/ALT02 remain inactive. |
| D-002 | **Remote sessions may drive the DF nodes and fabric through an allowlist.** The series default is "virtual commands only, no process execution". The owner selected "allowlisted run + verify" on 2026-09-21. | D. P. Russell, 2026-09-21 | `src/main/spiral/dfabric/policy.js`: fixed interpreter, fixed `adapter/dfabric/cli.py`, operator-bound `DF_ROOT`, argv rebuilt from validated tokens, bundle names from discovery only, no host-path options, allowlisted child environment, deadlines, cross-process concurrency lease, host paths redacted, per-principal `fabric` capability. `build` is operator-switchable (`VWS_FABRIC_BUILD`). Photon delegation and the browser pane are never installed remotely. |
| D-003 | **One supervised worker process per session** (series default). | series | Natural VFS/env/history separation between tenants (F02), per-session kill for non-cooperative CPU (F17). Not an OS sandbox: no untrusted plugins. |
| D-004 | **Single-instance profile; stream resume disabled** (`resume=false`). Reconnect = new session with fresh authentication. Optional quiescent workspace snapshots are per principal and off by default. | series + candidate | C05 shared datastore and I039 leases/fencing are NOT_APPLICABLE until a multi-instance profile is selected. |
| D-005 | **Identity is a seam, not a provider.** Adapters: `static-file` (hashed bearer tokens, operator file, hot revocation) and `none-loopback-dev` (refused off-loopback). No issuer, audience or key material is invented. | candidate | An OIDC/JWT adapter is BLOCKED until the owner selects a provider. |
| D-006 | **Browser admission = one-use ticket in an HttpOnly, SameSite=Strict, path-scoped cookie.** Query tickets stay disabled unless the operator asserts log redaction (`VWS_ALLOW_QUERY_TICKET`). Native clients use an `Authorization` header and must not send `Origin`. | series + candidate | No credential ever appears in a WebSocket URL or subprotocol (OBSERVED in Chromium, `tests/ui/browser.test.js`). |
| D-007 | **Text frames only; terminal bytes are canonical base64.** Binary frames close 1003. No WebSocket extensions are negotiated (no compression state). | series | 1.333x payload expansion, measured throughput in `docs/RESOURCE_MODEL.md`. |

## 3. Profiles

| Profile | Client | Shell location | State |
|---|---|---|---|
| LOCAL | Electron renderer + `client/ipc-adapter.js` | Kernel in the Electron main process | Code changed and unit-tested without Electron; **Electron GUI not run here** (BLOCKED: no Electron install possible). |
| WEB | `web/index.html` + `client/ws-adapter.js` in any browser | Headless worker behind `gateway/server.js` | OBSERVED end to end in Chromium, including a four-node fabric run. |
| REMOTE-DESKTOP | Electron renderer using the WebSocket adapter | Same as WEB | Not wired: `boot.js` selects IPC whenever the preload bridge exists. OPEN. |

## 4. Topology

```text
HERMIT VT parser + Screen + CanvasRenderer          (src/renderer/vt, preserved + hardened)
                 |
        TerminalTransport contract                    client/transport.js
        /                         \
IpcTransport (LOCAL)               WsTransport (WEB)  client/ipc-adapter.js, client/ws-adapter.js
   Electron preload                      |  wss://  hermit.vws.v1 (JSON text, base64 terminal bytes)
   ipc-guard.js                          v
                               gateway/server.js   0.0.0.0:$PORT
                 /health /live /config.json /api/ws-ticket /ws/terminal  static web client
                 path -> draining -> Origin -> RFC 6455 -> identity -> capacity -> upgrade
                               gateway/ws.js        one receive path, one ordered send path
                               gateway/connection.js   state machine, flow control, heartbeat, supervisor
                                         |  uint32-BE length + UTF-8 JSON records (protocol/bridge.js)
                                         v
                               worker/host.js       one process per session, no Electron import
                               SpiralKernel + VFS(quota) + Registry(filtered) + OutputGate
                                         |  spawn(shell:false), fixed python + cli.py, vetted argv
                                         v
                  DF_Fabric  ->  N_SMALL  N_MEDIUM  N_LARGE  N_XLARGE     (operator-bound DF_ROOT)
```

The gateway owns HTTP routing, admission, identity, session mapping, networking, cancellation, health and worker supervision. The worker owns shell parsing/execution and the virtual workspace. No socket object crosses the process boundary; worker input is structured records, never evaluated text. The worker executable and entry path are fixed constants.

## 5. Source map (what existed, what is new)

| Area | Supplied source | Candidate change |
|---|---|---|
| VT engine `src/renderer/vt/*` | parser, screen, canvas renderer | OSC/CSI bounds, true ST handling, count clamps, scrollback bound on resize, geometry clamp. Renderer-canvas untouched. |
| Renderer `src/renderer/renderer.js` | called `window.spiral` directly | depends on `window.HermitTransport`; open barrier; capability-gated chrome; IME/text-entry surface; bounded paste; accessible status + text mirror. |
| Kernel `src/main/spiral/*` | sessions, REPL, pipeline, VFS, commands, DF + Photon commands | geometry validation; single exit path; settle reader on close; `deferStart`/`startSession`; bounded captures, lines, history, `seq`, regex; type-ahead; VFS quotas, byte-safe append, snapshots; policy-aware DF commands; command-boundary backpressure. |
| Electron main/preload | unvalidated IPC, permissive navigation | sender/payload/ownership gate; deny-by-default navigation and permissions; packaged adapter discovery. |
| Absent in source | WebSocket server, auth, protocol, worker, web page, deployment files | `gateway/`, `worker/`, `protocol/`, `client/`, `web/`, `deploy/`, `tests/`, `tools/`. |

The README's "VB-JA21 v9.8.7" browser engine is **not** in the archive (only `vendor/browser/README.md` and an example). The pane reports `HERMIT-Fallback/Chromium` and `engineSource: builtin-fallback`; nothing claims a VB-JA21 engine (F15).

## 6. Repository split

`gateway/ worker/ protocol/ client/ web/ src/main/spiral/ src/renderer/` form the hosted build and have **zero third-party runtime dependencies** (Node standard library only), so there is no lockfile to drift and nothing to `npm install` in the image. Electron and electron-builder remain desktop-only devDependencies with caret ranges and **no lockfile** (F14): a reproducible desktop build is OPEN until `npm install` can run and a lockfile is committed. `package.json` `build.files` now includes `client/**` and `protocol/**`, which the desktop page loads.
