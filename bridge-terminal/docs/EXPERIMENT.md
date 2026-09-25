# Preregistered CPU and fidelity experiment (kit R28)

Configuration: `e/R28/experiment.frozen.json`, frozen before data collection; the harness refuses to run otherwise. Harness: `tests/load/experiment.js` (a separate client process; its CPU is excluded). Host: 2 vCPU Intel Xeon 2.80 GHz, Linux 6.18, Node v22.22.2, loopback, no TLS, no compression. Arms are separate gateway processes started from their own directories; arm order randomized per launch; 2 warm-up + 10 warmed runs per launch; 3 independent launches per arm; cluster bootstrap over launches (10 000 resamples). **One host, three clusters: the intervals are narrow only because run-to-run noise on this idle host is small; they say nothing about other hosts.**

Baseline: `hermit-vws 1.1.0-vws.1` — hermit.vws.v1, JSON + base64 data, worker process per session, output acks. Candidate: `hermit-ramws 2.0.0-ramws.1` — hermit.vws.v2, binary frames, worker thread per session with transferred buffers, byte credits, allocation ledger.

## Main result (`e/R28/result.json`)

CPU-seconds of the server process tree per completed unit; reduction = (baseline − candidate) / baseline; 95 % cluster-bootstrap interval; gate H2 requires the lower bound > 5 %.

| Workload | Unit | Baseline (per-launch means) | Candidate | Reduction | 95 % CI | H2 |
|---|---|---|---|---|---|---|
| W1 interactive (300 awaited keystrokes) | one echoed keystroke | 0.41 / 0.43 / 0.41 ms | 0.23 / 0.24 / 0.24 ms | **42 %** | 40.5–44.7 % | SUPPORTED |
| W2 bulk output (~2.9 MB) | one MiB delivered | 146 / 151 / 146 ms | 50.0 / 48.2 / 45.8 ms | **67 %** | 66.1–69.0 % | SUPPORTED |
| W3 3000-character paste | one paste | 713 / 723 / 717 ms | 6 / 6 / 5 ms | **99 %** | 99.2–99.3 % | SUPPORTED |

Non-inferiority: keystroke echo p50 0.21–0.27 ms → 0.035–0.037 ms (better); bulk 7.8–8.2 MiB/s → 27.5–28.3 MiB/s (better). Fidelity: all 60 runs delivered exactly 400 000 lines (`exact`); no run excluded. Residency observation: 0 major faults in the gateway process over every launch (interval observation, gateway scope only; the baseline's worker processes are outside this counter).

## Ablation: same protocol, process backend (`e/R28/result.process-backend.json`)

Separates the protocol change from the backend change. Candidate = v2 with `VWS_WORKER_BACKEND=process`.

| Workload | Reduction vs baseline | 95 % CI | H2 |
|---|---|---|---|
| W1 | **−6 %** (worse than v1; earlier runs: −13.5 % before the descriptor optimisation, 0.5 % before the review-2 fixes) | −10.3 – −2.0 % | NOT_SUPPORTED |
| W2 | **19 %** (earlier runs: 29 %, 31 %) | 17.6–20.2 % | SUPPORTED |
| W3 | **99 %** | 98.9–99.0 % | SUPPORTED |

Candidate/process latency p50 0.06–0.09 ms, throughput 13.9–14.7 MiB/s, fidelity exact.

Reading: with the process backend, the v2 protocol alone roughly halves the bulk-output cost of v1 (no base64 on the socket side, single-copy framing) and eliminates the paste cost, but the per-keystroke path was initially *more* expensive than v1: the per-operation descriptor admission (a structural schema walk of a descriptor the server had just built itself) and the pipe hop dominated. The structural walk was then skipped for server-built descriptors (runtime checks retained — ownership, epoch, plan identity, lease resolution, extents, budget), which is the only optimisation made after seeing data; the first results are preserved in `e/R28/pre-optimisation/`. The thread backend removes the pipe hop entirely, which is where most of W1's 42 % comes from.

## Runs and re-runs (all preserved)

The frozen configuration never changed; the candidate did, twice, after data had been seen, and the experiment was re-run in full each time:

| Run | Candidate state | Main W1 / W2 / W3 | Ablation W1 / W2 / W3 | Kept at |
|---|---|---|---|---|
| 1 | as first built | 46 % / 71 % / 99 % | −13.5 % / 29 % / 99 % | `e/R28/pre-optimisation/` |
| 2 | + trusted-shape descriptors | 46 % / 71 % / 99 % | 0.5 % / 31 % / 99 % | `e/R28/pre-review2/` |
| 3 (before coalescing) | + review-2 fixes (bounded in-flight output, `consumed` record per chunk) | 33 % / 67 % / 99 % | −29 % / 18.5 % / 99 % | figures in this table only (`e/R28/experiment.*.log` were overwritten by run 4) |
| **4 (reported)** | + `consumed` records coalesced per event-loop turn | **42 % / 67 % / 99 %** | **−6 % / 19 % / 99 %** | `e/R28/result*.json` |

The review-2 fixes (`docs/SECURITY.md`, "Second review") cost CPU on purpose: the worker's in-flight output is now bounded and every chunk's consumption is reported back, which is one more message per chunk on the process backend's pipe. Coalescing recovered most of it on the thread backend (33 → 42 %) and some on the process backend (−29 → −6 %). The process backend is therefore **not** recommended for keystroke-dominated sessions; it remains as the ablation and as the alternative for hosts where a per-worker heap cap cannot be enforced.

## Attribution (kit: name the eliminated work, do not say "zero-copy")

| Removed or reduced work | Where | Affects |
|---|---|---|
| base64 encode/decode + JSON parse per data message on the socket | v2 binary frames | W1, W2 |
| base64 + JSON + pipe write/read per message between gateway and worker | thread backend transfers `ArrayBuffer`s | W1, W2 |
| one concatenation copy per outbound message | header and payload written under cork | W2 |
| one repaint of the whole input line per pasted character | line reader batches printable runs | W3 (an algorithmic fix; RAM-neutral) |
| building the whole `seq` output as one string | streaming batches with cooperative `yield()` | W2 memory (not CPU) |
| an output-ack JSON message per output message from the client | credits renewed per ¼ window or 128 messages | W2 |
| structural schema walk per server-built descriptor | trusted-shape marker | W1 (after ablation) |

Nothing here moves computation into memory. The remaining CPU is the actual work: TCP, WebSocket framing, UTF-8, the shell, the VT redraw sequences.

## Gates (kit VALIDATION Table)

| Gate | Result |
|---|---|
| G0 protocol/security | PASS on this host: 127/127 tests incl. 15 raw-socket conformance, isolation, credit and reset tests. Repeated clean-room runs (9) found one intermittent failure, in the *test client* (a quadratic `Buffer.concat` inflated an in-process latency measurement; the gateway's own event-loop delay, measured in a separate process, stayed ≤ 13 ms); the client was fixed, the assertion was not loosened |
| H1 capacity model | **NOT RUN as specified**: the ledger's predicted charge vs. observed RSS was not compared at the 10 % level; `s` is a reservation, RSS is an overlapping view |
| H2 CPU benefit | SUPPORTED for W1–W3 on this host (lower bounds 40.5 %, 66.1 %, 99.2 %) |
| H3 fidelity | PASS (exact in all runs) |
| H4 traffic model | NOT RUN: software copy counts exist (`/live`), no hardware counter to compare against |
| H5 residency | interval observation only (0 major faults, gateway scope); `RESIDENCY_VERIFIED` is **not** claimed |

Status words (kit): PACKAGE_VERIFIED ✔ · IMPLEMENTATION_TESTED ✔ (this host) · DEPLOYMENT_TESTED ✘ · RESIDENCY_VERIFIED ✘ · CPU_BENEFIT_SUPPORTED ✔ (this host, these workloads, versus the previous candidate).
