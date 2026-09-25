# Telemetry governance (MC-42) — PROPOSED

Policy enforced in code (`telemetry.TELEMETRY_POLICY`): tenant ids pseudonymised in logs; log retention 30 d; metrics 395 d; trace sampling 0.1.

| Alert | Signal | Distinguishes |
|---|---|---|
| PlacementRefusalSpike | rate(placement_refusals_total{code="NO_CANDIDATE"}) | load / capacity |
| AuthFailureSpike | rate(placement_refusals_total{code=~"UNAUTHENTICATED|FORBIDDEN"}) | attack |
| AttestationFailures | refusals ATTESTATION_* | node compromise / discovery fault |
| DependencyDown | health.dependencies != ok, CIRCUIT_OPEN | dependency failure |
| Fenced | service_state == FENCED | ownership loss |
| InternalErrors | refusals code=INTERNAL | software defect |
| LatencySLO | placement_seconds p99 > 0.1 | degradation |

Dashboards and alert rules are specified here; none is deployed (no backend bound).
