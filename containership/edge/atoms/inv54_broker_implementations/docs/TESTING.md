# Test and certification strategy  (components 82-90)

| # | Suite | Where | Status |
|---|---|---|---|
| 82 | public-interface contract tests | `tests/test_brokers.py`, `tests/test_production_layer.py` | local PASS |
| 83 | cross-layer/provider integration | `adapters/conformance.py` on reference + fake Kafka/RabbitMQ/SQS clients | fakes PASS; **real providers SKIPPED** (`tools/certify_providers.py`) |
| 84 | cross-runtime/arch/protocol | CI matrix Python 3.10–3.12 in `.github/workflows/ci.yml`; run here on 3.11.15 x86_64 only | PARTIAL |
| 85 | fuzz/property | `tests/test_properties.py` (seeded random property tests: name grammar, config validator, storage recovery on random truncation) | local PASS; no coverage-guided fuzzer |
| 86 | concurrency/race | `test_c86_*` (8 publishers + consumer, no loss/dup/reorder) | local PASS; no distributed race suite |
| 87 | security tests from threat model | T01–T14 mapped in `THREAT_MODEL.md` | local PASS; T15–T17 open |
| 88 | benchmark/soak/burst/fleet | `bench/harness.py` | bench PASS on build host; soak/fleet UNVERIFIED |
| 89 | machine-readable acceptance evidence | `evidence/*.json` via `tools/gen_evidence.py` | generated |
| 90 | re-runnable pk_core certification | `tests/test_component.py` needs `pk_core` | **SKIPPED — pk_core not supplied** |

Rule: a skipped or not-run mandatory check is never reported as PASS.
