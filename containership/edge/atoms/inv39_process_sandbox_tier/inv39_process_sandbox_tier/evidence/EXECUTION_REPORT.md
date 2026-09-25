# INV-39 5.1.0 — Execution report

Workflow executed: `INV39_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST_v5.0.0.md` (106 components) on candidate `inv39_process_sandbox_tier` 5.0.0 (hardened).

## Verdict

**Exit gate: NO_GO** — 110 reasons in `evidence/exit-gate.json`. Nothing is ACCEPTED; nothing is claimed production-ready.

| Priority | IMPLEMENTED | PARTIAL | BLOCKED |
|---|---|---|---|
| P0 | 20 | 14 | 5 |
| P1 | 24 | 21 | 1 |
| P2 | 6 | 12 | 3 |

Total: 50 / 47 / 9.

## Measured on the build host (Linux 6.18.44, x86_64, Python 3.11.15, root in container)

* Test suite: 103 tests, 100 pass, 3 skipped (pk_core conformance). Same result under `python -O`.
* Certification mode (`INV39_CERT_TARGET=1`): 1 failure — `pk_core` absent (MC-094). This is the intended behaviour: no silent skips.
* Adversarial probes executed inside the sandbox: 17/17 BLOCKED (x32 ABI killed by SIGSYS).
* Launch latency (all controls + kernel read-back, /bin/true): p50 13.406 ms, p99 16.529 ms vs plain fork+exec p50 1.272 ms; burst of 16: p99 61.137 ms, 0 errors. Thresholds are PROPOSED.
* Release build reproducible (two builds byte-identical); SBOM + provenance bind the artifact digest; artifact unsigned (no key).

## Defects found and fixed during the pass

1. The first ready/pid handshake could lose the supervisor's pid message when the workload's ready message arrived first — merged into one loop.
2. `ctypes.util.find_library` ran after Landlock restricted the filesystem, so seccomp installation failed under Landlock — libc is now resolved at import time.
3. Probe output was lost when the x32 probe was SIGSYS-killed (buffered stdout) — probes are unbuffered and x32 runs on its own.
4. Inside the pid namespace the workload still saw host processes through the inherited /proc — a fresh `/proc` (hidepid=2) is now mounted and a probe checks it.
5. `run_as` could not work inside the user namespace (only uid 0 was mapped; `setgroups` denied) — the target ids are mapped directly and the setgroups-deny case is handled.
6. A test used `pgrep -f`, which matched unrelated processes' command lines — replaced with a pid-namespace membership scan.
7. A metrics test assumed a histogram could be added after the series cap — the cap applies, the test now asserts that.

## BLOCKED — external inputs needed

* **MC-001** Named accountable owner and escalation path — needs a named accountable owner, security reviewer, on-call and release approver.
* **MC-032** macOS Seatbelt profile compiler/launcher/verification adapter — needs a macOS host to execute and certify the Seatbelt backend.
* **MC-071** Verified optimization implementation/evidence for locality, batching, zero-copy, or equivalent where applicable — needs depends on MC-070 analysis; no optimisation claimed.
* **MC-073** Power/thermal measurements for constrained edge nodes — needs edge hardware and a power meter.
* **MC-087** Compatibility matrix test suite across supported CPU architectures, kernels, Python/runtime versions, bubblewrap/Seatbelt versions, and schema versions — needs runners for aarch64, other kernels, Python 3.10/3.12/3.13, bwrap and macOS.
* **MC-091** Benchmark, soak, burst, and fleet-scale certification tests — needs soak (>1 h) and fleet-scale environments.
* **MC-093** Machine-readable signed acceptance evidence required before release certification — needs an independent human reviewer's signing key and signature.
* **MC-094** Full 100-check `pk_core` conformance evidence from this archive; current integration tests skip because `pk_core` is absent — needs pk_core framework (fails under INV39_CERT_TARGET=1).
* **MC-106** Distribution license/NOTICE and package metadata suitable for redistribution — needs the owner's choice of licence and NOTICE text.

Full per-item detail: `TRACEABILITY.json`, `MISSING_COMPONENTS.md`.
