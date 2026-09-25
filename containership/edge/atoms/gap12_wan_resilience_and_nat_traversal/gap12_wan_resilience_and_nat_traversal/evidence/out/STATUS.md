# GAP-12 v4.3.0 checklist status

Items: **2420** — NOT-EVIDENCED 1805, PASS 615

Production gate: **NO-GO** · P0 exit gates passed 0 / 80 · P1 0 / 34 · P2 0 / 2

| Component | Title | Prio | Lifecycle | PASS | NOT-EV | FAIL | Exit gate |
|---|---|---|---|---|---|---|---|
| G12-A001 | STUN client | P0 | validation | 14 | 8 | 0 | NOT-EVIDENCED |
| G12-A002 | TURN client | P0 | validation | 12 | 10 | 0 | NOT-EVIDENCED |
| G12-A003 | ICE-compatible candidate gathering/checking state machine | P0 | validation | 9 | 13 | 0 | NOT-EVIDENCED |
| G12-A004 | UDP hole-punch implementation | P0 | validation | 10 | 12 | 0 | NOT-EVIDENCED |
| G12-A005 | TCP fallback / traversal adapter | P0 | validation | 7 | 15 | 0 | NOT-EVIDENCED |
| G12-A006 | NAT behavior classifier | P0 | validation | 6 | 16 | 0 | NOT-EVIDENCED |
| G12-A007 | Carrier-grade NAT detection/telemetry | P0 | validation | 7 | 15 | 0 | NOT-EVIDENCED |
| G12-A008 | PCP adapter | P1 | implementation | 5 | 17 | 0 | NOT-EVIDENCED |
| G12-A009 | NAT-PMP adapter | P1 | implementation | 7 | 15 | 0 | NOT-EVIDENCED |
| G12-A010 | UPnP IGD adapter | P1 | implementation | 5 | 17 | 0 | NOT-EVIDENCED |
| G12-A011 | IPv6 direct-path support | P0 | implementation | 5 | 17 | 0 | NOT-EVIDENCED |
| G12-A012 | NAT64 / DNS64 compatibility | P1 | implementation | 4 | 18 | 0 | NOT-EVIDENCED |
| G12-A013 | 464XLAT/mobile-network compatibility testing | P1 | design | 1 | 21 | 0 | NOT-EVIDENCED |
| G12-A014 | Dual-stack connection racing / Happy-Eyeballs policy | P0 | validation | 7 | 15 | 0 | NOT-EVIDENCED |
| G12-A015 | QUIC transport adapter | P1 | design | 1 | 21 | 0 | NOT-EVIDENCED |
| G12-A016 | TLS/TCP transport fallback adapter | P1 | validation | 5 | 19 | 0 | NOT-EVIDENCED |
| G12-B017 | Local interface inventory | P0 | validation | 9 | 11 | 0 | NOT-EVIDENCED |
| G12-B018 | Default-route and route-change watcher | P0 | validation | 7 | 13 | 0 | NOT-EVIDENCED |
| G12-B019 | Multi-WAN uplink manager | P0 | validation | 5 | 15 | 0 | NOT-EVIDENCED |
| G12-B020 | Link-flap debounce/hysteresis | P0 | validation | 5 | 15 | 0 | NOT-EVIDENCED |
| G12-B021 | Connection migration | P1 | validation | 3 | 17 | 0 | NOT-EVIDENCED |
| G12-B022 | Source-address/interface pinning | P1 | validation | 5 | 15 | 0 | NOT-EVIDENCED |
| G12-B023 | DNS resolver resilience | P0 | validation | 8 | 14 | 0 | NOT-EVIDENCED |
| G12-B024 | Captive-portal / walled-garden detection | P1 | validation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-B025 | Path MTU discovery and black-hole detection | P0 | validation | 7 | 15 | 0 | NOT-EVIDENCED |
| G12-B026 | MSS/MTU policy integration | P1 | validation | 3 | 17 | 0 | NOT-EVIDENCED |
| G12-B027 | Local firewall reachability diagnostics | P1 | validation | 5 | 15 | 0 | NOT-EVIDENCED |
| G12-C028 | Per-strategy attempt deadlines and cancellation | P0 | validation | 14 | 8 | 0 | NOT-EVIDENCED |
| G12-C029 | Health-probe scheduler | P0 | validation | 7 | 13 | 0 | NOT-EVIDENCED |
| G12-C030 | Bulk-transfer readiness probe | P0 | validation | 5 | 15 | 0 | NOT-EVIDENCED |
| G12-C031 | Latency/loss/jitter measurement | P0 | validation | 7 | 15 | 0 | NOT-EVIDENCED |
| G12-C032 | Available-bandwidth estimation | P1 | validation | 5 | 17 | 0 | NOT-EVIDENCED |
| G12-C033 | Path scoring with hysteresis | P1 | validation | 6 | 14 | 0 | NOT-EVIDENCED |
| G12-C034 | Session keepalive manager | P1 | validation | 3 | 17 | 0 | NOT-EVIDENCED |
| G12-C035 | Connection/session resumption | P1 | validation | 3 | 17 | 0 | NOT-EVIDENCED |
| G12-C036 | Candidate cache with safe expiry | P1 | validation | 3 | 17 | 0 | NOT-EVIDENCED |
| G12-C037 | Relay pre-warming policy | P1 | validation | 3 | 17 | 0 | NOT-EVIDENCED |
| G12-C038 | Relay region selection | P1 | validation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-C039 | Relay quota/budget enforcement | P0 | validation | 6 | 16 | 0 | NOT-EVIDENCED |
| G12-C040 | Automatic relay-byte instrumentation | P0 | validation | 7 | 15 | 0 | NOT-EVIDENCED |
| G12-C041 | Multipath failover/striping | P2 | implementation | 3 | 17 | 0 | NOT-EVIDENCED |
| G12-C042 | Predictive path switching | P2 | implementation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-D043 | GAP-06 peer identity/attestation enforcement | P0 | validation | 14 | 8 | 0 | NOT-EVIDENCED |
| G12-D044 | End-to-end authenticated encryption integration | P0 | validation | 11 | 11 | 0 | NOT-EVIDENCED |
| G12-D045 | Key acquisition/rotation/revocation behavior | P0 | validation | 5 | 15 | 0 | NOT-EVIDENCED |
| G12-D046 | Replay protection | P0 | validation | 8 | 14 | 0 | NOT-EVIDENCED |
| G12-D047 | TURN credential lifecycle and rotation | P0 | validation | 6 | 16 | 0 | NOT-EVIDENCED |
| G12-D048 | Relay authorization and tenancy isolation | P0 | validation | 6 | 14 | 0 | NOT-EVIDENCED |
| G12-D049 | Per-peer/IP/range rate limiting | P0 | validation | 11 | 11 | 0 | NOT-EVIDENCED |
| G12-D050 | Circuit breaker / retry budget | P0 | validation | 9 | 13 | 0 | NOT-EVIDENCED |
| G12-D051 | Egress/peer policy enforcement | P0 | validation | 6 | 14 | 0 | NOT-EVIDENCED |
| G12-D052 | Secrets manager integration | P0 | validation | 8 | 14 | 0 | NOT-EVIDENCED |
| G12-D053 | Endpoint privacy controls | P1 | validation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-D054 | Abuse/anomaly detection | P1 | implementation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-D055 | Tamper-evident security audit events | P1 | validation | 7 | 13 | 0 | NOT-EVIDENCED |
| G12-E056 | Thread/async safety model | P0 | validation | 11 | 11 | 0 | NOT-EVIDENCED |
| G12-E057 | Atomic state-transition implementation | P0 | validation | 8 | 12 | 0 | NOT-EVIDENCED |
| G12-E058 | Durable or reconstructable path/session state policy | P0 | validation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-E059 | Monotonic clock abstraction | P0 | validation | 5 | 17 | 0 | NOT-EVIDENCED |
| G12-E060 | Clock-jump/suspend-resume handling | P0 | validation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-E061 | Process supervision and restart policy | P0 | validation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-E062 | Dependency health model | P0 | validation | 3 | 21 | 0 | NOT-EVIDENCED |
| G12-E063 | Degraded-control-plane policy | P0 | validation | 3 | 17 | 0 | NOT-EVIDENCED |
| G12-E064 | Quarantine/disable control | P0 | validation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-E065 | Stale-controller/duplicate-owner protection | P1 | validation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-E066 | State migration/versioning | P1 | validation | 3 | 17 | 0 | NOT-EVIDENCED |
| G12-F067 | Versioned configuration schema | P0 | validation | 11 | 11 | 0 | NOT-EVIDENCED |
| G12-F068 | Configuration validation before activation | P0 | validation | 7 | 13 | 0 | NOT-EVIDENCED |
| G12-F069 | Environment/site overlays | P0 | validation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-F070 | Atomic configuration reload/rollback | P0 | validation | 5 | 15 | 0 | NOT-EVIDENCED |
| G12-F071 | Configuration provenance | P0 | validation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-F072 | Policy for enabling/disabling traversal mechanisms | P1 | validation | 3 | 17 | 0 | NOT-EVIDENCED |
| G12-F073 | Relay cost policy | P1 | validation | 3 | 17 | 0 | NOT-EVIDENCED |
| G12-F074 | Feature flags with expiry/ownership | P1 | validation | 3 | 17 | 0 | NOT-EVIDENCED |
| G12-G075 | Metrics exporter | P0 | validation | 11 | 11 | 0 | NOT-EVIDENCED |
| G12-G076 | Structured logging | P0 | validation | 8 | 14 | 0 | NOT-EVIDENCED |
| G12-G077 | Distributed trace propagation | P0 | validation | 6 | 16 | 0 | NOT-EVIDENCED |
| G12-G078 | Health/readiness endpoint | P0 | validation | 5 | 15 | 0 | NOT-EVIDENCED |
| G12-G079 | Reason codes | P0 | validation | 6 | 14 | 0 | NOT-EVIDENCED |
| G12-G080 | Operator explain view | P1 | validation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-G081 | Dashboards | P0 | implementation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-G082 | Alerts/SLO burn rules | P0 | implementation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-G083 | Telemetry retention/sampling/privacy policy | P1 | implementation | 5 | 15 | 0 | NOT-EVIDENCED |
| G12-G084 | Correlation with deployment/release lineage and topology graph | P1 | implementation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-H085 | Unit tests for every transition and boundary value | P0 | validation | 6 | 14 | 0 | NOT-EVIDENCED |
| G12-H086 | Contract/schema tests for `PK_PATH_REQUEST/1`, `PK_PATH_STATE/1`, `PK_BACKOFF/1`, and relay accounting | P0 | validation | 7 | 13 | 0 | NOT-EVIDENCED |
| G12-H087 | Integration tests against real STUN/TURN implementations | P0 | design | 2 | 22 | 0 | NOT-EVIDENCED |
| G12-H088 | NAT matrix test lab | P0 | validation | 4 | 18 | 0 | NOT-EVIDENCED |
| G12-H089 | Network-namespace/container emulation | P0 | implementation | 2 | 20 | 0 | NOT-EVIDENCED |
| G12-H090 | Partition/reconnect/flap tests | P0 | validation | 5 | 15 | 0 | NOT-EVIDENCED |
| G12-H091 | DNS outage/poison/stale-cache tests | P0 | validation | 5 | 15 | 0 | NOT-EVIDENCED |
| G12-H092 | IPv4/IPv6/NAT64 compatibility matrix | P0 | design | 2 | 18 | 0 | NOT-EVIDENCED |
| G12-H093 | Firewall/UDP-blocked/captive-portal test scenarios | P0 | validation | 5 | 15 | 0 | NOT-EVIDENCED |
| G12-H094 | Fuzz tests | P0 | validation | 6 | 16 | 0 | NOT-EVIDENCED |
| G12-H095 | Concurrency/race tests | P0 | validation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-H096 | Security tests | P0 | validation | 5 | 15 | 0 | NOT-EVIDENCED |
| G12-H097 | Long-duration soak tests | P1 | design | 2 | 18 | 0 | NOT-EVIDENCED |
| G12-H098 | Fleet-scale retry-storm test | P1 | validation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-H099 | Benchmarks | P1 | validation | 3 | 17 | 0 | NOT-EVIDENCED |
| G12-H100 | Machine-readable production acceptance evidence | P0 | validation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-I101 | Declared supported Python/runtime/platform matrix | P0 | validation | 5 | 15 | 0 | NOT-EVIDENCED |
| G12-I102 | Reproducible package metadata/build | P0 | validation | 4 | 16 | 0 | NOT-EVIDENCED |
| G12-I103 | Pinned external dependency versions | P0 | validation | 3 | 17 | 0 | NOT-EVIDENCED |
| G12-I104 | SBOM and provenance/signature generation | P0 | validation | 4 | 18 | 0 | NOT-EVIDENCED |
| G12-I105 | CI pipeline | P0 | validation | 5 | 17 | 0 | NOT-EVIDENCED |
| G12-I106 | Vulnerability scanning and patch SLA | P0 | design | 2 | 18 | 0 | NOT-EVIDENCED |
| G12-I107 | Canary/staged rollout/rollback mechanism | P0 | validation | 5 | 15 | 0 | NOT-EVIDENCED |
| G12-I108 | Emergency-disable/kill switch | P0 | validation | 6 | 16 | 0 | NOT-EVIDENCED |
| G12-I109 | Day-0 bootstrap runbook | P0 | validation | 2 | 22 | 0 | NOT-EVIDENCED |
| G12-I110 | Day-1 deployment runbook | P0 | validation | 2 | 18 | 0 | NOT-EVIDENCED |
| G12-I111 | Day-2 operations runbook | P0 | validation | 2 | 18 | 0 | NOT-EVIDENCED |
| G12-I112 | Incident severity/paging/escalation matrix | P0 | validation | 2 | 18 | 0 | NOT-EVIDENCED |
| G12-I113 | Backup/reconstruction guidance | P1 | validation | 2 | 18 | 0 | NOT-EVIDENCED |
| G12-I114 | Compatibility matrix and end-of-life policy | P0 | validation | 2 | 18 | 0 | NOT-EVIDENCED |
| G12-I115 | Exception/waiver/technical-debt register | P0 | validation | 3 | 17 | 0 | NOT-EVIDENCED |
| G12-I116 | Formal production exit gate | P0 | validation | 5 | 17 | 0 | NOT-EVIDENCED |

## Global definition of done

- **G-DOD-01** NOT-EVIDENCED — no P0 component has passed its exit gate (owners and security review absent)
- **G-DOD-02** NOT-EVIDENCED — mandatory IPv6/NAT64/independent-interop tests cannot run in this environment
- **G-DOD-03** PASS — hard deadlines (AttemptRunner) + bounded histories/limiters + retry budget, tested
- **G-DOD-04** NOT-EVIDENCED — identity/E2E enforcement is tested for direct/punched/relayed; TCP/QUIC/translated paths are not covered
- **G-DOD-05** NOT-EVIDENCED — IPv6, dual-stack, NAT64/464XLAT scenarios impossible here
- **G-DOD-06** PASS — explain() + registered reason codes, redacted
- **G-DOD-07** NOT-EVIDENCED — reproducible + SBOM + canary + kill switch exist; provenance unsigned

## Checklist defects found

- checklist defect: this item's text is copied from G12-A001 (STUN client) -> G12-E062-01
- checklist defect: this item's text is copied from G12-A001 (STUN client) -> G12-E062-02
- checklist defect: this item's text is copied from G12-A001 (STUN client) -> G12-I109-01
- checklist defect: this item's text is copied from G12-A001 (STUN client) -> G12-I109-02
- checklist defect: this item's text is copied from G12-A002 (TURN client) -> G12-D047-01
- checklist defect: this item's text is copied from G12-A002 (TURN client) -> G12-D047-02
- checklist defect: this item's text is copied from G12-A002 (TURN client) -> G12-E062-03
- checklist defect: this item's text is copied from G12-A002 (TURN client) -> G12-E062-04
- checklist defect: this item's text is copied from G12-A002 (TURN client) -> G12-I109-03
- checklist defect: this item's text is copied from G12-A002 (TURN client) -> G12-I109-04
- checklist defect: this item's text is copied from G12-A015 (QUIC transport adapter) -> G12-A016-01
- checklist defect: this item's text is copied from G12-A015 (QUIC transport adapter) -> G12-A016-02
