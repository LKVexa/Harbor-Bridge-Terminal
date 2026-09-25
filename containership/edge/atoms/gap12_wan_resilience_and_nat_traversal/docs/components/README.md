# GAP-12 component documents

_Generated from `evidence/registry.py` by `ops/gen_docs.py`; do not edit by hand._

| Component | Title | Priority | Lifecycle | Code |
|---|---|---|---|---|
| [G12-A001](G12-A001.md) | STUN client | P0 | validation | `wan.stun.binding`, `wan.stun.discover` |
| [G12-A002](G12-A002.md) | TURN client | P0 | validation | `wan.turn.TurnClient`, `wan.turn.TurnServer` |
| [G12-A003](G12-A003.md) | ICE-compatible candidate gathering/checking state machine | P0 | validation | `wan.ice.Agent`, `wan.ice.Candidate` |
| [G12-A004](G12-A004.md) | UDP hole-punch implementation | P0 | validation | `wan.holepunch.punch`, `wan.holepunch.Rendezvous` |
| [G12-A005](G12-A005.md) | TCP fallback / traversal adapter | P0 | validation | `wan.transport.tcp_connect`, `wan.transport.race` |
| [G12-A006](G12-A006.md) | NAT behavior classifier | P0 | validation | `wan.natclass.classify`, `wan.natclass.Classification` |
| [G12-A007](G12-A007.md) | Carrier-grade NAT detection/telemetry | P0 | validation | `wan.natclass.assess_cgnat`, `wan.natclass.CgnatAssessment` |
| [G12-A008](G12-A008.md) | PCP adapter | P1 | implementation | `wan.portmap.pcp_map_request`, `wan.portmap.pcp_parse_response` |
| [G12-A009](G12-A009.md) | NAT-PMP adapter | P1 | implementation | `wan.portmap.natpmp_transact`, `wan.portmap.natpmp_map_request` |
| [G12-A010](G12-A010.md) | UPnP IGD adapter | P1 | implementation | `wan.portmap.validate_igd_url`, `wan.portmap.soap_add_port_mapping` |
| [G12-A011](G12-A011.md) | IPv6 direct-path support | P0 | implementation | `wan.netenv.eligible_ipv6`, `wan.stun.encode_address` |
| [G12-A012](G12-A012.md) | NAT64 / DNS64 compatibility | P1 | implementation | `wan.natclass.discover_nat64_prefixes`, `wan.natclass.synthesize` |
| [G12-A013](G12-A013.md) | 464XLAT/mobile-network compatibility testing | P1 | design |  |
| [G12-A014](G12-A014.md) | Dual-stack connection racing / Happy-Eyeballs policy | P0 | validation | `wan.transport.race`, `wan.transport.interleave` |
| [G12-A015](G12-A015.md) | QUIC transport adapter | P1 | design | `wan.transport.QuicAdapter` |
| [G12-A016](G12-A016.md) | TLS/TCP transport fallback adapter | P1 | validation | `wan.transport.tls_connect`, `wan.transport.tls_context` |
| [G12-B017](G12-B017.md) | Local interface inventory | P0 | validation | `wan.netenv.snapshot`, `wan.netenv.Snapshot` |
| [G12-B018](G12-B018.md) | Default-route and route-change watcher | P0 | validation | `wan.netenv.RouteWatcher` |
| [G12-B019](G12-B019.md) | Multi-WAN uplink manager | P0 | validation | `wan.netenv.select_uplink`, `wan.netenv.Uplink` |
| [G12-B020](G12-B020.md) | Link-flap debounce/hysteresis | P0 | validation | `wan.netenv.Debounce` |
| [G12-B021](G12-B021.md) | Connection migration | P1 | validation | `wan.netenv.should_migrate` |
| [G12-B022](G12-B022.md) | Source-address/interface pinning | P1 | validation | `wan.netenv.pinned_socket`, `wan.netenv.verify_pinning` |
| [G12-B023](G12-B023.md) | DNS resolver resilience | P0 | validation | `wan.dns.Resolver`, `wan.dns.DnsServer` |
| [G12-B024](G12-B024.md) | Captive-portal / walled-garden detection | P1 | validation | `wan.netenv.captive_verdict` |
| [G12-B025](G12-B025.md) | Path MTU discovery and black-hole detection | P0 | validation | `wan.netenv.Plpmtud` |
| [G12-B026](G12-B026.md) | MSS/MTU policy integration | P1 | validation | `wan.netenv.usable_mtu`, `wan.netenv.mss_for` |
| [G12-B027](G12-B027.md) | Local firewall reachability diagnostics | P1 | validation | `wan.netenv.diagnose_firewall` |
| [G12-C028](G12-C028.md) | Per-strategy attempt deadlines and cancellation | P0 | validation | `wan.quality.AttemptRunner`, `wan.quality.bounded_prober` |
| [G12-C029](G12-C029.md) | Health-probe scheduler | P0 | validation | `wan.quality.HealthScheduler` |
| [G12-C030](G12-C030.md) | Bulk-transfer readiness probe | P0 | validation | `wan.quality.bulk_ready` |
| [G12-C031](G12-C031.md) | Latency/loss/jitter measurement | P0 | validation | `wan.quality.QualityWindow` |
| [G12-C032](G12-C032.md) | Available-bandwidth estimation | P1 | validation | `wan.quality.BandwidthEstimator` |
| [G12-C033](G12-C033.md) | Path scoring with hysteresis | P1 | validation | `wan.quality.PathScorer` |
| [G12-C034](G12-C034.md) | Session keepalive manager | P1 | validation | `wan.quality.KeepalivePolicy` |
| [G12-C035](G12-C035.md) | Connection/session resumption | P1 | validation | `wan.quality.ResumptionTickets` |
| [G12-C036](G12-C036.md) | Candidate cache with safe expiry | P1 | validation | `wan.quality.CandidateCache` |
| [G12-C037](G12-C037.md) | Relay pre-warming policy | P1 | validation | `wan.quality.RelayPrewarm` |
| [G12-C038](G12-C038.md) | Relay region selection | P1 | validation | `wan.quality.choose_region` |
| [G12-C039](G12-C039.md) | Relay quota/budget enforcement | P0 | validation | `wan.quality.RelayQuota` |
| [G12-C040](G12-C040.md) | Automatic relay-byte instrumentation | P0 | validation | `wan.quality.InstrumentedRelay`, `wan.turn.Counters` |
| [G12-C041](G12-C041.md) | Multipath failover/striping | P2 | implementation | `wan.quality.MultipathScheduler` |
| [G12-C042](G12-C042.md) | Predictive path switching | P2 | implementation | `wan.quality.TrendPredictor` |
| [G12-D043](G12-D043.md) | GAP-06 peer identity/attestation enforcement | P0 | validation | `wan.security.TrustGate`, `wan.security.Attestation` |
| [G12-D044](G12-D044.md) | End-to-end authenticated encryption integration | P0 | validation | `wan.security.SecureChannel` |
| [G12-D045](G12-D045.md) | Key acquisition/rotation/revocation behavior | P0 | validation | `wan.security.SecureChannel.rotate` |
| [G12-D046](G12-D046.md) | Replay protection | P0 | validation | `wan.security.ReplayWindow` |
| [G12-D047](G12-D047.md) | TURN credential lifecycle and rotation | P0 | validation | `wan.security.TurnRestCredentials` |
| [G12-D048](G12-D048.md) | Relay authorization and tenancy isolation | P0 | validation | `wan.security.RelayAuthorizer` |
| [G12-D049](G12-D049.md) | Per-peer/IP/range rate limiting | P0 | validation | `wan.security.RateLimiter` |
| [G12-D050](G12-D050.md) | Circuit breaker / retry budget | P0 | validation | `wan.security.CircuitBreaker`, `wan.security.RetryBudget` |
| [G12-D051](G12-D051.md) | Egress/peer policy enforcement | P0 | validation | `wan.security.EgressPolicy` |
| [G12-D052](G12-D052.md) | Secrets manager integration | P0 | validation | `wan.security.SecretRef`, `wan.security.SecretProvider` |
| [G12-D053](G12-D053.md) | Endpoint privacy controls | P1 | validation | `wan.security.redact`, `wan.security.endpoint_token` |
| [G12-D054](G12-D054.md) | Abuse/anomaly detection | P1 | implementation | `wan.security.AnomalyDetector` |
| [G12-D055](G12-D055.md) | Tamper-evident security audit events | P1 | validation | `wan.security.AuditLog` |
| [G12-E056](G12-E056.md) | Thread/async safety model | P0 | validation | `wan.state.PathStore` |
| [G12-E057](G12-E057.md) | Atomic state-transition implementation | P0 | validation | `wan.state.PathStore.transition` |
| [G12-E058](G12-E058.md) | Durable or reconstructable path/session state policy | P0 | validation | `wan.state.PathStore.save`, `wan.state.PathStore.restore` |
| [G12-E059](G12-E059.md) | Monotonic clock abstraction | P0 | validation | `wan.state.Clock`, `wan.state.FakeClock` |
| [G12-E060](G12-E060.md) | Clock-jump/suspend-resume handling | P0 | validation | `wan.state.ClockWatch` |
| [G12-E061](G12-E061.md) | Process supervision and restart policy | P0 | validation | `wan.state.Supervisor`, `wan.state.RestartPolicy` |
| [G12-E062](G12-E062.md) | Dependency health model | P0 | validation | `wan.state.DependencyHealth` |
| [G12-E063](G12-E063.md) | Degraded-control-plane policy | P0 | validation | `wan.state.degraded_policy` |
| [G12-E064](G12-E064.md) | Quarantine/disable control | P0 | validation | `wan.state.Quarantine` |
| [G12-E065](G12-E065.md) | Stale-controller/duplicate-owner protection | P1 | validation | `wan.state.FencedLease` |
| [G12-E066](G12-E066.md) | State migration/versioning | P1 | validation | `wan.state.migrate` |
| [G12-F067](G12-F067.md) | Versioned configuration schema | P0 | validation | `wan.config.SCHEMA`, `wan.config.validate` |
| [G12-F068](G12-F068.md) | Configuration validation before activation | P0 | validation | `wan.config.SCHEMA`, `wan.config.validate` |
| [G12-F069](G12-F069.md) | Environment/site overlays | P0 | validation | `wan.config.SCHEMA`, `wan.config.validate` |
| [G12-F070](G12-F070.md) | Atomic configuration reload/rollback | P0 | validation | `wan.config.SCHEMA`, `wan.config.validate` |
| [G12-F071](G12-F071.md) | Configuration provenance | P0 | validation | `wan.config.SCHEMA`, `wan.config.validate` |
| [G12-F072](G12-F072.md) | Policy for enabling/disabling traversal mechanisms | P1 | validation | `wan.config.SCHEMA`, `wan.config.validate` |
| [G12-F073](G12-F073.md) | Relay cost policy | P1 | validation | `wan.config.SCHEMA`, `wan.config.validate` |
| [G12-F074](G12-F074.md) | Feature flags with expiry/ownership | P1 | validation | `wan.config.SCHEMA`, `wan.config.validate` |
| [G12-G075](G12-G075.md) | Metrics exporter | P0 | validation | `wan.obs.Metrics`, `wan.obs.CATALOG` |
| [G12-G076](G12-G076.md) | Structured logging | P0 | validation | `wan.obs.EventLog`, `wan.obs.EVENTS` |
| [G12-G077](G12-G077.md) | Distributed trace propagation | P0 | validation | `wan.obs.Tracer`, `wan.obs.Span` |
| [G12-G078](G12-G078.md) | Health/readiness endpoint | P0 | validation | `wan.obs.HealthServer`, `wan.obs.readiness_from` |
| [G12-G079](G12-G079.md) | Reason codes | P0 | validation | `wan.reasons.REASONS`, `wan.reasons.reason_class` |
| [G12-G080](G12-G080.md) | Operator explain view | P1 | validation | `wan.obs.explain`, `wan.controller.Controller.explain` |
| [G12-G081](G12-G081.md) | Dashboards | P0 | implementation | `wan.obs.dashboard` |
| [G12-G082](G12-G082.md) | Alerts/SLO burn rules | P0 | implementation | `wan.obs.alert_rules`, `wan.obs.classify_incident` |
| [G12-G083](G12-G083.md) | Telemetry retention/sampling/privacy policy | P1 | implementation | `wan.obs.RETENTION` |
| [G12-G084](G12-G084.md) | Correlation with deployment/release lineage and topology graph | P1 | implementation | `wan.obs.lineage` |
| [G12-H085](G12-H085.md) | Unit tests for every transition and boundary value | P0 | validation | `evidence.run_tests` |
| [G12-H086](G12-H086.md) | Contract/schema tests for `PK_PATH_REQUEST/1`, `PK_PATH_STATE/1`, `PK_BACKOFF/1`, and relay accounting | P0 | validation | `wan.contracts.validate`, `wan.contracts.SCHEMAS` |
| [G12-H087](G12-H087.md) | Integration tests against real STUN/TURN implementations | P0 | design |  |
| [G12-H088](G12-H088.md) | NAT matrix test lab | P0 | validation | `lab.netlab.Lab`, `lab.scenarios.SCENARIOS` |
| [G12-H089](G12-H089.md) | Network-namespace/container emulation | P0 | implementation | `lab.netlab.Lab` |
| [G12-H090](G12-H090.md) | Partition/reconnect/flap tests | P0 | validation | `tests.test_c_quality` |
| [G12-H091](G12-H091.md) | DNS outage/poison/stale-cache tests | P0 | validation | `wan.dns.DnsServer` |
| [G12-H092](G12-H092.md) | IPv4/IPv6/NAT64 compatibility matrix | P0 | design |  |
| [G12-H093](G12-H093.md) | Firewall/UDP-blocked/captive-portal test scenarios | P0 | validation | `lab.scenarios.SCENARIOS` |
| [G12-H094](G12-H094.md) | Fuzz tests | P0 | validation | `tests.test_h_engineering.FuzzTest` |
| [G12-H095](G12-H095.md) | Concurrency/race tests | P0 | validation | `tests.test_h_engineering.ConcurrencyTest` |
| [G12-H096](G12-H096.md) | Security tests | P0 | validation | `tests.test_h_engineering.SecurityNegativeTest` |
| [G12-H097](G12-H097.md) | Long-duration soak tests | P1 | design |  |
| [G12-H098](G12-H098.md) | Fleet-scale retry-storm test | P1 | validation | `tests.test_h_engineering.RetryStormTest` |
| [G12-H099](G12-H099.md) | Benchmarks | P1 | validation | `evidence.bench` |
| [G12-H100](G12-H100.md) | Machine-readable production acceptance evidence | P0 | validation | `evidence.evaluate` |
| [G12-I101](G12-I101.md) | Declared supported Python/runtime/platform matrix | P0 | validation | `pyproject.toml` |
| [G12-I102](G12-I102.md) | Reproducible package metadata/build | P0 | validation | `ops.build` |
| [G12-I103](G12-I103.md) | Pinned external dependency versions | P0 | validation | `pyproject.toml` |
| [G12-I104](G12-I104.md) | SBOM and provenance/signature generation | P0 | validation | `ops.sbom` |
| [G12-I105](G12-I105.md) | CI pipeline | P0 | validation | `ops.ci` |
| [G12-I106](G12-I106.md) | Vulnerability scanning and patch SLA | P0 | design |  |
| [G12-I107](G12-I107.md) | Canary/staged rollout/rollback mechanism | P0 | validation | `wan.rollout.Rollout` |
| [G12-I108](G12-I108.md) | Emergency-disable/kill switch | P0 | validation | `wan.rollout.KillSwitch` |
| [G12-I109](G12-I109.md) | Day-0 bootstrap runbook | P0 | validation | `docs.RUNBOOK_DAY0` |
| [G12-I110](G12-I110.md) | Day-1 deployment runbook | P0 | validation | `docs.RUNBOOK_DAY1` |
| [G12-I111](G12-I111.md) | Day-2 operations runbook | P0 | validation | `docs.RUNBOOK_DAY2` |
| [G12-I112](G12-I112.md) | Incident severity/paging/escalation matrix | P0 | validation | `docs.INCIDENT_MATRIX` |
| [G12-I113](G12-I113.md) | Backup/reconstruction guidance | P1 | validation | `docs.BACKUP_RECONSTRUCTION` |
| [G12-I114](G12-I114.md) | Compatibility matrix and end-of-life policy | P0 | validation | `docs.COMPATIBILITY_EOL` |
| [G12-I115](G12-I115.md) | Exception/waiver/technical-debt register | P0 | validation | `evidence.waivers`, `ops/waivers.json` |
| [G12-I116](G12-I116.md) | Formal production exit gate | P0 | validation | `evidence.evaluate`, `evidence.ci_gate` |
