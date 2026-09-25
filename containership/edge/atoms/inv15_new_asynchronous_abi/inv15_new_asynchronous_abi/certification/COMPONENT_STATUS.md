# INV-15 v4.3.0 — component checklist execution status

Environment: CPython 3.11.15 / Linux x86_64, INV15_SCALE=3. Tests: 104 in 38 classes, normal and `-O`; failing classes: 0.

| Status | Boxes |
|---|---|
| EVIDENCED | 656 |
| PARTIAL | 591 |
| BLOCKED | 272 |
| NOT_DONE | 80 |
| **total** | **1599** |

Status meanings: EVIDENCED = implemented and checked by an executed passing test/tool in this delivery; PARTIAL = real but incomplete (reason given); BLOCKED = needs a person, production host, other runtime/hardware, another component, keys, or elapsed time; NOT_DONE = reachable but not done. No box is ticked `[x]`.

| # | Component | Pri | E | P | B | N | Evidence | Open points |
|---|---|---|---|---|---|---|---|---|
| 1 | Canonical WIT/IDL definition for `PK_ASYNC_CALL/1` | P0 | 12 | 7 | 3 | 0 | `test_wire.TestIdl`, `test_host.TestCore`, `test_adapters.TestAsyncFunction` | B: only one language (Python) and one runtime exist |
| 2 | Canonical WIT/IDL definition for `PK_WAITABLE_SET/1` | P0 | 13 | 7 | 2 | 0 | `test_host.TestCore`, `test_wire.TestNegotiation` | — |
| 3 | Canonical WIT/IDL definition for `PK_SUBTASK_CANCEL/1` | P0 | 13 | 7 | 2 | 0 | `test_host.TestCancellation`, `test_certification.TestRaces` | — |
| 4 | Machine-readable error envelope | P0 | 10 | 10 | 2 | 0 | `test_wire.TestIdl`, `test_security_telemetry.TestRedaction` | P: registry has code+retryable but no owner/severity class; categories are distinct codes not a published class taxonomy; envelope carries no causal chain |
| 5 | Opaque-handle binary representation | P0 | 12 | 7 | 3 | 0 | `test_wire.TestHandleEncoding`, `test_wire.TestVectors` | B: layout is explicit big-endian but was only executed on one little-endian x86_64 host |
| 6 | Handle version tag / feature bits | P0 | 12 | 8 | 2 | 0 | `test_wire.TestHandleEncoding`, `test_wire.TestVectors` | P: vectors cover version 0/1/2, bit1 and bit4, not every flag combination |
| 7 | Formal lifecycle state machine specification | P0 | 13 | 7 | 2 | 0 | `test_host.TestLifecycle`, `test_certification.TestProperty` | — |
| 8 | Conformance vectors | P0 | 11 | 8 | 3 | 0 | `test_wire.TestVectors` | B: only one language consumes the corpus; P: corpus hashed in MANIFEST, not signed |
| 9 | Deadline propagation | P0 | 9 | 11 | 2 | 0 | `test_host.TestDeadlines` | P: detachment does not opt out of deadline inheritance; no cross-binding rounding exists; scheduler suspension not tested |
| 10 | Timeout behavior | P0 | 12 | 8 | 2 | 0 | `test_host.TestDeadlines` | — |
| 11 | Cancellation acknowledgment protocol | P0 | 12 | 8 | 2 | 0 | `test_host.TestCancellation` | — |
| 12 | Cancellation cause taxonomy | P0 | 9 | 10 | 2 | 1 | `test_host.TestCancellation`, `test_wire.TestIdl` | N: v1 decoders REJECT unknown reason codes (MALFORMED) instead of mapping them to OTHER - not forward-compatible; P: no vendor range; only Future.cancel is mapped |
| 13 | Nested cancellation tree | P0 | 11 | 9 | 2 | 0 | `test_host.TestCancellation` | P: deep tree tested (64 levels); wide trees under quota pressure not tested |
| 14 | Idempotency metadata | P0 | 9 | 10 | 2 | 1 | `test_host.TestIdempotency` | N: same-key/different-payload conflict is not detected (payload is not compared); P: no entropy guidance; callee retry safety not declared per operation |
| 15 | Retry contract | P0 | 9 | 9 | 2 | 2 | `test_host.TestIdempotency` | N: attempt number is not carried; no retry-storm test; P: ambiguous-commit outcome not distinguished |
| 16 | Hierarchical budgets | P0 | 10 | 10 | 2 | 0 | `test_host.TestBudgetsFairness`, `test_certification.TestSoakOverload` | P: node/global scopes collapse into process; explain() shows tenant names to operators (not reviewed) |
| 17 | Fairness policy hooks | P0 | 11 | 9 | 2 | 0 | `test_host.TestBudgetsFairness`, `test_certification.TestSoakOverload` | P: fairness measured as held-count parity, no starvation metric |
| 18 | Drain/quiesce mode | P0 | 11 | 9 | 2 | 0 | `test_host.TestDrainDisable` | P: no bounded grace-period timer; policies are allow/cancel/invalidate |
| 19 | Production host-side table backend | P0 | 0 | 2 | 17 | 3 | — | B: the production backend is by definition not this Python reference; nothing here replaces it |
| 20 | Generation-safe handle registry | P0 | 12 | 6 | 4 | 0 | `test_host.TestGenerations` | — |
| 21 | Cryptographically strong token source binding | P0 | 10 | 8 | 4 | 0 | `test_host.TestRng`, `test_certification.TestFaultInjection` | P: secrets.token_bytes documented, FIPS not considered; guessing math for deployment scale not written |
| 22 | Wakeup registration primitive | P0 | 9 | 8 | 5 | 0 | `test_host.TestSubscribe`, `test_certification.TestLostWakeup` | B: no futex/scheduler-native primitive; P: thousands of randomized iterations, not millions; removal-vs-publication race not threaded |
| 23 | Ready-queue implementation | P0 | 10 | 6 | 6 | 0 | `test_host.TestReadyQueue`, `test_certification.TestSoakOverload` | B: no MPSC/scheduler-native queue; no multi-core contention measurement possible under the GIL |
| 24 | Batched readiness delivery | P0 | 10 | 7 | 4 | 1 | `test_host.TestReadyQueue` | P: singleton-starvation not tested; N: no batch-size benchmark |
| 25 | Completion publication API | P0 | 12 | 6 | 4 | 0 | `test_host.TestCore`, `test_certification.TestFaultInjection` | — |
| 26 | Trap/fault completion state | P0 | 9 | 8 | 5 | 0 | `test_host.TestCore`, `test_adapters.TestAsyncFunction` | P: one TRAPPED class, host abort/resource kill not distinguished; no privileged diagnostic path; B: no language bindings |
| 27 | Instance teardown invalidation | P0 | 12 | 6 | 4 | 0 | `test_host.TestTeardownRestart` | — |
| 28 | Runtime restart semantics | P0 | 10 | 8 | 4 | 0 | `test_host.TestTeardownRestart` | P: epoch is in memory, not persisted; crash at every transition not tested |
| 29 | Memory accounting | P0 | 11 | 7 | 4 | 0 | `test_host.TestMemoryOwnership`, `test_certification.TestSoakOverload` | P: reconciliation ran and FOUND a gap - declared 256 B/row vs ~1.1 KB/row measured by tracemalloc (see BENCHMARK_BASELINE.json) |
| 30 | Payload ownership/zero-copy contract | P0 | 10 | 7 | 5 | 0 | `test_host.TestMemoryOwnership` | P: result ownership defined, input buffers not; B: sanitizers do not apply to CPython |
| 31 | SCH-01 scheduler adapter | P1 | 11 | 8 | 3 | 0 | `test_adapters.TestScheduler`, `test_certification.TestFaultInjection` | P: adapter run queue is FIFO, tenant fairness not preserved at this layer |
| 32 | INV-16 async component function adapter | P1 | 9 | 10 | 3 | 0 | `test_adapters.TestAsyncFunction` | P: no generated guest stubs; deadline not mapped from the future; timeout/teardown/version-mismatch paths untested at this layer |
| 33 | INV-17 streaming adapter | P1 | 10 | 9 | 3 | 0 | `test_adapters.TestStream` | P: gap/duplicate rules unwritten; only some close/error races tested |
| 34 | INV-18 completion adapter | P1 | 10 | 9 | 3 | 0 | `test_adapters.TestCompletion` | P: type check is isinstance only; resolution races untested |
| 35 | INV-11 contract-language bindings | P1 | 10 | 7 | 4 | 1 | `test_wire.TestIdl` | B: INV-11 grammar belongs to INV-11; N: no diagnostics for unsupported async features |
| 36 | INV-12 language interop bindings | P1 | 0 | 3 | 16 | 3 | — | B: INV-12 and other languages absent; P: widths/BE/UTF-8 explicit in codec |
| 37 | INV-14 migration shim | P1 | 8 | 10 | 4 | 0 | `test_adapters.TestShim` | B: INV-14 behaviour inventory needs INV-14's source; P: deprecation counter has no workload label; no cutover deadline |
| 38 | Cross-runtime interop harness | P1 | 4 | 8 | 5 | 5 | `test_wire.TestVectors` | B: 'two independent runtimes, not two wrappers' - there is one author and one language; the harness compares codec vs codec_alt and v4.2 model vs v4.3 host |
| 39 | Capability-boundary threat model | P0 | 7 | 4 | 4 | 7 | `test_security_telemetry.TestSideChannel`, `test_host.TestReplayTenant` | B: residual-risk owner unnamed |
| 40 | Handle redaction policy | P0 | 11 | 8 | 3 | 0 | `test_security_telemetry.TestRedaction` | P: correlation-id collision/rotation not documented beyond per-process key |
| 41 | Replay protection across serialized boundaries | P0 | 10 | 9 | 3 | 0 | `test_host.TestReplayTenant`, `test_wire.TestHandleEncoding`, `test_host.TestTeardownRestart` | P: no per-transport anti-replay window; version-upgrade replay not tested |
| 42 | Tenant identity binding | P0 | 11 | 8 | 3 | 0 | `test_host.TestCore`, `test_host.TestReplayTenant`, `test_security_telemetry.TestAudit` | P: adapters carry views but the scheduler adapter keys by instance name; not reviewed |
| 43 | Security audit events | P0 | 9 | 10 | 3 | 0 | `test_security_telemetry.TestAudit` | P: timestamp is host monotonic (not trusted), no host id; chain integrity but no access control; forensic reconstruction not exercised |
| 44 | Resource-exhaustion adversarial suite | P0 | 10 | 9 | 3 | 0 | `test_certification.TestSoakOverload`, `test_host.TestBudgetsFairness`, `test_host.TestSubscribe` | P: CPU/lock contention not measured; recovery phases short |
| 45 | Side-channel review | P0 | 10 | 9 | 3 | 0 | `test_security_telemetry.TestSideChannel` | P: timing compared by median over 400 samples with a coarse 5x bound, noise not modelled; explain/metrics surface not reviewed |
| 46 | Supply-chain attestation | P0 | 8 | 9 | 4 | 1 | `test_ops.TestRelease` | B: no signing key/signer; N: no vulnerability scan; P: SBOM is empty because there are zero dependencies |
| 47 | Metrics exporter | P1 | 10 | 8 | 2 | 2 | `test_security_telemetry.TestTelemetry` | P: table invariants reconciled, counters not; N: exporter overhead not load-tested |
| 48 | Cancellation latency histogram | P1 | 10 | 8 | 2 | 2 | `test_host.TestCancellation`, `test_security_telemetry.TestTelemetry` | N: buckets are generic log2, not derived from an SLO; P: alert rule written, not verified with injected delay |
| 49 | Readiness-to-resume latency histogram | P1 | 8 | 10 | 2 | 2 | `test_adapters.TestScheduler` | P: publication, runnable and resume stamped; guest resume is outside this model; N: batching/coalescing treatment unwritten |
| 50 | Structured event log schema | P1 | 11 | 8 | 2 | 1 | `test_security_telemetry.TestTelemetry` | P: schema fixed but not version-tagged |
| 51 | Distributed trace propagation | P1 | 9 | 9 | 2 | 2 | `test_security_telemetry.TestTelemetry` | N: no span/link model for fan-out/retries; P: scheduler wake not traced |
| 52 | Explain/debug endpoint | P1 | 10 | 7 | 3 | 2 | `test_security_telemetry.TestTelemetry` | B: there is no endpoint server to authenticate; N: explain() under overload not tested |
| 53 | Dashboard and alert pack | P1 | 9 | 9 | 3 | 1 | `test_ops.TestRelease` | B: never imported into Grafana/Prometheus or exercised in staging; P: thresholds PROPOSED, no owner |
| 54 | Telemetry retention/sampling policy | P1 | 9 | 8 | 3 | 2 | `test_security_telemetry.TestTelemetry` | N: no collector-outage behaviour; B: privacy review |
| 55 | Property-based state-machine tests | P0 | 11 | 7 | 3 | 1 | `test_certification.TestProperty` | P: teardown not in the generator; N: no shrinking |
| 56 | Protocol/handle fuzzing | P0 | 10 | 8 | 4 | 0 | `test_certification.TestFuzz` | B: sanitizers; P: seeds are generator outputs not the full vector corpus; mutations are byte-level |
| 57 | Concurrency race suite | P0 | 10 | 8 | 4 | 0 | `test_certification.TestRaces` | B: thread sanitizer; P: slot reuse covered in TestGenerations not under threads; iteration gate small |
| 58 | Lost-wakeup stress test | P0 | 10 | 9 | 3 | 0 | `test_certification.TestLostWakeup` | P: 3,000 x SCALE iterations on one host, not millions across cores; removal-vs-publication not included |
| 59 | Soak and churn test | P0 | 11 | 8 | 3 | 0 | `test_certification.TestSoakOverload` | P: 20,000 x SCALE cycles in seconds, not long-duration; patterns mixed randomly, not rotated in phases |
| 60 | Overload test | P0 | 11 | 8 | 3 | 0 | `test_certification.TestSoakOverload`, `test_host.TestBudgetsFairness` | P: p99 recorded, CPU not; fail-fast cost not profiled |
| 61 | Benchmark suite | P0 | 0 | 8 | 3 | 11 | `test_ops.TestBench` | P: core ops benchmarked at 1 and 8 threads, no wait-registration benchmark; environment recorded, no warmup rule; N: no CI regression gate |
| 62 | Architecture compatibility matrix | P0 | 7 | 3 | 4 | 8 | `test_ops.TestRelease` | B: other OS/arch/runtimes not available; N: install-time blocking of unsupported rows |
| 63 | Fault-injection suite | P0 | 12 | 7 | 3 | 0 | `test_certification.TestFaultInjection` | P: trap, clock, RNG, scheduler stall, producer death, callback faults injected; host crash only as restart(); allocator pressure only via memory ceilings |
| 64 | Independent implementation conformance test | P0 | 5 | 6 | 6 | 5 | `test_wire.TestVectors` | B: no independent production implementation exists; results unsigned |
| 65 | Package/build metadata | P1 | 7 | 11 | 4 | 0 | `test_ops.TestRelease` | P: no build revision embedded; clean isolated install not run |
| 66 | CI pipeline | P1 | 5 | 11 | 5 | 1 | `test_ops.TestRelease` | P: ci.sh has no lint/type-check stage; N: no cache exists; B: protected-branch approvals |
| 67 | Version compatibility matrix | P1 | 6 | 11 | 5 | 0 | `test_adapters.TestScheduler`, `test_wire.TestNegotiation` | B: adjacent component versions are unknown here; E: fail-fast on unsupported major |
| 68 | Canary rollout procedure | P1 | 6 | 11 | 5 | 0 | `test_ops.TestRollbackHook` | B: representative workloads/architectures; P: hook compares a subset of signals, pause is not automated |
| 69 | Automated rollback hook | P1 | 6 | 10 | 6 | 0 | `test_ops.TestRollbackHook`, `test_host.TestTeardownRestart` | B: no deployment system to automate restore or exercise |
| 70 | Emergency disable/drain control | P1 | 6 | 11 | 5 | 0 | `test_host.TestDrainDisable` | P: instance + global scope only, unauthenticated, no grace deadline; B: control-plane loss |
| 71 | Incident runbook | P1 | 2 | 7 | 6 | 7 | `test_ops.TestRelease` | B: escalation contacts and exercises need people |
| 72 | Patch/vulnerability/EOL policy | P1 | 1 | 8 | 5 | 8 | `test_ops.TestRelease` | B: owners; N: exception tracking |

## Tool checks

- `bindgen`: exit 0
- `vectors`: exit 0
- `interop`: exit 0

## Certification scale actually executed

```
{
 "blocking_wait_iterations": 1500,
 "fuzz_decodes": 300000,
 "fuzz_inputs": 60000,
 "lost_wakeup_iterations": 9000,
 "overload_ops": 30000,
 "overload_p99_ns": 115854,
 "property_sequences": 90,
 "property_steps": 36000,
 "race_rounds": 120,
 "soak_cycles": 60000,
 "soak_heap_growth_bytes": -11764
}
```
