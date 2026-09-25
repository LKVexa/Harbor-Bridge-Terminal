# Resource model and measurements

Limits are in `config/limits.json` (machine-readable) and enforced in code; every one has a test that hits the boundary. They are the series' PROPOSED starting values plus four this candidate needed (`ackWindowBytes`, `workerPendingOutputBytes`, pipeline capture, `seq` items).

## Per-session memory bound (gateway side)

```text
gateway_session_peak <= receive assembly (65 536)
                      + socket send queue (524 288 + 16 384 control)
                      + pending envelopes while paused (<= a few 21 848-char records; the worker pipe is not read while paused)
                      + ack bookkeeping (one small Map entry per un-acknowledged output record)
worker_session_peak  <= Node baseline RSS (measured below)
                      + VFS content (16 MiB) + output gate (4 MiB) + one pipeline capture (1 MiB chars, UTF-16 => <= 2 MiB)
                      + DF CLI child processes while a fabric job runs (not measured here; bounded in count by the lease: 2)
```

`admission_limit <= floor((approved_memory - gateway_base - margin) / worker_session_peak)`. With the measured 55 MiB idle worker and the 22 MiB of per-session quotas above, a conservative planning figure is **~80 MiB per session** before any fabric job. `VWS_MAX_SESSIONS` stays at 4 until the target host is measured.

## Measured (OBSERVED, loopback, this host only)

Host: 2 vCPU Intel Xeon 2.80 GHz, Linux 6.18, Node v22.22.2. Raw output: `e/I053/bench.json`; harness: `tests/load/bench.js`. One run; treat spread as indicative.

| Workload | Result |
|---|---|
| W1 keystroke echo round trip, 300 samples | p50 0.69 ms · p95 1.67 ms · p99 3.96 ms · max 4.91 ms |
| W2 bulk output, 6 182 393 raw bytes, acknowledged | 1.41 s -> 4.19 MiB/s raw (wire >= 1.333x because of base64) |
| W3 8 concurrent sessions | open p50 52 ms, max 71 ms · worker RSS 55.1–55.2 MiB each · gateway RSS 83 -> 90 MiB (includes the harness and its 8 clients) |
| Fabric run `01_bell_pair.pal`, 4 nodes, via browser | verdict in ~0.7 s wall (CLI-reported) |
| Drain on SIGTERM, real process, 3 sessions (idle / each running `sleep 300`) | exit 0 in 20 ms / 15 ms wall; every client got `service.draining`, `session.exit{shutdown}`, close 1001 (`e/I049/drain-measure.json`) |
| Non-cooperative worker containment | killed and reported in < 5 s with 150 ms ping / 900 ms stall settings (defaults 5 s / 15 s) |

Not measured: WAN latency, TLS edge, the target container, memory under sustained fabric load, many-hour soak, more than 8 sessions. Those remain I053 BLOCKED items for the deployed profile.
