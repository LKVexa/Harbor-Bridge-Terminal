# 40 - Adversarial / fuzz security suite - PK_DYN_ADVERSARIAL/1

Executable spec: `production/tests/test_secobs.py` classes `Fuzz*` and `Adversarial*`.
Owner: UNASSIGNED.

| Sub-part | Surfaces | Oracle |
|---|---|---|
| Parser fuzzing | `core.canonical`/`json` round trip, `Pool.tick` inputs, `parse_traceparent`, attestation evidence, policy bundles, audit lines | never an unexpected exception type; accepted input round-trips exactly; rejected input leaves state unchanged |
| Replay/spoof/injection | `TrustRoot`, nonces, delegation chain, log/JSON injection | replayed/forged/revoked material is rejected |
| Privilege escalation / authz bypass | `TrustRoot(production=True)`, `require_production`, `NamespacedState`, explain roles, revoked keys | always denied |
| Resource exhaustion / complexity | huge int demand, deep JSON, long traceparent, max_nodes=10000 tick | bounded time (asserted wall-clock ceilings) |
| Side channel / secret leakage | `Inv08Error.to_dict`, `redact`, logger, key `describe()` | no secret substring in output; MAC compare uses `hmac.compare_digest` |

Seeds are fixed integer constants in the tests so failures reproduce.
Timing side-channel measurement is out of scope (PARTIAL): no statistically valid
timing harness on shared CI hardware.
