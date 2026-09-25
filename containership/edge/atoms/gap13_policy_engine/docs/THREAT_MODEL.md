# GAP-13 threat model (drives `tests/test_security.py`, G13-MC-037)

Trust boundaries: (1) bundle publisher → GAP-13 (signed envelope); (2) caller → GAP-13 (request attributes, tokens); (3) operator → GAP-13 (privileged API); (4) GAP-13 → local disk (cache, anti-replay, control, audit); (5) GAP-13 → telemetry sinks.

| ID | STRIDE | Threat | Control | Test |
|---|---|---|---|---|
| TM01 | Spoofing/Tampering | Unsigned or forged bundle adds a permissive rule | Ed25519 verification before parse; VERIFIED minted only in `verify.py` | `test_TM01_*`, `test_verify` |
| TM02 | Elevation | Caller self-asserts tenant/identity/classification | Protected attributes only from trusted provider | `test_TM02_*` |
| TM03 | Info disclosure | Cross-tenant rule applies to another tenant | Tenant from provider; tenant rules bind tenant | `test_TM03_*` |
| TM04 | Elevation | Tenant rule widens an estate deny | Activation-time scope check | `test_TM04_*` |
| TM05 | Tampering | Replay/downgrade of an older valid bundle | Durable anti-rollback floor, collision detection | `test_TM05_*`, `test_replay_*` |
| TM06 | Tampering | Tie-break manipulation to pick attacker rule | Deny-before-allow at equal specificity | `test_TM06_*` |
| TM07 | DoS | Oversized bundle/request, rule explosion | Byte/count/depth/attr limits; admission control | `test_TM07_*`, bench overload |
| TM08 | Tampering | Type confusion (`true` vs `1`) matches a rule | Type-strict matching and typed attributes | `test_TM08_*` |
| TM09 | Spoofing | Unicode confusables / invisible characters | NFC + control/format char rejection | `test_TM09_*` |
| TM10 | Elevation | Service identity or wrong role performs admin op | Capabilities, service caps capped, scope, step-up, SoD | `test_TM10_*`, `AuthTests` |
| TM11 | Info disclosure | Explanations/logs leak request data or tenant IDs | Value redaction, detailed-explain capability, pseudonymisation | `test_TM11_*`, `test_telemetry` |
| TM12 | Tampering | Algorithm downgrade (`alg: none`) via envelope | Local allowlist, key-registered algorithm | `test_TM12_*` |
| TM13 | Repudiation | Admin denies an action | Hash-chained audit log | `AuditTests` |
| TM14 | Tampering | Old cache restored to disk | Re-verification + anti-rollback floor | `test_faults.test_restore_from_old_cache_cannot_downgrade` |
| TM15 | Tampering | Clock rollback extends stale policy | Monotonic + max(wall) age | `StaleTests`, `test_faults` |
| TM16 | DoS | Audit sink down hides actions | Bounded buffer, privileged ops refused when full | `test_faults` |

Residual risks: in-process attacker with code execution can bypass any library control; HMAC admin tokens are a reference format (replace with IdP-issued asymmetric tokens, EXT-03); external pen-test not yet performed.
