# Operator and maintainer guide

## Run it locally (loopback)

Requirements: Node.js 20+ (developed on 22). For the fabric: Python 3.10+, and the five DF folders (`DF_Small DF_Medium DF_Large DF_Xtra_Large DF_Fabric`) in one directory, **built once** with `DF_Fabric/BUILD` (C11 compiler + make + OpenSSL; Java for Xtra_Large column-verified compiles).

```text
Windows:  double-click START.cmd            Linux/macOS:  ./start.sh
```

`tools/start-local.js` binds `127.0.0.1:10000`, creates `.vws-local/principals.json` on first run and prints the operator token once, enables snapshots under `.vws-local/snapshots`, and turns the fabric on when it finds `DF_Fabric` in `./df`, the parent folder, or `DF_ROOT`. Open `http://127.0.0.1:10000/`, paste the token, then try `fabric status`, `node small run 01_bell_pair.pal`, `fabric run 02_ghz3.pal --programs replica,bsp`.

Windows was **not tested in this run** (the work was done on Linux). Known differences: Python is looked up as `python`; `taskkill` does not deliver SIGTERM to Node, so use Ctrl+C (SIGINT) for a graceful drain; the DF nodes need their Windows toolchain (`BUILD.cmd`).

## Principals

```text
node tools/mkprincipal.js principals.json alice acme terminal,fabric     # prints the token once, stores only SHA-256
```

Fields: `sub`, `tenant`, `tokenSha256`, `capabilities` (`terminal`, `fabric`), optional `notAfter` (ISO date), `revoked`. The file is re-read when it changes; revoked or expired principals lose live sessions within 30 s. Keep it outside the web root, mode 0600, delivered as a secret file.

## Configuration reference (environment only; malformed values stop startup with exit 78)

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | 10000 when absent | 1..65535; a malformed present value is an error, never replaced |
| `VWS_HOST` | `0.0.0.0` | bind address |
| `VWS_AUTH` | `static-file` | or `none-loopback-dev` (loopback bind only) |
| `VWS_PRINCIPALS_FILE` | — | required for `static-file` |
| `VWS_ALLOWED_ORIGINS` | empty | comma list of exact origins besides same-origin |
| `VWS_ALLOW_NO_ORIGIN` | 1 | native clients (bearer header, no Origin) |
| `VWS_ALLOW_QUERY_TICKET` | 0 | leave off unless every log on the path redacts queries |
| `VWS_SECURE_COOKIES` | 1 | set 0 only for plain-HTTP loopback |
| `VWS_MAX_SESSIONS` / `_PER_PRINCIPAL` | 4 / 2 | admission caps |
| `VWS_MAX_CONNECTIONS_PER_PRINCIPAL` | 4 | sockets (opened or not) one principal may hold |
| `VWS_MAX_PAUSE_MS`, `VWS_WORKER_STDIN_BYTES`, `VWS_WORKER_PENDING_BYTES`, `VWS_BRIDGE_ASSEMBLY_MS` | 120 s, 1 MiB, 4 MiB, 5 s | slow-consumer budget, queued input bound, worker output buffer, bridge record deadline |
| `VWS_FABRIC`, `DF_ROOT`, `VWS_FABRIC_BUILD`, `VWS_FABRIC_SLOTS`, `PYTHON` | 0, —, 1, 2, auto | fabric capability, root, remote build switch, concurrent jobs, interpreter |
| `VWS_SNAPSHOTS`, `VWS_SNAPSHOT_DIR`, `VWS_SNAPSHOT_TTL_MS` | 0, —, 7 d | workspace snapshots |
| `VWS_SHUTDOWN_MS` | 20000 | drain budget; keep below the platform allowance |
| `VWS_SEND_QUEUE_BYTES`, `VWS_ACK_WINDOW_BYTES`, `VWS_MSG_RATE`, `VWS_IDLE_MS`, `VWS_HEARTBEAT_MS`, `VWS_HEARTBEAT_WINDOW_MS`, `VWS_WORKER_*`, `VWS_VFS_*` | see `config/limits.json` | limits and timers |
| `VWS_LOG` | `info` | `debug info warn error silent` |

Public, browser-visible configuration is exactly `GET /config.json` (protocol, paths, auth mode, capability flags, ack/heartbeat hints). Secrets are runtime environment or secret files; nothing is baked into the image, the web assets, the SPIRAL environment or protocol traces. No build-time secret is needed (C45 BuildKit secret mounts: not applicable).

## Health and logs

`GET /health` -> 200 `{"status":"ok"}` when listening and not draining, else 503; unauthenticated, constant work, no redirect. `GET /live` -> process/session counters. Logs are JSON lines on stderr: `gateway.listening ws.accepted ws.rejected session.opened session.exit conn.closed worker.failed worker.unresponsive gateway.draining gateway.stopped`. They never contain tokens, cookies, query strings or terminal bytes.

## Deployment (AUTHORED, NOT EXECUTED)

`deploy/Dockerfile`, `deploy/.dockerignore`, `deploy/render.yaml` were written but **never built or applied**: there was no Docker daemon, no registry access and no Render authorization. Before first use: pin the base image digest, build, run the test suite inside the image, confirm SIGTERM reaches PID 1, measure RSS per session, then set `plan` and `VWS_MAX_SESSIONS`. First deploy, restart, update, rollback and credential rotation rehearsals (I050) are BLOCKED until a staging service is authorized. Do not expose the service publicly before the identity decision (D-005) and those rehearsals.

## Rollback and migration

The candidate is additive: the desktop app still runs from `src/`; removing `gateway/ worker/ client/ web/ protocol/ deploy/` and reverting `src/` to the archived files (hashes in `ledger/source.json`) restores the supplied behaviour. Protocol is v1 only; there is no persisted state to migrate except optional snapshots (`v:1`), which are safe to delete. A future protocol change must be a new subprotocol name negotiated alongside v1.

## Maintainer notes

Run `npm test` (no install needed), `npm run test:ui` with Playwright available (`NODE_PATH` to a global install works), `npm run test:load`, `npm run verify` (hash manifest). Add a command by registering a descriptor; decide explicitly whether it is allowed remotely in `worker/capabilities.js`. Any new process-spawning command needs a policy like `dfabric/policy.js`. Any new envelope field needs a new protocol version.
