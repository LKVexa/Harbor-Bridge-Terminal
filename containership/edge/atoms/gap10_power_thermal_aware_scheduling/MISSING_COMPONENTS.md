# GAP-10 Missing Components After v4.2.0 Audit

> **4.3.0 status:** all 40 components now have code or artefacts in this package (see `docs/COMPONENTS.md`). Item-level status against the professional checklist is in `evidence/CHECKLIST_EVIDENCE.md`. Production closure still needs the items marked PARTIAL/OPEN there: named owners and reviewer sign-off, real GAP-09/GAP-11/SCH-01/PLN-05 integration, an external linearizable store, site hardware calibration, fleet-scale runs on target hardware, and asymmetric signing (`docs/EXCEPTION_REGISTER.md`). The original v4.2.0 list is kept below unchanged.

This list describes capabilities **not present in the supplied GAP-10 ZIP** after the v4.2.0 hardening pass. Some may already exist elsewhere in the larger Post-Kubernetes estate; they should be integrated and evidenced rather than reimplemented if so.

## P0 - Required before production enforcement

1. **Authenticated telemetry adapter for GAP-09** (`C021-C024`, `C041-C048`) — a concrete adapter that accepts only attested temperature/power/battery samples and carries source identity, freshness, and signature status into GAP-10.
2. **Downstream scheduler enforcement adapter** (`C021`, `C030`, `C054`) — integration that makes `PK_POWER_CEILING/1` a hard admission/placement ceiling rather than advisory data.
3. **Elasticity-plane enforcement adapter** (`C021`, `C030`) — propagation of reduced ceilings to scale-out/scale-in logic so autoscaling cannot immediately refill thermally constrained capacity.
4. **Durable per-node state store** (`C032`, `C057`, `C058`, `C095`) — persistence/reconstruction of band, last trusted sample, policy version, and hysteresis state across process restart/failover.
5. **Atomic policy distribution and activation service** (`C033-C038`) — site/environment policy delivery with validation, staged activation, provenance, rollback, and immutable revision IDs.
6. **Policy authorization/signature verification** (`C023-C025`, `C045`, `C049`) — prevent an untrusted actor from raising thermal thresholds, power budgets, or reserve limits.
7. **Explicit fail-closed scheduler behavior when GAP-10 is absent/unhealthy** (`C014`, `C048`, `C054-C059`) — downstream consumers must never interpret missing GAP-10 output as unlimited node capacity.
8. **Controller ownership/leader fencing** (`C057-C059`) — avoid two schedulers/controllers simultaneously publishing conflicting ceilings for the same node.

## P1 - Core operational capability

9. **Hardware/site calibration inventory** (`C012`, `C017`, `C031`, `C035`) — validated per-device temperature limits, sustained/TDP power budgets, battery chemistry/reserve rules, and cooling characteristics.
10. **Multi-sensor aggregation model** (`C011-C015`) — combine CPU, GPU, VRM, SSD, inlet, exhaust, chassis, and accelerator hotspot sensors using an explicit worst-case or weighted policy.
11. **Thermal rate-of-rise predictor** (`C013`, `C061-C070`) — predictive derating before the static threshold is crossed, required to substantiate the stated 99% pre-throttle SLO.
12. **Battery discharge/remaining-runtime estimator** (`C017`, `C068-C069`) — use load, battery health, discharge curve, reserve target, and expected runtime instead of a single remaining-fraction threshold.
13. **Cooling-domain/site correlation** (`C006`, `C055`, `C068-C069`) — model shared racks/cabinets/rooms so a local cool reading does not hide a failing shared cooling domain.
14. **Accelerator thermal integration with GAP-11** (`C003`, `C030`, `C068`) — GPU/NPU/FPGA power and hotspot contribution integrated into node ceilings.
15. **Workload-class-aware shedding policy** (`C017`, optional contract capability) — deterministic rules for which capacity classes are reduced first without allowing any class to bypass emergency exclusion.
16. **Constraint-precedence engine** (`C019`) — documented and executable precedence among thermal safety, security, residency, SLO, cost, maintenance, and emergency operator actions.
17. **Health/readiness API** (`C052`, `C071`) — expose active policy revision, sample age, dependency health, state-store health, and whether the component is safe to enforce.
18. **Quarantine/freeze/emergency-disable control** (`C059`, `C092`) — authenticated operational control that is observable, reversible, and cannot silently revert to unlimited capacity.

## P2 - Security, observability, and resilience

19. **Structured error taxonomy** (`C026`) — stable machine-readable error codes for invalid policy, stale telemetry, missing trust, store failure, ownership conflict, and downstream rejection.
20. **Tamper-evident audit sink** (`C049`) — append-only records for policy changes, emergency exclusions, overrides, ownership changes, and security failures.
21. **Metrics exporter** (`C072`) — gauges/counters/histograms for temperature, power ratio, ceiling, exclusions, telemetry age, hysteresis holds, decision latency, and dependency failures.
22. **Structured logging and trace propagation** (`C073-C075`) — stable node/site/workload/operation IDs with privacy-safe high-cardinality diagnostics.
23. **Operator explain endpoint/UI** (`C076-C078`) — show current decision, exact source samples, policy revision, threshold crossings, hysteresis state, and downstream enforcement status.
24. **Dashboards and alerts** (`C080`) — distinguish ordinary derating from stale telemetry, cooling failure, battery emergency, forged-input rejection, software defects, and fleet-wide events.
25. **Retry/backoff/circuit-breaker policy** (`C025`, `C053-C056`) — bounded dependency behavior for telemetry, state store, policy service, and downstream scheduler calls.
26. **Partition/reconnect semantics** (`C018`, `C055`, `C057-C058`, `C089`) — specify local authority and reconciliation when edge nodes are disconnected from the control plane.
27. **Clock-source/time-service strategy** (`C048`, `C051`) — authenticated/monotonic freshness handling and documented behavior under clock jumps or time-service loss.
28. **Secret/key isolation model** (`C039`, `C042-C047`) — capability-scoped identities, no ambient secret access, managed key rotation, and encrypted transport/state where sensitive metadata is present.

## P3 - Certification, performance, release, and governance

29. **End-to-end integration test harness** (`C030`, `C083`) — real GAP-09 -> GAP-10 -> scheduler/elasticity test path with success, stale, forged, emergency, and recovery scenarios.
30. **Contract/schema validator tests** (`C082`, `C085`) — validate JSON instances against the bundled schemas and fuzz untrusted telemetry/policy boundaries.
31. **Concurrency/race test suite** (`C086`) — simultaneous updates, policy swaps, controller failover, duplicate samples, and node deletion/recreation.
32. **Fault-injection suite** (`C060`, `C089`) — sensor dropout, stuck-high/stuck-low values, telemetry delay, store outage, scheduler outage, partition, process crash, and restart.
33. **Benchmark/soak/fleet-scale harness** (`C061-C070`, `C088`) — p50/p95/p99 decision latency, memory growth, CPU cost, queue saturation, and long-running stability across realistic fleet sizes.
34. **Cross-platform/hardware compatibility matrix** (`C084`, `C093`) — supported CPU architectures, sensor providers, operating systems/runtimes, GAP-09/GAP-11 schema versions, and scheduler versions.
35. **SBOM, dependency pinning, and vulnerability policy** (`C031`, `C045`, `C094`) — machine-readable dependency inventory, approved versions, CVE response SLA, and end-of-life policy.
36. **Artifact signing/provenance and reproducible release build** (`C045`, `C090`, `C100`) — signed package, build attestation, digest manifest, and machine-readable acceptance evidence.
37. **Canary/staged rollout controller** (`C092`) — policy/code rollout by site and hardware cohort with automated rollback triggers.
38. **Backup/restore/reconstruction runbook** (`C095-C097`) — restore policy/state, recover ownership safely, and verify downstream ceilings before reopening placement.
39. **Incident severity/paging/escalation definitions** (`C009`, `C097`) — named accountable owner, escalation path, thermal-safety incident classes, and response objectives.
40. **Architecture decision record and exception register** (`C010`, `C098-C100`) — approved ADR, waivers with owners/expiry, recurring architecture review, and formal production exit gate.

## Recommended closure order

Close P0 first, then P1 items 9-18. P2 and P3 can proceed in parallel once the enforcement path and durable state model are stable. The most important architectural rule is that no missing dependency, restart, stale sample, or policy failure may produce a less restrictive ceiling by accident.
