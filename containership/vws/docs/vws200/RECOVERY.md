# Liveness, reconnect, snapshots, retention, shutdown

## Liveness (I036)

Three separate signals, never conflated:

| Signal | Mechanism | Failure action |
|---|---|---|
| Transport | RFC 6455 Ping answered with Pong (server side); TCP close/error | connection released |
| Application | server `heartbeat.ping` every 20 s, 10 s window; client may ping too | close 1008, `session.exit{expired}` — OBSERVED |
| Worker | bridge `ping` every 5 s; no `pong` for 15 s while not paused | SIGKILL that worker, `session.exit{worker_failure}`, close 1011 — OBSERVED with a catastrophic RegExp |

A paused worker (backpressure) is not treated as stalled. Idle sessions end after `VWS_IDLE_MS` (30 min). Browser tab suspension can delay pongs; the 10 s window is a starting value.

## Reconnect (I037)

Client policy (`client/ws-adapter.js`): full jitter `uniform(0, min(30 s, 0.5 s * 2^attempt))`, one timer, max 8 attempts, cancelled by explicit close, no retry after policy closes (1002/1003/1007/1008/1009) or a 401/403 ticket refusal. Every attempt obtains a **fresh ticket**. A reconnect opens a **new session**; the terminal prints that fact. Raw keystrokes and command text are never replayed. Input messages without a `request.ack` when the link dropped are counted and reported as **outcome UNKNOWN**. OBSERVED in Chromium (`03-reconnected.png`).

## Quiescent snapshots (I038, I040) — optional, off by default

`VWS_SNAPSHOTS=1 VWS_SNAPSHOT_DIR=…`. On an orderly end (client close, drain, idle, network loss) the gateway asks the worker for a snapshot; the worker refuses while a command is running. Saved: VFS tree byte-exact (strings and Buffers keep their kind), cwd, aliases, shell variables not matching the deny pattern, optionally the last 200 history lines. Never saved: sockets, promises, the running command, the input line, service environment, tokens. Record: SHA-256 over the body, <= 60 000 bytes, one file per (tenant, principal) named by a hash, mode 0600, atomic rename, TTL (7 days default). Restore validates integrity, shape, names, depth and quotas into a detached tree before swapping; any failure starts clean and says so. The restored terminal states: *workspace restored … this is a NEW session — no command was resumed*. OBSERVED: restore, per-principal separation, tamper rejection.

## Retention

| Data | Where | Lifetime |
|---|---|---|
| Terminal output | browser scrollback only (5000 rows / 2 M cells) | tab lifetime; never stored server-side |
| Session workspace | worker memory | session lifetime; lost on instance replacement unless snapshots are on |
| Snapshots | `VWS_SNAPSHOT_DIR` | TTL; on an ephemeral filesystem they disappear with the instance — mount persistent storage or accept the loss |
| DF run records | `DF_*/_runs/` written by the DF CLIs | operator-managed |
| Logs | stderr JSON lines; no payloads, tokens, cookies or query strings | platform-managed |

Multi-instance continuity (shared store, leases, fencing: C05, I039) is NOT_APPLICABLE to this single-instance profile.

## Shutdown (I049)

`SIGTERM`/`SIGINT` handlers are registered before `listen`. Sequence: `draining=true` (`/health` 503, tickets 503, upgrades 503) -> `service.draining{deadlineMs,reason}` to every connection -> per session: snapshot if enabled and quiescent, `close` record, worker exits or is killed after 1.5 s -> ordered `session.exit{shutdown}` -> close 1001 -> when the last connection is gone, close the listener and exit 0. A hard timer at `VWS_SHUTDOWN_MS` (20 s) kills remaining workers, terminates sockets and exits 1. Keep the platform allowance above that budget (`maxShutdownDelaySeconds: 30` in the Blueprint). Node runs as PID 1 via exec-form `ENTRYPOINT`, so no shell intercepts the signal. OBSERVED on a real process: see `docs/RESOURCE_MODEL.md`.

## Failure experiments run (I054)

worker SIGKILL · event-loop stall · abrupt TCP loss (worker reaped, no orphan) · heartbeat silence · open deadline · unacknowledging client · TCP peer that stops reading · oversized in-process producer · snapshot tamper · SIGTERM with idle and busy sessions · malformed `PORT` (exit 78). Not run: store failure, multi-instance replacement, real network partitions, hosted restarts.
