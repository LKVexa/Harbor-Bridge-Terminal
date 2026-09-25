# Test and certification strategy (INV-40-C082..C090)

| Kind | Where | Lane | Status |
|---|---|---|---|
| Contract tests for every public interface | `tests/test_fvt_service.py::ContractTest`, schema tests | cloud/any CPython ≥3.10 | run |
| Integration with adjacent layers (INV-23, PLN-04, INV-32, INV-33) | — | needs those elements | **BLOCKED** (not in repo); pk_core integration tests skip without pk_core |
| Compatibility across CPU arch / hypervisor / protocol versions | protocol negotiation tests; CPython 3.10–3.12 CI matrix declared | arch/hypervisor matrix **BLOCKED** (HW-KVM) |
| Fuzzing | `tools/fuzz.py` (4 targets + structure-aware journal lane), 40k iterations in CI | run |
| Concurrency / races | lease race (v4.2.0), parallel creates vs quota, parallel boots one winner | run |
| Security tests from threat model | T2–T13 mapped in THREAT_MODEL.md | run (T1/T14 BLOCKED) |
| Fault injection | `FaultInjectionTest` via programmable FakeProvider | run |
| Benchmark / burst | `tools/bench.py` | run (control-plane only); soak & fleet **BLOCKED** (ELAPSED, FLEET) |
| Disaster / partition / reconnect | crash-restart reconcile, fencing partition, backup/restore of journal | run in-process; multi-node **BLOCKED** (DIST-STORE) |
| Machine-readable acceptance evidence | `tools/ci.py` → `evidence/ci_run.json`, bound to artifact digest; mandatory skips fail the run | run |

Mandatory-skip rule: `tools/ci.py` treats any skipped test outside the declared `pk_core` lane as a failure, and reports the `pk_core` lane itself as `NOT_RUN` (never PASS).
