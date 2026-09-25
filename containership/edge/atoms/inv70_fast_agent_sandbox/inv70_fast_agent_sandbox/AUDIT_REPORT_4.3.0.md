# INV-70 Remediation Audit Report — v4.3.0

**Date:** 2026-09-23
**Input:** `inv70_fast_agent_sandbox_v4.2.0_hardened` + `INV70_MISSING_COMPONENTS_REMEDIATION_CHECKLIST_4.2.0.md` (50 MISSING work packages)
**Method:** each package was implemented in the order the checklist recommends, tested, and then re-audited under the checklist's rule that "`[x]` only with objective evidence".

## Result

| | Before (4.2.0) | After (4.3.0) |
|---|---|---|
| MISSING | 50 | **0** |
| VERIFIED (new status) | — | **31** |
| PARTIAL | 35 | 52 (35 carried over + 17 new) |
| BLOCKED | — | 2 (C031 Wasm engine, C068 edge power) |
| PRESENT / N/A | 12 / 3 | 12 / 3 |
| Automated tests | 12 pass, 3 skip | **99 pass, 8 skip, 0 fail** (normal and `python -O`) |

**Release verdict (`RELEASE_EVIDENCE.json`): NOT_ACCEPTED.** The gate is designed to block here. Seven P0 items are PARTIAL because they need the owner's named people or signatures, or environments outside this repository. C031 is BLOCKED because the pinned wasmtime wheel could not be installed. The lockfile hash is UNSET. None of these was marked done or waived without evidence.

## Most important engineering changes

1. **A real deadline.** Every run executes in a fresh single-use `spawn` process that is killed at `wall_clock_ms`. A `jmp 0` loop with 10M fuel now stops at the 300 ms deadline, and a hung host callback stops at `host_call_timeout_ms`. In 4.2.0 neither could be pre-empted.
2. **A governed entry point** (`service.Sandbox.handle`). A request now passes through version negotiation, the degraded-mode gate, token authentication, idempotency, admission and circuit breaking, validation, capability intersection with the token grant, execution, stable `FB-*` reason codes, the audit chain, telemetry, and the explain record.
3. **Fail-closed trust.** Losing the trust store, time source or audit sink puts the sandbox in HALT. A successful result is never released unaudited.
4. **Measured optimization.** A warm pool of never-used workers keeps per-run isolation and cuts governed-run p50 from 62.7 ms to 2.2 ms.
5. **Honest SLO re-scope.** The old "p99 start < 50 µs" holds only for the in-process VM (arith6 p50 10.9 µs). The process-isolated path is now stated separately in `contract.py`.

## Defects found and fixed during remediation (with regression tests)
- A failed audit write could leave a new config active with no record. Now the audit is written before the swap (`test_audit_failure_aborts_activation`).
- An audit failure on an already-rejected request overwrote its reason. Now only successful results are converted, and rejections are flagged instead (`test_audit_sink_failure_is_fail_closed`).
- Artifact verification failures were marked `trapped` instead of `rejected`. Verification now runs before the RUNNING transition (`WasmProfile.test_fail_closed`).

## Test evidence

| Suite | Run | Pass | Skip | Fail |
|---|---|---|---|---|
| test_component | 3 | 0 | 3 | 0 |
| test_config | 6 | 6 | 0 | 0 |
| test_fuzz | 3 | 3 | 0 | 0 |
| test_governance | 13 | 13 | 0 | 0 |
| test_integration | 20 | 20 | 0 | 0 |
| test_resilience | 15 | 15 | 0 | 0 |
| test_runtime | 12 | 12 | 0 | 0 |
| test_security | 11 | 11 | 0 | 0 |
| test_semantics | 9 | 9 | 0 | 0 |
| test_telemetry | 8 | 8 | 0 | 0 |
| test_wasm | 7 | 2 | 5 | 0 |

The skips: `test_component` (3) needs the external `pk_core` package, carried over from 4.2.0. `test_wasm` (5) needs the pinned engine, and under `INV70_REQUIRE_WASM=1` those 5 become failures. Fuzzing: 3,000 random programs plus 1,000 random request envelopes plus 1,000 parser inputs on seed 7070 found no uncaught exception and no unknown reason code.

## What only the owner can close
1. Name the on-call alias, security reviewer and reliability reviewer in `OWNERS.md` (C009, C097).
2. Sign the ADR-0001 approval block (C010).
3. Install `wasmtime==25.0.0` on a CI runner and record its wheel sha256 in `requirements/wasm.lock` (C031). Then `release_evidence --require-wasm`.
4. Provide the environments: real INV-69/GAP-09 integration (C030, C083), a live attestation handshake (C044), multi-site failover (C055), staging fault certification (C060, C089), soak/fleet (C063, C088), edge power hardware (C068), a monitoring stack (C080), a scanner feed (C094).

## Remediated item matrix (the 50 previously MISSING)

| ID | Status | Implementation | Remaining gap |
|---|---|---|---|
| INV-70-C009 | **PARTIAL** | OWNERS.md | Accountable owner named. On-call alias, security reviewer and reliability reviewer are UNASSIGNED placeholders - the owner must name them. |
| INV-70-C010 | **PARTIAL** | docs/adr/ADR-0001-execution-technology.md | ADR drafted with options, decision and consequences; status PROPOSED until the owner and security reviewer sign the approval block. |
| INV-70-C012 | **VERIFIED** | docs/DEPLOYMENT_MATRIX.md, config.py::ENVIRONMENTS | — |
| INV-70-C015 | **VERIFIED** | semantics.py::Lifecycle, RUNTIME_SPEC.md#lifecycle | — |
| INV-70-C019 | **VERIFIED** | semantics.py::resolve_conflict, docs/PRECEDENCE.md, service.py (capability intersection, fuel tightening) | — |
| INV-70-C020 | **VERIFIED** | requirements/RTM.yaml, tools/remediation_status.py | — |
| INV-70-C023 | **VERIFIED** | security.py::Authenticator, docs/INTERFACES.md#authentication | Residual: HMAC key-id verifier; ADR-0001 records the move to asymmetric keys via the Verifier seam. |
| INV-70-C025 | **VERIFIED** | resilience.py::Deadline/CancelToken/IdempotencyCache, executor.py::ProcessExecutor, docs/INTERFACES.md#timeouts | — |
| INV-70-C027 | **VERIFIED** | semantics.py::negotiate/downgrade_result | — |
| INV-70-C030 | **PARTIAL** | tests/test_integration.py | All adjacent seams (caller tokens, host pipe, observability, control plane) are exercised in-process; the real INV-69 / GAP-09 / INV-71 components are not in this repository. |
| INV-70-C031 | **BLOCKED** | executor.py::WasmBackend, requirements/wasm.lock, docs/WASM_RUNTIME.md, tests/test_wasm.py | Engine seam, exact pin, fail-closed behaviour and malicious-module tests are in place; the pinned wasmtime wheel could not be installed in the remediation environment, so 5 engine tests SKIP (and FAIL under INV70_REQUIRE_WASM=1). Wheel hash in wasm.lock is UNSET. |
| INV-70-C035 | **VERIFIED** | config.py::resolve, docs/CONFIGURATION.md | — |
| INV-70-C036 | **VERIFIED** | config.py::ConfigStore._record | — |
| INV-70-C037 | **VERIFIED** | config.py::ConfigStore.activate/rollback | — |
| INV-70-C044 | **PARTIAL** | security.py::make_attestation/verify_attestation | Verification mechanism for all four roles is implemented and tested; there is no live node/peer/control-plane handshake in this repository to wire it into. |
| INV-70-C045 | **VERIFIED** | security.py::verify_artifact, service.py (wasm path) | — |
| INV-70-C048 | **VERIFIED** | security.py::TrustStore.available/Clock.healthy, resilience.py::derive_mode | — |
| INV-70-C049 | **VERIFIED** | security.py::AuditLog | — |
| INV-70-C053 | **VERIFIED** | resilience.py::RetryPolicy | Retry is a caller-side policy by design; the sandbox never retries a guest internally. |
| INV-70-C054 | **VERIFIED** | resilience.py::Admission/CircuitBreaker | — |
| INV-70-C055 | **PARTIAL** | resilience.py::select_failover | Failover selection policy is implemented and tested; there is no multi-site deployment to exercise it end to end. |
| INV-70-C056 | **VERIFIED** | resilience.py::Mode/DEGRADED_RULES, service.py::mode, RUNBOOK.md#degraded-modes | — |
| INV-70-C058 | **VERIFIED** | resilience.py::IdempotencyCache/FencedLease | — |
| INV-70-C060 | **PARTIAL** | tests/test_integration.py::Faults | Eight in-process fault-injection scenarios with recovery assertions; certification in a staging environment is still required. |
| INV-70-C061 | **VERIFIED** | tools/bench.py, perf/baseline.json | Baseline is for one machine class (recorded in the file). |
| INV-70-C063 | **PARTIAL** | tools/bench.py::bench_service/bench_burst | Steady, burst, overload and recovery measured; multi-node scale not measurable here. |
| INV-70-C064 | **VERIFIED** | tools/bench.py::bench_tenants | — |
| INV-70-C065 | **VERIFIED** | docs/PERFORMANCE.md#overhead-analysis | — |
| INV-70-C066 | **VERIFIED** | executor.py::ProcessExecutor(warm), docs/PERFORMANCE.md#optimizations | — |
| INV-70-C068 | **BLOCKED** | docs/PERFORMANCE.md#edge-power | Needs physical edge hardware with power instrumentation; procedure is written, no measurements exist. |
| INV-70-C070 | **VERIFIED** | tools/bench.py::gate, .github/workflows/ci.yml | — |
| INV-70-C072 | **VERIFIED** | telemetry.py::Metrics | — |
| INV-70-C073 | **VERIFIED** | telemetry.py::StructuredLog | — |
| INV-70-C074 | **VERIFIED** | telemetry.py::TraceContext | — |
| INV-70-C075 | **VERIFIED** | telemetry.py::DiagnosticChannel | — |
| INV-70-C077 | **VERIFIED** | service.py::Sandbox.explain | — |
| INV-70-C078 | **PARTIAL** | service.py::RELEASE_LINEAGE | Every run links to release version, source revision and config digest; no live infrastructure graph exists to correlate against. |
| INV-70-C079 | **PARTIAL** | telemetry.py::TELEMETRY_POLICY/redact | Policy as code with in-process redaction, sampling and bounds; retention-day enforcement belongs to the collector (GAP-09). |
| INV-70-C080 | **PARTIAL** | ops/alerts.yaml, ops/dashboard.json, service.py::REASON_CODES | Alert rules, dashboard and diagnostic classes are shipped as code; not deployed to a monitoring stack. |
| INV-70-C083 | **PARTIAL** | tests/test_integration.py | dev / prod / edge tiers certified in-process; real multi-layer environment not available. |
| INV-70-C084 | **PARTIAL** | docs/COMPATIBILITY.md, .github/workflows/ci.yml | Matrix defined; only CPython 3.11 / Linux x86_64 was actually exercised. |
| INV-70-C085 | **VERIFIED** | tests/test_fuzz.py | — |
| INV-70-C088 | **PARTIAL** | tools/bench.py | Benchmark and burst done locally; soak and fleet-scale not run. |
| INV-70-C089 | **PARTIAL** | tests/test_integration.py::Faults | Trust/time/audit outage, control-plane partition, drain and reconnect simulated in-process; no real network partition test. |
| INV-70-C090 | **VERIFIED** | tools/release_evidence.py, RELEASE_EVIDENCE.json | — |
| INV-70-C093 | **VERIFIED** | semantics.py::SUPPORTED_PEER_RELEASES/check_peer_release, docs/COMPATIBILITY.md | — |
| INV-70-C094 | **PARTIAL** | ops/VULNERABILITY_AND_EOL.md | Policy written; owner adoption and a scanner feed are pending. |
| INV-70-C097 | **PARTIAL** | RUNBOOK.md | Severity, containment and recovery defined; paging target is UNASSIGNED. |
| INV-70-C098 | **PARTIAL** | ops/REVIEWS.md | Review schedule defined; no review has been held yet. |
| INV-70-C099 | **VERIFIED** | EXCEPTIONS.yaml | — |

The full 100-item matrix is in `AUDIT_MATRIX_4.3.0.json`, traceability in `requirements/RTM.yaml`, and the annotated checklist in `INV70_REMEDIATION_CHECKLIST_4.3.0_STATUS.md`.
