# Failure catalog, recovery semantics and objectives (component 13)

INV-20 is stateless per request: no request state survives a crash, nothing is replayed automatically
after head commit, and duplicate-execution risk exists only for retried idempotent calls.

| Failure | Detection | Behaviour | RTO target | Evidence |
|---|---|---|---|---|
| Handler trap | task exception | `E_HANDLER_TRAP`; resources released | immediate | test_aio trap tests |
| Runtime/process crash | orchestrator liveness (`HealthMonitor.live`) | in-flight requests lost (client retries if idempotent); restart from bootstrap config | < 30 s | ReconstructionTest (in-process) |
| Node loss | orchestrator | reschedule; same as crash | < 60 s | **fleet drill pending** |
| Network partition / latency | deadlines, breaker | `E_DEADLINE`, `E_CIRCUIT_OPEN`; bounded retries | breaker reset 10 s | test_aio breaker/deadline |
| DNS failure / poisoned answer | resolver error / policy | `E_DNS_FAILURE` (retryable) / `E_DNS_DENIED` (never) | per TTL | test_egress |
| Upstream failure | transport error | retry safe classes only; breaker opens after 5 | 10 s | test_aio |
| Identity / policy service outage | exception from verifier/PDP | fail closed (`E_POLICY_UNAVAILABLE`); readiness → DEGRADED | on recovery | test_identity, HealthTest |
| Config service outage / stale config | readiness, provenance digest | keep last known-good; refuse new activation | n/a | test_config |
| Control-plane outage | stale config digest vs expected | continue on known-good; no authority expansion possible | n/a | **drill pending** |
| Resource exhaustion | admission counters, saturation | `E_OVERLOADED` load-shed; DEGRADED at 90 % queue | immediate | AdmissionTest, HealthTest |
| Security incident | alert / operator | `CapabilityStore.revoke_all()` (egress kill switch), `quarantine(tenant)` | < 1 min (operator) | test_identity |

Maximum degraded duration before escalation: 15 min (proposed). Escalation: see RUNBOOKS.md.
Detection objective: < 30 s for liveness/readiness changes (stall threshold default 30 s).
Fault-injection that needs real infrastructure (node restart under load, partitions, site loss) is
**not executed** in 4.3.0.
