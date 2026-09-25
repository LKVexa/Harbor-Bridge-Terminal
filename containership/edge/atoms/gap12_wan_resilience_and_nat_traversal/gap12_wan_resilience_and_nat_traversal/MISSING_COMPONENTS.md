# GAP-12 Production Missing Components

> **v4.3.0 note:** this is the v4.2.0 inventory, kept as delivered. Its 116 items are the components of the
> applied checklist; their current per-sub-check status is in `evidence/out/STATUS.md` (0 of 116 exit gates
> pass; see `AUDIT_REPORT.md`).

This inventory distinguishes the hardened **reference-control logic** in v4.2.0 from the components required for a production WAN resilience and NAT traversal subsystem. Priority is relative to production readiness: **P0 = required before production**, **P1 = strongly recommended**, **P2 = advanced/optimization**.

## A. Concrete NAT traversal and transport adapters

1. **P0 - STUN client** for server-reflexive address discovery and binding behavior tests.
2. **P0 - TURN client** with authenticated allocations, permissions, channels, refresh, and expiry handling.
3. **P0 - ICE-compatible candidate gathering/checking state machine** or a documented equivalent.
4. **P0 - UDP hole-punch implementation** with simultaneous-open coordination.
5. **P0 - TCP fallback / traversal adapter** for networks that block UDP.
6. **P0 - NAT behavior classifier** covering endpoint-independent, address-dependent, port-dependent, and symmetric mappings/filtering.
7. **P0 - Carrier-grade NAT detection/telemetry** so CGNAT-specific failure modes are explainable.
8. **P1 - PCP adapter** for explicit port mappings when available.
9. **P1 - NAT-PMP adapter** for compatible gateways.
10. **P1 - UPnP IGD adapter** with strict local-network trust and policy controls.
11. **P0 - IPv6 direct-path support** including global address/candidate discovery.
12. **P1 - NAT64 / DNS64 compatibility** and detection.
13. **P1 - 464XLAT/mobile-network compatibility testing**.
14. **P0 - Dual-stack connection racing / Happy-Eyeballs policy**.
15. **P1 - QUIC transport adapter** with connection migration support where the data plane permits it.
16. **P1 - TLS/TCP transport fallback adapter** where QUIC/UDP is unavailable.

## B. Link, interface, and routing management

17. **P0 - Local interface inventory** for Ethernet, Wi-Fi, cellular, VPN/tunnel, and virtual adapters.
18. **P0 - Default-route and route-change watcher**.
19. **P0 - Multi-WAN uplink manager** with priority and policy constraints.
20. **P0 - Link-flap debounce/hysteresis** to avoid oscillating path decisions.
21. **P1 - Connection migration** between uplinks without unnecessarily discarding healthy sessions.
22. **P1 - Source-address/interface pinning** for probes and established paths.
23. **P0 - DNS resolver resilience** with multiple resolvers, timeout policy, and stale-answer rules.
24. **P1 - Captive-portal / walled-garden detection**.
25. **P0 - Path MTU discovery and black-hole detection**.
26. **P1 - MSS/MTU policy integration** for tunnel/relay paths.
27. **P1 - Local firewall reachability diagnostics** that explain blocked ingress/egress without modifying policy implicitly.

## C. Path-quality, selection, and session lifecycle

28. **P0 - Per-strategy attempt deadlines and cancellation** so a hung prober cannot block escalation.
29. **P0 - Health-probe scheduler** independent of caller traffic.
30. **P0 - Bulk-transfer readiness probe** separate from small liveness probes.
31. **P0 - Latency/loss/jitter measurement** for usable-path quality decisions.
32. **P1 - Available-bandwidth estimation**.
33. **P1 - Path scoring with hysteresis** to prevent route thrash.
34. **P1 - Session keepalive manager** with NAT mapping refresh policy.
35. **P1 - Connection/session resumption** after brief disconnects.
36. **P1 - Candidate cache with safe expiry**.
37. **P1 - Relay pre-warming policy** for sites with repeatedly failed direct traversal.
38. **P1 - Relay region selection** based on topology, latency, residency, and cost.
39. **P0 - Relay quota/budget enforcement** to prevent billing abuse.
40. **P0 - Automatic relay-byte instrumentation** wired to the actual transport rather than manual accounting calls.
41. **P2 - Multipath failover/striping** where semantics and transport support it.
42. **P2 - Predictive path switching** based on deteriorating quality signals.

## D. Identity, encryption, trust, and abuse resistance

43. **P0 - GAP-06 peer identity/attestation enforcement** before accepting a path as trusted.
44. **P0 - End-to-end authenticated encryption integration** across direct, punched, and relayed paths.
45. **P0 - Key acquisition/rotation/revocation behavior** for WAN sessions.
46. **P0 - Replay protection** for traversal/control messages.
47. **P0 - TURN credential lifecycle and rotation**.
48. **P0 - Relay authorization and tenancy isolation**.
49. **P0 - Per-peer/IP/range rate limiting** for traversal attempts.
50. **P0 - Circuit breaker / retry budget** beyond per-path backoff to prevent fleet-wide failure cascades.
51. **P0 - Egress/peer policy enforcement** defining where the subsystem may connect.
52. **P0 - Secrets manager integration**; no long-lived credentials in ordinary config/logs.
53. **P1 - Endpoint privacy controls** for logs, metrics, traces, and support bundles.
54. **P1 - Abuse/anomaly detection** for forced-relay attacks, scanning, amplification, or credential misuse.
55. **P1 - Tamper-evident security audit events** linked to identity and configuration lineage.

## E. State, concurrency, persistence, and failure containment

56. **P0 - Thread/async safety model** for shared `Path` state.
57. **P0 - Atomic state-transition implementation** for concurrent probe/timer events.
58. **P0 - Durable or reconstructable path/session state policy** after process/node restart.
59. **P0 - Monotonic clock abstraction** injected by the runtime and test harness.
60. **P0 - Clock-jump/suspend-resume handling**.
61. **P0 - Process supervision and restart policy**.
62. **P0 - Dependency health model** for STUN, TURN, DNS, identity, keys, observability, and control plane.
63. **P0 - Degraded-control-plane policy** defining which existing sessions may continue.
64. **P0 - Quarantine/disable control** for a faulty traversal backend or peer.
65. **P1 - Stale-controller/duplicate-owner protection** if path decisions can be made by multiple controllers.
66. **P1 - State migration/versioning** across software upgrades.

## F. Configuration and policy plane

67. **P0 - Versioned configuration schema** for strategies, servers, timeouts, freshness, retry ceilings, and policy.
68. **P0 - Configuration validation before activation** with fail-closed rules for trust-sensitive fields.
69. **P0 - Environment/site overlays** without rebuilding immutable artifacts.
70. **P0 - Atomic configuration reload/rollback**.
71. **P0 - Configuration provenance** including author/source/version/activation time.
72. **P1 - Policy for enabling/disabling traversal mechanisms** per environment or network zone.
73. **P1 - Relay cost policy** including regional price/budget metadata.
74. **P1 - Feature flags with expiry/ownership** for staged rollout of traversal methods.

## G. Observability and operator experience

75. **P0 - Metrics exporter** for attempts, outcomes, latency, backoff, partitions, relay bytes, and dependency health.
76. **P0 - Structured logging** with stable site/peer/operation identifiers and endpoint redaction.
77. **P0 - Distributed trace propagation** across control and data-plane path establishment.
78. **P0 - Health/readiness endpoint** exposing version, configuration generation, dependencies, and active capabilities.
79. **P0 - Reason codes** for every automated path-selection/failover decision.
80. **P1 - Operator explain view** linking selected strategy to probe outcomes and constraints.
81. **P0 - Dashboards** separating ordinary load, network degradation, dependency failure, policy rejection, attack, and software defect.
82. **P0 - Alerts/SLO burn rules** for partition rate, establishment latency, retry storms, and relay saturation/cost.
83. **P1 - Telemetry retention/sampling/privacy policy**.
84. **P1 - Correlation with deployment/release lineage and topology graph**.

## H. Testing, emulation, and certification

85. **P0 - Unit tests for every transition and boundary value** beyond the included reference tests.
86. **P0 - Contract/schema tests for `PK_PATH_REQUEST/1`, `PK_PATH_STATE/1`, `PK_BACKOFF/1`, and relay accounting**.
87. **P0 - Integration tests against real STUN/TURN implementations**.
88. **P0 - NAT matrix test lab** covering full-cone/restricted/port-restricted/symmetric/CGNAT behavior.
89. **P0 - Network-namespace/container emulation** for packet loss, latency, jitter, reordering, duplication, and corruption.
90. **P0 - Partition/reconnect/flap tests** with exact recovery objectives.
91. **P0 - DNS outage/poison/stale-cache tests**.
92. **P0 - IPv4/IPv6/NAT64 compatibility matrix**.
93. **P0 - Firewall/UDP-blocked/captive-portal test scenarios**.
94. **P0 - Fuzz tests** for config, control messages, candidate parsing, and untrusted adapter results.
95. **P0 - Concurrency/race tests** for simultaneous probes, timers, disconnects, and config reloads.
96. **P0 - Security tests** for replay, spoofing, forced relay, credential abuse, and resource exhaustion.
97. **P1 - Long-duration soak tests** for NAT mapping churn and memory/history stability.
98. **P1 - Fleet-scale retry-storm test** proving jitter/circuit-breaking behavior.
99. **P1 - Benchmarks** for establishment latency, CPU, memory, packets/bytes, relay overhead, and power on edge hardware.
100. **P0 - Machine-readable production acceptance evidence** generated by the parent architecture gate with all dependencies present.

## I. Packaging, deployment, and operations

101. **P0 - Declared supported Python/runtime/platform matrix**.
102. **P0 - Reproducible package metadata/build** (`pyproject.toml` or parent-repository equivalent).
103. **P0 - Pinned external dependency versions** for concrete network adapters.
104. **P0 - SBOM and provenance/signature generation** for release artifacts.
105. **P0 - CI pipeline** running unit, integration, security, compatibility, and optimized-mode tests.
106. **P0 - Vulnerability scanning and patch SLA**.
107. **P0 - Canary/staged rollout/rollback mechanism**.
108. **P0 - Emergency-disable/kill switch** for unsafe traversal methods.
109. **P0 - Day-0 bootstrap runbook** including STUN/TURN/identity/config dependencies.
110. **P0 - Day-1 deployment runbook** including readiness and rollback criteria.
111. **P0 - Day-2 operations runbook** including partitions, relay saturation, and cost incidents.
112. **P0 - Incident severity/paging/escalation matrix**.
113. **P1 - Backup/reconstruction guidance** for any durable state introduced later.
114. **P0 - Compatibility matrix and end-of-life policy** for protocol/runtime/dependency versions.
115. **P0 - Exception/waiver/technical-debt register** with owners and expiry dates.
116. **P0 - Formal production exit gate** that treats absent dependencies or skipped tests as non-evidence.

## Highest-priority implementation sequence

For the shortest path from this reference component to a real service, implement P0 work in this order: **(1) concrete STUN/TURN/ICE + deadlines, (2) identity/encryption, (3) interface/multi-WAN/DNS/MTU handling, (4) concurrency + supervision + configuration, (5) observability, (6) NAT/network emulation and security testing, (7) deployment/CI/evidence gate**.
