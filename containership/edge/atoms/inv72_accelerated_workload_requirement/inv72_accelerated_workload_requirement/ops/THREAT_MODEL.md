# INV-72 threat model (C041, C050, C087)

Method: STRIDE over the boundary inventory in `ops/BOUNDARIES.md`. Every threat names its control
and the adversarial test that exercises it (`tests/test_v43.py::AdversarialTest` and the suites named).
Status **open** means no in-archive control exists.

| ID | Actor / asset | Threat | Control | Test |
|---|---|---|---|---|
| T1 | malicious tenant → partition isolation | escalate to a shared slice via a lookalike isolation value (`"Shared"`, `"any"`, `None`) | strict enum, default dedicated | `AdversarialTest.test_T1_…` |
| T2 | malicious tenant → logs/audit | log/JSON injection through identifiers | schema pattern on ids; one JSON object per line; redaction | `test_T2_…` |
| T3 | network attacker → API | replay a captured request token | nonce cache within validity window, bounded TTL | `test_T3_…`, `TrustTest.test_replay_refused` |
| T4 | compromised/spoofed node → inventory | publish fake devices (advertised label) | digest + HMAC per source, monotonic generation, failover only to verified sources | `test_T4_…`, `DiscoveryTest` |
| T5 | tenant A → tenant B's reservation | release/steal another tenant's devices | tenant-scoped token + reservation tenant check | `test_T5_…` |
| T6 | caller → source of truth | inject inventory through the request | request schema forbids extra fields | `test_T6_…` |
| T7 | any caller → availability | exhaust memory (nonce cache, audit buffer, tenant buckets, metric series) | every table bounded; overflow refuses **before** side effects | `test_T7_…`, `ResilienceTest`, `TelemetryTest` |
| T8 | buggy/compromised peer code → matcher | mutate a validated Device (NaN memory) after construction | re-validation inside `decide()` | `test_T8_…` |
| T9 | stale controller → reservation state | split-brain double allocation after failover | fencing tokens | `FaultInjectionTest.test_controller_failover_…` |
| T10 | insider with disk access → journal / audit | edit history | SHA-256 chain (HMAC when keyed), external head anchor for tail truncation | `AuditTest`, `FaultInjectionTest.test_mid_journal_corruption_refused` |
| T11 | unavailable key/identity service | "allow while down" | fail closed (`ACCEL_DEPENDENCY_UNAVAILABLE`) | `TrustTest.test_key_service_down_fails_closed` |
| T12 | operator mistake → config | activate an unsafe profile | schema + semantic validation, secrets refused, probe + auto-rollback | `ConfigTest` |
| T13 | malicious tenant → device memory / side channels | co-resident slice leaks data | **open** — execution isolation is host/GAP-11 owned (W-003) | — |
| T14 | supply chain → code | tampered release | SHA256SUMS + RELEASE_MANIFEST; **no asymmetric signature** (W-004) | `tools/manifest.py --verify` |
| T15 | data at rest → journal | read reservation history | **open** — no at-rest encryption (W-004) | — |

Residual risk is carried by the named waivers; none is approved.
