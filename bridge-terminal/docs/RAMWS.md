# RAMWS candidate — what "RAM-resident virtual WebSocket" means here

Candidate `2.0.0-ramws.1`, built by applying the RAMWS v1.0.0 kit (SHA-256 `4bf7b67e…`) to `hermit-vws 1.1.0-vws.1` (`db65b5e3…`). Kit evidence classes are used throughout: SOURCE (in the kit or the inputs), ADAPTATION (new design in this candidate), OBSERVED (run here), UNVERIFIED / NOT_RUN.

## The claim, and what it is not

The request was a "silicon processing web socket". The kit's own boundary (A01 Part 1, MASTER_PROMPT) is the one this candidate keeps: **ordinary RAM stores data; the CPU, runtime and OS execute everything.** This candidate does not relabel DRAM as a processor, does not claim zero CPU, and does not claim physical residency. What it does claim, with evidence, is the kit's deployable interpretation:

1. every retained byte of **session, payload and transport** state lives in **bounded, ledgered process RAM** — none of it is spilled to disk, by policy and by code (the previous candidate's disk snapshots were removed). The one thing the service still writes to disk is not session state: the DF fabric capacity lease (`worker/fabric-lease.js`) creates tiny slot directories under a temp path so that concurrent fabric jobs across sessions can be counted; it holds a pid, never user data, and is reclaimed on release or when the owner dies;
2. **avoidable processor work was removed** — base64, JSON-per-keystroke, per-character screen repaints, whole-output string construction, pipe serialization and copies — and the reduction was **measured** in a preregistered experiment against the previous candidate (`docs/EXPERIMENT.md`);
3. every admission decision is made by a **reservation controller** that charges each distinct allocation once, before the memory is acquired, and returns it exactly once after its last consumer completes.

## Decisions (approved by the owner on 2026-09-21)

| ID | Decision |
|---|---|
| RD-01 | Profile **LOCAL_VOLATILE** (kit default). Process loss loses sessions; the client is told so with `session.reset` and an exact count of inputs with unknown outcome. `VWS_PROFILE` other than LOCAL_VOLATILE, and any snapshot setting, is a startup error (exit 78), never a silent fallback. |
| RD-02 | Protocol **hermit.vws.v2 only**; v1 is no longer offered (a v1 client is refused at the handshake, 400). Control messages stay strict JSON text; terminal bytes are binary WebSocket messages with a 7-byte header (`kind`, `uint48 seq`). |
| RD-03 | Gateway host remains **Node** (inherited decision D-001). The kit's PowerShell/.NET items stay NOT_APPLICABLE for this profile; the kit's HttpListener probe (R05 part) is NOT_RUN for the same reason as before (no `pwsh`, registries blocked). |
| RD-04 | Worker boundary: **one worker thread per session** (`VWS_WORKER_BACKEND=thread`, default) with an **enforced V8 heap cap** and transferred output buffers; the process backend is retained and tested as an alternative (`process`). |
| RD-05 | Flow control: **client byte credits** (kit CREDIT), cumulative and window-bounded, replace v1's output acknowledgements; `input.ack` distinguishes ACK_ACCEPTED (`acceptedSeq`) from ACK_EXECUTED (`executedSeq`). |

## Eight descriptor fields and six invariants — where each lives

| Kit element | Implementation | Evidence |
|---|---|---|
| Operator · Buffers · Formats · Budget · Ownership · Completion · Quality · Backend | `ram/descriptor.js` builds every descriptor from server state; `ram/descriptor.schema.json` is the kit's schema byte-for-byte | 13/13 kit fixtures give the kit's verdict (`tests/ram/descriptor.test.js`) |
| Budget | `ram/ledger.js`: session → tenant → global checked and committed together, synchronously; capacity (not length) is charged; pool slabs counted once globally | `tests/ram/ledger.test.js` incl. 4000-step randomized reconciliation |
| Lifetime | `Lease.retain()/release()`: capacity returns on the last consumer; socket writes release in the write **callback**; duplicate release is counted, never refunded | ledger tests; `e2e` "ledger returns to zero" for both backends |
| Aliasing | views add references, not capacity; `reserveCapacity()` charges quota without physical bytes; thread backend **transfers** output buffers (`bridge_out_transfer`) while the process backend copies (`bridge_out_copy`) — both counted in `ram/traffic.js` | `/live` → `ram.traffic` |
| Quality | exact bytes end to end; no base64; incremental UTF-8; output seq contiguous; a credit-starved session pauses instead of dropping; `seq`, captures and the line reader are bounded and stream | W2 fidelity `exact` in all 60 experiment runs; 150 000/200 000-line lossless catch-up tests |
| Transparency | `/live` exposes the plan, ledger, pool, traffic estimates, counters (`sessionResets`, `workerHeapCapHits`, `undeliveredOutputBytes`, `memoryRefusals`) and `heapCap: ENFORCED / UNENFORCED / UNKNOWN`; residency is `UNKNOWN` unless observed | `tests/gateway/e2e.test.js`, `tests/ram/v2-e2e.test.js` |
| Validity | plan identity = hash(code version, protocol, descriptor schema, policy generation, backend, **server epoch**, profile); a policy change or restart invalidates every cached plan and handle | `tests/ram/descriptor.test.js` |

Lifecycle `CREATED → VALIDATED → RESERVED → ACTIVE → DRAINING → COMPLETED → RELEASED` (`REJECTED`/`FAILED` terminal) is enforced by `Operation._to()`; illegal transitions throw.

## Memory plan (kit R06) — enforced, not just planned

`ram/allowance.js`: `L` = smallest finite boundary found (explicit `VWS_MEMORY_LIMIT_BYTES`, cgroup v2 `memory.max`, cgroup v1 limit; installed RAM only as a labelled weak fallback), `F` = gateway RSS at startup (or configured), `G` = pool idle allowance, `H` = headroom, `s` = per-session reservation = transport buckets + worker reservation. `ceiling = floor((L−F−G−H)/s)`; the admitted session cap is `min(configured, ceiling)`. The ledger's global allowance is `L−F−G−H`; a connection is admitted (transport reservation) **before** the 101, a session (worker reservation) **before** the worker exists; refusals are 503 / `LIMIT_EXCEEDED` and allocate nothing. OBSERVED: with `L = F + 2s + 64 KiB` exactly two sessions are admitted, the third is refused before upgrade, and capacity returns on close.

Per-session reservation on this host (thread backend, defaults): worker heap cap 48 MiB + measured 12 MiB thread overhead + VFS 4 MiB + output workspace 2 MiB + transport ≈ 1.4 MiB ≈ **67.4 MiB**. The V8 cap is the enforced upper bound on strings the VFS/history/captures hold; the quotas beneath it are earlier, softer limits.

**Heap-cap caveat (OBSERVED):** a process-wide `--max-old-space-size` (typically via `NODE_OPTIONS`) silently overrides per-worker `resourceLimits`. The gateway probes this at startup and refuses to start (`EHEAPCAP`, exit 78) unless `VWS_REQUIRE_HEAP_CAP=0`, in which case `/live` reports `heapCap: UNENFORCED`. The process backend passes its own `--max-old-space-size` and is unaffected.

## What crosses which boundary (kit R08, R18)

| Path | v1 (baseline) | v2 (candidate) |
|---|---|---|
| keystroke, client → gateway | JSON text + base64 (≈120 B/byte) | 7-byte header + raw bytes, unmasked in place, one owned copy |
| gateway → worker | framed pipe, base64 again, second address space | thread: `postMessage` with a transferred `ArrayBuffer` (no copy) |
| worker → gateway output | base64 → pipe → decode | transferred `ArrayBuffer`; gateway sends header + payload as two writes under cork (no concatenation) |
| gateway → client | JSON + base64, ack per message | binary frame; credit renewals every ≥¼ window |
| worker in-flight output | unbounded pipe buffer | bounded by `VWS_WORKER_PENDING_BYTES`; the gateway reports consumption back per event-loop turn (`consumed`) |
| a 3000-character paste | 3000 repaints ≈ 4.3 MB of output | one repaint ≈ 6 KB |

All of these are *software* copy counts (`ram/traffic.js`); hardware traffic was not measured.

## Not done / not claimed

- No PIM, accelerator or "compute in memory" of any kind (kit PIM_RESEARCH disabled). No page locking, no swap control, no crash-dump control.
- Residency: `ram/residency.js` observed **0 major faults** over every experiment launch for the gateway process — an interval observation on one host, not a guarantee.
- Multi-instance continuity (DISTRIBUTED_VOLATILE) and durability (DURABLE_HYBRID): not implemented; the kit's C04/C05 items remain NOT_APPLICABLE/OPEN.
- Render/Docker/PowerShell/Electron/Windows: still NOT_RUN (same environment limits as the previous run).
- A worker thread is not an OS security boundary (nor was a worker process a sandbox). Tenant separation rests on one isolate per session, the allowlisted environment, the command filter and the fabric policy — the same controls as before, now with a per-session heap cap.
