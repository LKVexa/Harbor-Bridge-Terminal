# INV-19 Repository Audit — 5.0.0

## Verdict

**BLOCKED — not production-certified.** The missing-components checklist (MC-01..MC-28) was executed. Linux x86-64 now has genuine host I/O through io_uring, epoll and a portable fallback, with executable evidence behind every requirement the local host can prove. The production gate still reports BLOCKED because the remaining items need inputs that do not exist in this archive or this environment. The exact counts, the per-requirement blockers and the signed evidence bundle are in `evidence/gate_result.json` and `evidence/evidence_bundle.jsonl` (verify them with `python tools/run_gate.py --verify`).

## How to read the evidence
- Behaviour, security, platform and performance requirements PASS only when their mapped tests pass under **both** `python` and `python -O`, or when their measured evidence files meet thresholds. Evidence files carry the source revision, so stale evidence fails.
- A skip counts as a blocker, never as a pass. Unexplained skips block too.
- The gate is shown to fail when fed bad input: `evidence/self_test.json` records seven tamper cases plus two known-bad mutants (readiness that fabricates completions; completion errors swallowed), and all of them are caught.

## Defects found and fixed by this pass's own tooling
1. **io_uring CQ-overflow stall.** With `IORING_FEAT_NODROP`, overflowed CQEs wait in a kernel backlog that only `io_uring_enter(GETEVENTS)` flushes. The reaper never called it, so one overflow stalled every later completion. The soak burst's 300-op cancellation storm found this. The fix flushes when `IORING_SQ_CQ_OVERFLOW` is set. The regression test fails on the old code and passes on the fix.
2. **Quarantine did not fail over.** Quarantining the active backend re-initialised the same backend.
3. **Config coercion.** `int(inf)` raised `OverflowError` instead of `ConfigError`, and `1.5` was silently truncated to `1`. Config fuzzing found this; regression corpus entries R5 and R6 cover it.

4. **Start-up under descriptor exhaustion.** `AsyncHost()` crashed with a raw `OSError` (EMFILE). It now refuses with `BackendUnavailable(NO_USABLE_BACKEND)` and per-backend `PROBE_FAILED:RESOURCE_EXHAUSTED` reasons. The 256-fd certification cell found this.
5. **Test cascade under low fd limits.** The 256-caller test leaked descriptors when it failed, turning one failure into 58. It now cleans up, scales to the fd budget, and reports a reduced run as BLOCKED rather than PASS.

## Measured on this host (Linux 6.18, x86-64, CPython 3.11)
See `evidence/bench.json` and `evidence/soak.json`. Headline: reap p99 was about 0.2 ms on io_uring, epoll and portable, inside the 1 ms one-tick SLO. io_uring shows **no** latency advantage here, because each operation's Python control-plane work (capability MAC, audit hash chain, metrics) dominates. That result is recorded as a finding, not hidden.

## Remaining blockers (all named in the bundle)
pk_core source and pin (MC-01) · IOCP, kqueue and arm64 execution (MC-03/05/24) · authoritative INV-17/18/15/13/SCH-01 packages (MC-08/09/10/23) · KMS-bound keys, at-rest encryption, advisory feed (MC-16/17) · 4-hour release soak (MC-26) · named owners and approvers, ADR approval, staging rollback, recurring reviews, countersigned exit record (MC-28) · node attestation, infrastructure-graph correlation, scale-out/in and power/thermal measurement.
