# GAP-12 WAN Resilience & NAT Traversal — Professional Engineering Checklist

**Checklist baseline:** v4.2.0 missing-components inventory  
**Scope:** Production WAN resilience, multi-path connectivity, NAT traversal, identity/trust, operations, testing, and release readiness  
**Priority semantics:** **P0** = required before production; **P1** = strongly recommended; **P2** = advanced/optimization  

## Checklist usage and evidence rules

- A checkbox is complete only when implementation **and objective evidence** exist. Design intent or a skipped test is not completion.
- For P0 items, unresolved mandatory sub-checks block the production gate unless a time-bounded, approved waiver exists with compensating controls.
- Every evidence artifact should identify source revision, build/artifact digest, configuration generation, dependency versions, environment/topology, timestamp, and responsible automation/owner.
- Use `PASS`, `FAIL`, `NOT-EVIDENCED`, and `WAIVED` as machine-readable gate states. Do not coerce `SKIP`, `UNKNOWN`, or missing dependencies into `PASS`.
- Security-sensitive values (credentials, raw tokens, private keys, full endpoint details where restricted) must be redacted or referenced by secure identifier rather than embedded in evidence.
- Recommended tracking fields per component: `Owner`, `Status`, `Target release`, `Dependencies`, `Risk`, `Test evidence`, `Security review`, `Runbook`, `Waiver`, and `Last verified`.

## Global Definition of Done

- [ ] **G-DOD-01** All P0 components have completed implementation, security review, integration testing, operational documentation, and machine-readable production evidence.
- [ ] **G-DOD-02** No mandatory integration/security/network-emulation test is skipped because an external dependency or test environment is absent.
- [ ] **G-DOD-03** Path establishment and failover are bounded by explicit deadlines/retry budgets and cannot create unbounded retry, task, socket, memory, or telemetry growth.
- [ ] **G-DOD-04** Identity, encryption, authorization, egress policy, secrets handling, and replay/abuse controls apply consistently to direct, hole-punched, translated, TCP/QUIC, and relayed paths.
- [ ] **G-DOD-05** IPv4, IPv6, dual-stack, NAT64/464XLAT, representative NAT/CGNAT, UDP-blocked, DNS-degraded, route-change, and relay scenarios are covered by repeatable tests.
- [ ] **G-DOD-06** Operators can explain every automated selection/failover decision using stable reason codes and correlated telemetry without exposing protected endpoint or credential data.
- [ ] **G-DOD-07** Release artifacts are reproducible/traceable, dependency-pinned, SBOM/provenance-covered, canary deployable, rollbackable, and emergency-disable capable.

## A. Concrete NAT traversal and transport adapters

### 1. STUN client — P0

**Component ID:** `G12-A001`  
**Objective:** STUN client for server-reflexive address discovery and binding behavior tests.  
**Standards/compatibility note:** Primary standards anchor: STUN (RFC 8489).  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-A001-01** Implement RFC 8489-compatible Binding transactions, transaction-ID matching, XOR-MAPPED-ADDRESS parsing, MESSAGE-INTEGRITY/FINGERPRINT handling when configured, and retransmission timing appropriate to the selected transport.
- [ ] **G12-A001-02** Verify discovery against multiple independent STUN servers and distinguish server failure, DNS failure, blocked UDP, malformed response, and mapping inconsistency.
- [ ] **G12-A001-03** Map the component to the applicable wire protocol, RFC/specification, message types, timers, error codes, and interoperability expectations; record intentional deviations as versioned architecture decisions.
- [ ] **G12-A001-04** Define candidate/address/socket ownership, creation and teardown rules, interface binding, IPv4/IPv6 behavior, port allocation, and resource ceilings for every traversal attempt.
- [ ] **G12-A001-05** Implement explicit transaction identifiers, timeout/retransmission behavior, cancellation, duplicate-response handling, late-packet handling, and idempotent cleanup.
- [ ] **G12-A001-06** Define protocol downgrade/fallback ordering and ensure a failed mechanism cannot silently bypass security policy, identity requirements, or configured egress restrictions.
- [ ] **G12-A001-07** Verify behavior across endpoint-independent, address-dependent, port-dependent, symmetric NAT, CGNAT, IPv6-only, NAT64, UDP-blocked, TCP-only, and captive/walled networks as applicable.
- [ ] **G12-A001-08** Capture packet-level interoperability evidence (pcap or equivalent test artifact) for success, timeout, refusal, authentication failure, mapping change, and teardown paths.
- [ ] **G12-A001-09** Implement and document the exact behavior required by this inventory item: **STUN client for server-reflexive address discovery and binding behavior tests**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-A001-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-A001-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-A001-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-A001-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-A001-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-A001-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-A001-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-A001-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-A001-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-A001-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-A001-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-A001-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-A001-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-A001`.

### 2. TURN client — P0

**Component ID:** `G12-A002`  
**Objective:** TURN client with authenticated allocations, permissions, channels, refresh, and expiry handling.  
**Standards/compatibility note:** Primary standards anchor: TURN (RFC 8656) with STUN framing/semantics.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-A002-01** Implement Allocate, Refresh, CreatePermission, ChannelBind, Send/Data indications, channel-data framing, allocation expiry, and deterministic teardown; enforce authenticated access and realm/nonce handling.
- [ ] **G12-A002-02** Validate UDP/TCP/TLS TURN transports required by policy, permission/channel refresh timers, quota accounting, server failover, and credential rotation without orphaning allocations.
- [ ] **G12-A002-03** Map the component to the applicable wire protocol, RFC/specification, message types, timers, error codes, and interoperability expectations; record intentional deviations as versioned architecture decisions.
- [ ] **G12-A002-04** Define candidate/address/socket ownership, creation and teardown rules, interface binding, IPv4/IPv6 behavior, port allocation, and resource ceilings for every traversal attempt.
- [ ] **G12-A002-05** Implement explicit transaction identifiers, timeout/retransmission behavior, cancellation, duplicate-response handling, late-packet handling, and idempotent cleanup.
- [ ] **G12-A002-06** Define protocol downgrade/fallback ordering and ensure a failed mechanism cannot silently bypass security policy, identity requirements, or configured egress restrictions.
- [ ] **G12-A002-07** Verify behavior across endpoint-independent, address-dependent, port-dependent, symmetric NAT, CGNAT, IPv6-only, NAT64, UDP-blocked, TCP-only, and captive/walled networks as applicable.
- [ ] **G12-A002-08** Capture packet-level interoperability evidence (pcap or equivalent test artifact) for success, timeout, refusal, authentication failure, mapping change, and teardown paths.
- [ ] **G12-A002-09** Implement and document the exact behavior required by this inventory item: **TURN client with authenticated allocations, permissions, channels, refresh, and expiry handling**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-A002-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-A002-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-A002-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-A002-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-A002-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-A002-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-A002-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-A002-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-A002-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-A002-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-A002-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-A002-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-A002-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-A002`.

### 3. ICE-compatible candidate gathering/checking state machine — P0

**Component ID:** `G12-A003`  
**Objective:** ICE-compatible candidate gathering/checking state machine or a documented equivalent.  
**Standards/compatibility note:** Primary standards anchor: ICE (RFC 8445) or a formally documented equivalent state machine.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-A003-01** Model host, server-reflexive, peer-reflexive, and relay candidates with stable foundations/priorities; implement checklist construction, pair states, triggered checks, nomination, role handling, and consent freshness or an explicitly documented equivalent.
- [ ] **G12-A003-02** Prove deterministic candidate pruning and bounded pair counts so malicious or pathological candidate sets cannot cause combinatorial explosion.
- [ ] **G12-A003-03** Map the component to the applicable wire protocol, RFC/specification, message types, timers, error codes, and interoperability expectations; record intentional deviations as versioned architecture decisions.
- [ ] **G12-A003-04** Define candidate/address/socket ownership, creation and teardown rules, interface binding, IPv4/IPv6 behavior, port allocation, and resource ceilings for every traversal attempt.
- [ ] **G12-A003-05** Implement explicit transaction identifiers, timeout/retransmission behavior, cancellation, duplicate-response handling, late-packet handling, and idempotent cleanup.
- [ ] **G12-A003-06** Define protocol downgrade/fallback ordering and ensure a failed mechanism cannot silently bypass security policy, identity requirements, or configured egress restrictions.
- [ ] **G12-A003-07** Verify behavior across endpoint-independent, address-dependent, port-dependent, symmetric NAT, CGNAT, IPv6-only, NAT64, UDP-blocked, TCP-only, and captive/walled networks as applicable.
- [ ] **G12-A003-08** Capture packet-level interoperability evidence (pcap or equivalent test artifact) for success, timeout, refusal, authentication failure, mapping change, and teardown paths.
- [ ] **G12-A003-09** Implement and document the exact behavior required by this inventory item: **ICE-compatible candidate gathering/checking state machine or a documented equivalent**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-A003-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-A003-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-A003-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-A003-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-A003-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-A003-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-A003-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-A003-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-A003-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-A003-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-A003-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-A003-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-A003-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-A003`.

### 4. UDP hole-punch implementation — P0

**Component ID:** `G12-A004`  
**Objective:** UDP hole-punch implementation with simultaneous-open coordination.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-A004-01** Coordinate simultaneous outbound probes using authenticated rendezvous metadata; randomize/limit punch schedules and close unused sockets promptly.
- [ ] **G12-A004-02** Handle mapping/port changes during the punch window and record whether failure was caused by coordination, NAT filtering, local firewall, or remote unreachability.
- [ ] **G12-A004-03** Map the component to the applicable wire protocol, RFC/specification, message types, timers, error codes, and interoperability expectations; record intentional deviations as versioned architecture decisions.
- [ ] **G12-A004-04** Define candidate/address/socket ownership, creation and teardown rules, interface binding, IPv4/IPv6 behavior, port allocation, and resource ceilings for every traversal attempt.
- [ ] **G12-A004-05** Implement explicit transaction identifiers, timeout/retransmission behavior, cancellation, duplicate-response handling, late-packet handling, and idempotent cleanup.
- [ ] **G12-A004-06** Define protocol downgrade/fallback ordering and ensure a failed mechanism cannot silently bypass security policy, identity requirements, or configured egress restrictions.
- [ ] **G12-A004-07** Verify behavior across endpoint-independent, address-dependent, port-dependent, symmetric NAT, CGNAT, IPv6-only, NAT64, UDP-blocked, TCP-only, and captive/walled networks as applicable.
- [ ] **G12-A004-08** Capture packet-level interoperability evidence (pcap or equivalent test artifact) for success, timeout, refusal, authentication failure, mapping change, and teardown paths.
- [ ] **G12-A004-09** Implement and document the exact behavior required by this inventory item: **UDP hole-punch implementation with simultaneous-open coordination**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-A004-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-A004-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-A004-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-A004-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-A004-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-A004-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-A004-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-A004-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-A004-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-A004-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-A004-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-A004-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-A004-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-A004`.

### 5. TCP fallback / traversal adapter — P0

**Component ID:** `G12-A005`  
**Objective:** TCP fallback / traversal adapter for networks that block UDP.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-A005-01** Define connect-racing, SYN/connect timeout, proxy/VPN interaction, half-open cleanup, keepalive, backpressure, and failure promotion rules for TCP paths.
- [ ] **G12-A005-02** Verify fallback does not create head-of-line or indefinite-connect behavior that blocks higher-priority strategies.
- [ ] **G12-A005-03** Map the component to the applicable wire protocol, RFC/specification, message types, timers, error codes, and interoperability expectations; record intentional deviations as versioned architecture decisions.
- [ ] **G12-A005-04** Define candidate/address/socket ownership, creation and teardown rules, interface binding, IPv4/IPv6 behavior, port allocation, and resource ceilings for every traversal attempt.
- [ ] **G12-A005-05** Implement explicit transaction identifiers, timeout/retransmission behavior, cancellation, duplicate-response handling, late-packet handling, and idempotent cleanup.
- [ ] **G12-A005-06** Define protocol downgrade/fallback ordering and ensure a failed mechanism cannot silently bypass security policy, identity requirements, or configured egress restrictions.
- [ ] **G12-A005-07** Verify behavior across endpoint-independent, address-dependent, port-dependent, symmetric NAT, CGNAT, IPv6-only, NAT64, UDP-blocked, TCP-only, and captive/walled networks as applicable.
- [ ] **G12-A005-08** Capture packet-level interoperability evidence (pcap or equivalent test artifact) for success, timeout, refusal, authentication failure, mapping change, and teardown paths.
- [ ] **G12-A005-09** Implement and document the exact behavior required by this inventory item: **TCP fallback / traversal adapter for networks that block UDP**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-A005-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-A005-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-A005-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-A005-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-A005-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-A005-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-A005-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-A005-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-A005-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-A005-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-A005-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-A005-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-A005-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-A005`.

### 6. NAT behavior classifier — P0

**Component ID:** `G12-A006`  
**Objective:** NAT behavior classifier covering endpoint-independent, address-dependent, port-dependent, and symmetric mappings/filtering.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-A006-01** Classify mapping and filtering behavior independently using controlled multi-address/multi-port observations; represent uncertainty rather than forcing an unsupported NAT label.
- [ ] **G12-A006-02** Expire classification when interface, gateway, public address, or relevant mapping behavior changes.
- [ ] **G12-A006-03** Map the component to the applicable wire protocol, RFC/specification, message types, timers, error codes, and interoperability expectations; record intentional deviations as versioned architecture decisions.
- [ ] **G12-A006-04** Define candidate/address/socket ownership, creation and teardown rules, interface binding, IPv4/IPv6 behavior, port allocation, and resource ceilings for every traversal attempt.
- [ ] **G12-A006-05** Implement explicit transaction identifiers, timeout/retransmission behavior, cancellation, duplicate-response handling, late-packet handling, and idempotent cleanup.
- [ ] **G12-A006-06** Define protocol downgrade/fallback ordering and ensure a failed mechanism cannot silently bypass security policy, identity requirements, or configured egress restrictions.
- [ ] **G12-A006-07** Verify behavior across endpoint-independent, address-dependent, port-dependent, symmetric NAT, CGNAT, IPv6-only, NAT64, UDP-blocked, TCP-only, and captive/walled networks as applicable.
- [ ] **G12-A006-08** Capture packet-level interoperability evidence (pcap or equivalent test artifact) for success, timeout, refusal, authentication failure, mapping change, and teardown paths.
- [ ] **G12-A006-09** Implement and document the exact behavior required by this inventory item: **NAT behavior classifier covering endpoint-independent, address-dependent, port-dependent, and symmetric mappings/filtering**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-A006-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-A006-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-A006-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-A006-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-A006-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-A006-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-A006-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-A006-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-A006-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-A006-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-A006-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-A006-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-A006-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-A006`.

### 7. Carrier-grade NAT detection/telemetry — P0

**Component ID:** `G12-A007`  
**Objective:** Carrier-grade NAT detection/telemetry so CGNAT-specific failure modes are explainable.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-A007-01** Detect/report CGNAT indicators without relying on a single heuristic; preserve evidence such as observed public/private ranges, mapping behavior, and upstream characteristics where permitted.
- [ ] **G12-A007-02** Use CGNAT classification only as a policy/diagnostic signal and never as proof of peer identity or exact carrier topology.
- [ ] **G12-A007-03** Map the component to the applicable wire protocol, RFC/specification, message types, timers, error codes, and interoperability expectations; record intentional deviations as versioned architecture decisions.
- [ ] **G12-A007-04** Define candidate/address/socket ownership, creation and teardown rules, interface binding, IPv4/IPv6 behavior, port allocation, and resource ceilings for every traversal attempt.
- [ ] **G12-A007-05** Implement explicit transaction identifiers, timeout/retransmission behavior, cancellation, duplicate-response handling, late-packet handling, and idempotent cleanup.
- [ ] **G12-A007-06** Define protocol downgrade/fallback ordering and ensure a failed mechanism cannot silently bypass security policy, identity requirements, or configured egress restrictions.
- [ ] **G12-A007-07** Verify behavior across endpoint-independent, address-dependent, port-dependent, symmetric NAT, CGNAT, IPv6-only, NAT64, UDP-blocked, TCP-only, and captive/walled networks as applicable.
- [ ] **G12-A007-08** Capture packet-level interoperability evidence (pcap or equivalent test artifact) for success, timeout, refusal, authentication failure, mapping change, and teardown paths.
- [ ] **G12-A007-09** Implement and document the exact behavior required by this inventory item: **Carrier-grade NAT detection/telemetry so CGNAT-specific failure modes are explainable**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-A007-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-A007-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-A007-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-A007-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-A007-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-A007-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-A007-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-A007-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-A007-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-A007-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-A007-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-A007-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-A007-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-A007`.

### 8. PCP adapter — P1

**Component ID:** `G12-A008`  
**Objective:** PCP adapter for explicit port mappings when available.  
**Standards/compatibility note:** Primary standards anchor: Port Control Protocol (RFC 6887).  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-A008-01** Implement PCP request/response validation, epoch handling, mapping lifetime refresh, external-address changes, result-code handling, and safe deletion of owned mappings.
- [ ] **G12-A008-02** Bind mappings to the intended internal address/protocol/port and reject responses inconsistent with the active interface or transaction.
- [ ] **G12-A008-03** Map the component to the applicable wire protocol, RFC/specification, message types, timers, error codes, and interoperability expectations; record intentional deviations as versioned architecture decisions.
- [ ] **G12-A008-04** Define candidate/address/socket ownership, creation and teardown rules, interface binding, IPv4/IPv6 behavior, port allocation, and resource ceilings for every traversal attempt.
- [ ] **G12-A008-05** Implement explicit transaction identifiers, timeout/retransmission behavior, cancellation, duplicate-response handling, late-packet handling, and idempotent cleanup.
- [ ] **G12-A008-06** Define protocol downgrade/fallback ordering and ensure a failed mechanism cannot silently bypass security policy, identity requirements, or configured egress restrictions.
- [ ] **G12-A008-07** Verify behavior across endpoint-independent, address-dependent, port-dependent, symmetric NAT, CGNAT, IPv6-only, NAT64, UDP-blocked, TCP-only, and captive/walled networks as applicable.
- [ ] **G12-A008-08** Capture packet-level interoperability evidence (pcap or equivalent test artifact) for success, timeout, refusal, authentication failure, mapping change, and teardown paths.
- [ ] **G12-A008-09** Implement and document the exact behavior required by this inventory item: **PCP adapter for explicit port mappings when available**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-A008-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-A008-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-A008-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-A008-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-A008-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-A008-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-A008-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-A008-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-A008-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-A008-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-A008-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-A008-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-A008-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-A008`.

### 9. NAT-PMP adapter — P1

**Component ID:** `G12-A009`  
**Objective:** NAT-PMP adapter for compatible gateways.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-A009-01** Implement public-address and mapping requests with epoch/result handling, bounded retry, lifetime refresh, and cleanup; scope operation to the selected local gateway only.
- [ ] **G12-A009-02** Treat NAT-PMP as optional capability with strict fallback and never expose gateway-discovered mappings outside configured policy.
- [ ] **G12-A009-03** Map the component to the applicable wire protocol, RFC/specification, message types, timers, error codes, and interoperability expectations; record intentional deviations as versioned architecture decisions.
- [ ] **G12-A009-04** Define candidate/address/socket ownership, creation and teardown rules, interface binding, IPv4/IPv6 behavior, port allocation, and resource ceilings for every traversal attempt.
- [ ] **G12-A009-05** Implement explicit transaction identifiers, timeout/retransmission behavior, cancellation, duplicate-response handling, late-packet handling, and idempotent cleanup.
- [ ] **G12-A009-06** Define protocol downgrade/fallback ordering and ensure a failed mechanism cannot silently bypass security policy, identity requirements, or configured egress restrictions.
- [ ] **G12-A009-07** Verify behavior across endpoint-independent, address-dependent, port-dependent, symmetric NAT, CGNAT, IPv6-only, NAT64, UDP-blocked, TCP-only, and captive/walled networks as applicable.
- [ ] **G12-A009-08** Capture packet-level interoperability evidence (pcap or equivalent test artifact) for success, timeout, refusal, authentication failure, mapping change, and teardown paths.
- [ ] **G12-A009-09** Implement and document the exact behavior required by this inventory item: **NAT-PMP adapter for compatible gateways**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-A009-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-A009-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-A009-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-A009-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-A009-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-A009-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-A009-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-A009-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-A009-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-A009-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-A009-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-A009-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-A009-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-A009`.

### 10. UPnP IGD adapter — P1

**Component ID:** `G12-A010`  
**Objective:** UPnP IGD adapter with strict local-network trust and policy controls.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-A010-01** Constrain SSDP discovery and SOAP control to trusted local interfaces/zones; validate device/service URLs and prevent arbitrary URL fetch/SSRF behavior.
- [ ] **G12-A010-02** Track mapping ownership, lease duration, collision behavior, gateway reboot/change, and deterministic removal of mappings created by this component.
- [ ] **G12-A010-03** Map the component to the applicable wire protocol, RFC/specification, message types, timers, error codes, and interoperability expectations; record intentional deviations as versioned architecture decisions.
- [ ] **G12-A010-04** Define candidate/address/socket ownership, creation and teardown rules, interface binding, IPv4/IPv6 behavior, port allocation, and resource ceilings for every traversal attempt.
- [ ] **G12-A010-05** Implement explicit transaction identifiers, timeout/retransmission behavior, cancellation, duplicate-response handling, late-packet handling, and idempotent cleanup.
- [ ] **G12-A010-06** Define protocol downgrade/fallback ordering and ensure a failed mechanism cannot silently bypass security policy, identity requirements, or configured egress restrictions.
- [ ] **G12-A010-07** Verify behavior across endpoint-independent, address-dependent, port-dependent, symmetric NAT, CGNAT, IPv6-only, NAT64, UDP-blocked, TCP-only, and captive/walled networks as applicable.
- [ ] **G12-A010-08** Capture packet-level interoperability evidence (pcap or equivalent test artifact) for success, timeout, refusal, authentication failure, mapping change, and teardown paths.
- [ ] **G12-A010-09** Implement and document the exact behavior required by this inventory item: **UPnP IGD adapter with strict local-network trust and policy controls**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-A010-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-A010-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-A010-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-A010-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-A010-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-A010-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-A010-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-A010-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-A010-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-A010-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-A010-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-A010-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-A010-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-A010`.

### 11. IPv6 direct-path support — P0

**Component ID:** `G12-A011`  
**Objective:** IPv6 direct-path support including global address/candidate discovery.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-A011-01** Gather only policy-eligible IPv6 addresses; handle temporary/privacy addresses, scope IDs, deprecation, preferred/valid lifetimes, and route reachability.
- [ ] **G12-A011-02** Do not assume globally scoped IPv6 implies inbound reachability; incorporate host/network firewall and peer-policy checks.
- [ ] **G12-A011-03** Map the component to the applicable wire protocol, RFC/specification, message types, timers, error codes, and interoperability expectations; record intentional deviations as versioned architecture decisions.
- [ ] **G12-A011-04** Define candidate/address/socket ownership, creation and teardown rules, interface binding, IPv4/IPv6 behavior, port allocation, and resource ceilings for every traversal attempt.
- [ ] **G12-A011-05** Implement explicit transaction identifiers, timeout/retransmission behavior, cancellation, duplicate-response handling, late-packet handling, and idempotent cleanup.
- [ ] **G12-A011-06** Define protocol downgrade/fallback ordering and ensure a failed mechanism cannot silently bypass security policy, identity requirements, or configured egress restrictions.
- [ ] **G12-A011-07** Verify behavior across endpoint-independent, address-dependent, port-dependent, symmetric NAT, CGNAT, IPv6-only, NAT64, UDP-blocked, TCP-only, and captive/walled networks as applicable.
- [ ] **G12-A011-08** Capture packet-level interoperability evidence (pcap or equivalent test artifact) for success, timeout, refusal, authentication failure, mapping change, and teardown paths.
- [ ] **G12-A011-09** Implement and document the exact behavior required by this inventory item: **IPv6 direct-path support including global address/candidate discovery**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-A011-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-A011-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-A011-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-A011-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-A011-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-A011-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-A011-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-A011-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-A011-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-A011-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-A011-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-A011-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-A011-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-A011`.

### 12. NAT64 / DNS64 compatibility — P1

**Component ID:** `G12-A012`  
**Objective:** NAT64 / DNS64 compatibility and detection.  
**Standards/compatibility note:** Primary standards anchors: NAT64 (RFC 6146) and DNS64 (RFC 6147).  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-A012-01** Detect NAT64/DNS64 behavior using standards-compatible discovery or controlled probes and keep synthesized-address handling separate from native IPv6 candidates.
- [ ] **G12-A012-02** Test resolver changes, prefix changes, IPv4 literals, DNSSEC interactions as applicable, and failover between native and translated connectivity.
- [ ] **G12-A012-03** Map the component to the applicable wire protocol, RFC/specification, message types, timers, error codes, and interoperability expectations; record intentional deviations as versioned architecture decisions.
- [ ] **G12-A012-04** Define candidate/address/socket ownership, creation and teardown rules, interface binding, IPv4/IPv6 behavior, port allocation, and resource ceilings for every traversal attempt.
- [ ] **G12-A012-05** Implement explicit transaction identifiers, timeout/retransmission behavior, cancellation, duplicate-response handling, late-packet handling, and idempotent cleanup.
- [ ] **G12-A012-06** Define protocol downgrade/fallback ordering and ensure a failed mechanism cannot silently bypass security policy, identity requirements, or configured egress restrictions.
- [ ] **G12-A012-07** Verify behavior across endpoint-independent, address-dependent, port-dependent, symmetric NAT, CGNAT, IPv6-only, NAT64, UDP-blocked, TCP-only, and captive/walled networks as applicable.
- [ ] **G12-A012-08** Capture packet-level interoperability evidence (pcap or equivalent test artifact) for success, timeout, refusal, authentication failure, mapping change, and teardown paths.
- [ ] **G12-A012-09** Implement and document the exact behavior required by this inventory item: **NAT64 / DNS64 compatibility and detection**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-A012-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-A012-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-A012-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-A012-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-A012-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-A012-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-A012-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-A012-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-A012-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-A012-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-A012-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-A012-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-A012-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-A012`.

### 13. 464XLAT/mobile-network compatibility testing — P1

**Component ID:** `G12-A013`  
**Objective:** 464XLAT/mobile-network compatibility testing .  
**Standards/compatibility note:** Primary standards anchor: 464XLAT (RFC 6877).  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-A013-01** Validate CLAT/PLAT behavior on representative mobile stacks, including interface transitions and IPv4-literal reachability through translation.
- [ ] **G12-A013-02** Capture platform-specific constraints so application policy does not incorrectly prefer an unavailable native IPv4 path.
- [ ] **G12-A013-03** Map the component to the applicable wire protocol, RFC/specification, message types, timers, error codes, and interoperability expectations; record intentional deviations as versioned architecture decisions.
- [ ] **G12-A013-04** Define candidate/address/socket ownership, creation and teardown rules, interface binding, IPv4/IPv6 behavior, port allocation, and resource ceilings for every traversal attempt.
- [ ] **G12-A013-05** Implement explicit transaction identifiers, timeout/retransmission behavior, cancellation, duplicate-response handling, late-packet handling, and idempotent cleanup.
- [ ] **G12-A013-06** Define protocol downgrade/fallback ordering and ensure a failed mechanism cannot silently bypass security policy, identity requirements, or configured egress restrictions.
- [ ] **G12-A013-07** Verify behavior across endpoint-independent, address-dependent, port-dependent, symmetric NAT, CGNAT, IPv6-only, NAT64, UDP-blocked, TCP-only, and captive/walled networks as applicable.
- [ ] **G12-A013-08** Capture packet-level interoperability evidence (pcap or equivalent test artifact) for success, timeout, refusal, authentication failure, mapping change, and teardown paths.
- [ ] **G12-A013-09** Implement and document the exact behavior required by this inventory item: **464XLAT/mobile-network compatibility testing **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-A013-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-A013-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-A013-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-A013-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-A013-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-A013-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-A013-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-A013-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-A013-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-A013-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-A013-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-A013-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-A013-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-A013`.

### 14. Dual-stack connection racing / Happy-Eyeballs policy — P0

**Component ID:** `G12-A014`  
**Objective:** Dual-stack connection racing / Happy-Eyeballs policy .  
**Standards/compatibility note:** Primary standards anchor: Happy Eyeballs v2 (RFC 8305) or current platform-equivalent policy.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-A014-01** Implement deterministic family/candidate racing with configurable delay, cancellation of losing attempts, connection reuse rules, and telemetry for selected family/path.
- [ ] **G12-A014-02** Avoid starvation of IPv6 or IPv4 during repeated failures by using bounded historical influence and fresh reachability evidence.
- [ ] **G12-A014-03** Map the component to the applicable wire protocol, RFC/specification, message types, timers, error codes, and interoperability expectations; record intentional deviations as versioned architecture decisions.
- [ ] **G12-A014-04** Define candidate/address/socket ownership, creation and teardown rules, interface binding, IPv4/IPv6 behavior, port allocation, and resource ceilings for every traversal attempt.
- [ ] **G12-A014-05** Implement explicit transaction identifiers, timeout/retransmission behavior, cancellation, duplicate-response handling, late-packet handling, and idempotent cleanup.
- [ ] **G12-A014-06** Define protocol downgrade/fallback ordering and ensure a failed mechanism cannot silently bypass security policy, identity requirements, or configured egress restrictions.
- [ ] **G12-A014-07** Verify behavior across endpoint-independent, address-dependent, port-dependent, symmetric NAT, CGNAT, IPv6-only, NAT64, UDP-blocked, TCP-only, and captive/walled networks as applicable.
- [ ] **G12-A014-08** Capture packet-level interoperability evidence (pcap or equivalent test artifact) for success, timeout, refusal, authentication failure, mapping change, and teardown paths.
- [ ] **G12-A014-09** Implement and document the exact behavior required by this inventory item: **Dual-stack connection racing / Happy-Eyeballs policy **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-A014-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-A014-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-A014-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-A014-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-A014-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-A014-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-A014-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-A014-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-A014-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-A014-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-A014-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-A014-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-A014-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-A014`.

### 15. QUIC transport adapter — P1

**Component ID:** `G12-A015`  
**Objective:** QUIC transport adapter with connection migration support where the data plane permits it.  
**Standards/compatibility note:** Primary standards anchor: QUIC transport (RFC 9000) plus the selected application mapping.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-A015-01** Validate QUIC version negotiation, handshake, idle timeout, path validation, anti-amplification, connection ID handling, migration, and stateless-reset behavior required by the selected library.
- [ ] **G12-A015-02** Verify migration across interface/address changes does not bypass peer identity, policy, congestion control, or relay-accounting requirements.
- [ ] **G12-A015-03** Map the component to the applicable wire protocol, RFC/specification, message types, timers, error codes, and interoperability expectations; record intentional deviations as versioned architecture decisions.
- [ ] **G12-A015-04** Define candidate/address/socket ownership, creation and teardown rules, interface binding, IPv4/IPv6 behavior, port allocation, and resource ceilings for every traversal attempt.
- [ ] **G12-A015-05** Implement explicit transaction identifiers, timeout/retransmission behavior, cancellation, duplicate-response handling, late-packet handling, and idempotent cleanup.
- [ ] **G12-A015-06** Define protocol downgrade/fallback ordering and ensure a failed mechanism cannot silently bypass security policy, identity requirements, or configured egress restrictions.
- [ ] **G12-A015-07** Verify behavior across endpoint-independent, address-dependent, port-dependent, symmetric NAT, CGNAT, IPv6-only, NAT64, UDP-blocked, TCP-only, and captive/walled networks as applicable.
- [ ] **G12-A015-08** Capture packet-level interoperability evidence (pcap or equivalent test artifact) for success, timeout, refusal, authentication failure, mapping change, and teardown paths.
- [ ] **G12-A015-09** Implement and document the exact behavior required by this inventory item: **QUIC transport adapter with connection migration support where the data plane permits it**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-A015-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-A015-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-A015-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-A015-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-A015-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-A015-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-A015-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-A015-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-A015-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-A015-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-A015-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-A015-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-A015-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-A015`.

### 16. TLS/TCP transport fallback adapter — P1

**Component ID:** `G12-A016`  
**Objective:** TLS/TCP transport fallback adapter where QUIC/UDP is unavailable.  
**Standards/compatibility note:** Primary standards anchor: TLS 1.3 (RFC 8446) where supported by platform policy.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-A016-01** Validate QUIC version negotiation, handshake, idle timeout, path validation, anti-amplification, connection ID handling, migration, and stateless-reset behavior required by the selected library.
- [ ] **G12-A016-02** Verify migration across interface/address changes does not bypass peer identity, policy, congestion control, or relay-accounting requirements.
- [ ] **G12-A016-03** Require authenticated TLS with approved protocol/cipher policy, certificate/identity verification, hostname/service binding, session resumption policy, and revocation/rotation behavior.
- [ ] **G12-A016-04** Bound handshake/connect/read/write timeouts and ensure TLS alerts and certificate failures produce distinct reason codes from generic network failures.
- [ ] **G12-A016-05** Map the component to the applicable wire protocol, RFC/specification, message types, timers, error codes, and interoperability expectations; record intentional deviations as versioned architecture decisions.
- [ ] **G12-A016-06** Define candidate/address/socket ownership, creation and teardown rules, interface binding, IPv4/IPv6 behavior, port allocation, and resource ceilings for every traversal attempt.
- [ ] **G12-A016-07** Implement explicit transaction identifiers, timeout/retransmission behavior, cancellation, duplicate-response handling, late-packet handling, and idempotent cleanup.
- [ ] **G12-A016-08** Define protocol downgrade/fallback ordering and ensure a failed mechanism cannot silently bypass security policy, identity requirements, or configured egress restrictions.
- [ ] **G12-A016-09** Verify behavior across endpoint-independent, address-dependent, port-dependent, symmetric NAT, CGNAT, IPv6-only, NAT64, UDP-blocked, TCP-only, and captive/walled networks as applicable.
- [ ] **G12-A016-10** Capture packet-level interoperability evidence (pcap or equivalent test artifact) for success, timeout, refusal, authentication failure, mapping change, and teardown paths.
- [ ] **G12-A016-11** Implement and document the exact behavior required by this inventory item: **TLS/TCP transport fallback adapter where QUIC/UDP is unavailable**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-A016-12** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-A016-13** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-A016-14** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-A016-15** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-A016-16** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-A016-17** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-A016-18** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-A016-19** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-A016-20** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-A016-21** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-A016-22** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-A016-23** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-A016-24** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-A016`.

## B. Link, interface, and routing management

### 17. Local interface inventory — P0

**Component ID:** `G12-B017`  
**Objective:** Local interface inventory for Ethernet, Wi-Fi, cellular, VPN/tunnel, and virtual adapters.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-B017-01** Build an immutable local-network snapshot model containing interface identity, link state, addresses/prefixes, DNS configuration, route metrics, MTU, gateway, VPN/tunnel state, and network cost/metering attributes where available.
- [ ] **G12-B017-02** Consume operating-system network-change notifications and reconcile them with periodic full snapshots so missed or coalesced events cannot leave stale routing state indefinitely.
- [ ] **G12-B017-03** Define event coalescing, debounce, hysteresis, and minimum-stability intervals so transient Wi-Fi/cellular/VPN changes do not cause path-selection thrash.
- [ ] **G12-B017-04** Make interface/route selection explicit at socket creation and probe time; verify source-address pinning remains correct after route-table churn.
- [ ] **G12-B017-05** Separate observation from mutation: diagnostics may explain local firewall, DNS, or routing conditions but must not modify host/network policy unless an authorized control explicitly permits it.
- [ ] **G12-B017-06** Test suspend/resume, interface rename, DHCP renewal, IPv6 privacy-address rotation, VPN connect/disconnect, metric changes, gateway replacement, and simultaneous multi-interface transitions.
- [ ] **G12-B017-07** Implement and document the exact behavior required by this inventory item: **Local interface inventory for Ethernet, Wi-Fi, cellular, VPN/tunnel, and virtual adapters**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-B017-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-B017-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-B017-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-B017-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-B017-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-B017-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-B017-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-B017-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-B017-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-B017-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-B017-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-B017-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-B017-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-B017`.

### 18. Default-route and route-change watcher — P0

**Component ID:** `G12-B018`  
**Objective:** Default-route and route-change watcher .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-B018-01** Build an immutable local-network snapshot model containing interface identity, link state, addresses/prefixes, DNS configuration, route metrics, MTU, gateway, VPN/tunnel state, and network cost/metering attributes where available.
- [ ] **G12-B018-02** Consume operating-system network-change notifications and reconcile them with periodic full snapshots so missed or coalesced events cannot leave stale routing state indefinitely.
- [ ] **G12-B018-03** Define event coalescing, debounce, hysteresis, and minimum-stability intervals so transient Wi-Fi/cellular/VPN changes do not cause path-selection thrash.
- [ ] **G12-B018-04** Make interface/route selection explicit at socket creation and probe time; verify source-address pinning remains correct after route-table churn.
- [ ] **G12-B018-05** Separate observation from mutation: diagnostics may explain local firewall, DNS, or routing conditions but must not modify host/network policy unless an authorized control explicitly permits it.
- [ ] **G12-B018-06** Test suspend/resume, interface rename, DHCP renewal, IPv6 privacy-address rotation, VPN connect/disconnect, metric changes, gateway replacement, and simultaneous multi-interface transitions.
- [ ] **G12-B018-07** Implement and document the exact behavior required by this inventory item: **Default-route and route-change watcher **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-B018-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-B018-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-B018-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-B018-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-B018-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-B018-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-B018-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-B018-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-B018-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-B018-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-B018-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-B018-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-B018-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-B018`.

### 19. Multi-WAN uplink manager — P0

**Component ID:** `G12-B019`  
**Objective:** Multi-WAN uplink manager with priority and policy constraints.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-B019-01** Build an immutable local-network snapshot model containing interface identity, link state, addresses/prefixes, DNS configuration, route metrics, MTU, gateway, VPN/tunnel state, and network cost/metering attributes where available.
- [ ] **G12-B019-02** Consume operating-system network-change notifications and reconcile them with periodic full snapshots so missed or coalesced events cannot leave stale routing state indefinitely.
- [ ] **G12-B019-03** Define event coalescing, debounce, hysteresis, and minimum-stability intervals so transient Wi-Fi/cellular/VPN changes do not cause path-selection thrash.
- [ ] **G12-B019-04** Make interface/route selection explicit at socket creation and probe time; verify source-address pinning remains correct after route-table churn.
- [ ] **G12-B019-05** Separate observation from mutation: diagnostics may explain local firewall, DNS, or routing conditions but must not modify host/network policy unless an authorized control explicitly permits it.
- [ ] **G12-B019-06** Test suspend/resume, interface rename, DHCP renewal, IPv6 privacy-address rotation, VPN connect/disconnect, metric changes, gateway replacement, and simultaneous multi-interface transitions.
- [ ] **G12-B019-07** Implement and document the exact behavior required by this inventory item: **Multi-WAN uplink manager with priority and policy constraints**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-B019-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-B019-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-B019-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-B019-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-B019-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-B019-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-B019-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-B019-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-B019-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-B019-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-B019-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-B019-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-B019-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-B019`.

### 20. Link-flap debounce/hysteresis — P0

**Component ID:** `G12-B020`  
**Objective:** Link-flap debounce/hysteresis to avoid oscillating path decisions.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-B020-01** Build an immutable local-network snapshot model containing interface identity, link state, addresses/prefixes, DNS configuration, route metrics, MTU, gateway, VPN/tunnel state, and network cost/metering attributes where available.
- [ ] **G12-B020-02** Consume operating-system network-change notifications and reconcile them with periodic full snapshots so missed or coalesced events cannot leave stale routing state indefinitely.
- [ ] **G12-B020-03** Define event coalescing, debounce, hysteresis, and minimum-stability intervals so transient Wi-Fi/cellular/VPN changes do not cause path-selection thrash.
- [ ] **G12-B020-04** Make interface/route selection explicit at socket creation and probe time; verify source-address pinning remains correct after route-table churn.
- [ ] **G12-B020-05** Separate observation from mutation: diagnostics may explain local firewall, DNS, or routing conditions but must not modify host/network policy unless an authorized control explicitly permits it.
- [ ] **G12-B020-06** Test suspend/resume, interface rename, DHCP renewal, IPv6 privacy-address rotation, VPN connect/disconnect, metric changes, gateway replacement, and simultaneous multi-interface transitions.
- [ ] **G12-B020-07** Implement and document the exact behavior required by this inventory item: **Link-flap debounce/hysteresis to avoid oscillating path decisions**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-B020-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-B020-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-B020-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-B020-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-B020-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-B020-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-B020-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-B020-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-B020-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-B020-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-B020-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-B020-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-B020-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-B020`.

### 21. Connection migration — P1

**Component ID:** `G12-B021`  
**Objective:** Connection migration between uplinks without unnecessarily discarding healthy sessions.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-B021-01** Build an immutable local-network snapshot model containing interface identity, link state, addresses/prefixes, DNS configuration, route metrics, MTU, gateway, VPN/tunnel state, and network cost/metering attributes where available.
- [ ] **G12-B021-02** Consume operating-system network-change notifications and reconcile them with periodic full snapshots so missed or coalesced events cannot leave stale routing state indefinitely.
- [ ] **G12-B021-03** Define event coalescing, debounce, hysteresis, and minimum-stability intervals so transient Wi-Fi/cellular/VPN changes do not cause path-selection thrash.
- [ ] **G12-B021-04** Make interface/route selection explicit at socket creation and probe time; verify source-address pinning remains correct after route-table churn.
- [ ] **G12-B021-05** Separate observation from mutation: diagnostics may explain local firewall, DNS, or routing conditions but must not modify host/network policy unless an authorized control explicitly permits it.
- [ ] **G12-B021-06** Test suspend/resume, interface rename, DHCP renewal, IPv6 privacy-address rotation, VPN connect/disconnect, metric changes, gateway replacement, and simultaneous multi-interface transitions.
- [ ] **G12-B021-07** Implement and document the exact behavior required by this inventory item: **Connection migration between uplinks without unnecessarily discarding healthy sessions**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-B021-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-B021-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-B021-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-B021-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-B021-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-B021-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-B021-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-B021-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-B021-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-B021-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-B021-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-B021-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-B021-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-B021`.

### 22. Source-address/interface pinning — P1

**Component ID:** `G12-B022`  
**Objective:** Source-address/interface pinning for probes and established paths.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-B022-01** Build an immutable local-network snapshot model containing interface identity, link state, addresses/prefixes, DNS configuration, route metrics, MTU, gateway, VPN/tunnel state, and network cost/metering attributes where available.
- [ ] **G12-B022-02** Consume operating-system network-change notifications and reconcile them with periodic full snapshots so missed or coalesced events cannot leave stale routing state indefinitely.
- [ ] **G12-B022-03** Define event coalescing, debounce, hysteresis, and minimum-stability intervals so transient Wi-Fi/cellular/VPN changes do not cause path-selection thrash.
- [ ] **G12-B022-04** Make interface/route selection explicit at socket creation and probe time; verify source-address pinning remains correct after route-table churn.
- [ ] **G12-B022-05** Separate observation from mutation: diagnostics may explain local firewall, DNS, or routing conditions but must not modify host/network policy unless an authorized control explicitly permits it.
- [ ] **G12-B022-06** Test suspend/resume, interface rename, DHCP renewal, IPv6 privacy-address rotation, VPN connect/disconnect, metric changes, gateway replacement, and simultaneous multi-interface transitions.
- [ ] **G12-B022-07** Implement and document the exact behavior required by this inventory item: **Source-address/interface pinning for probes and established paths**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-B022-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-B022-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-B022-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-B022-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-B022-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-B022-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-B022-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-B022-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-B022-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-B022-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-B022-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-B022-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-B022-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-B022`.

### 23. DNS resolver resilience — P0

**Component ID:** `G12-B023`  
**Objective:** DNS resolver resilience with multiple resolvers, timeout policy, and stale-answer rules.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-B023-01** Implement resolver ordering/racing policy, bounded per-query and overall deadlines, negative caching, stale-answer rules, split-horizon awareness, and result provenance.
- [ ] **G12-B023-02** Prevent retry multiplication across resolver, transport, and application layers; cap concurrent queries and preserve reason codes for NXDOMAIN, timeout, SERVFAIL, validation failure, and local configuration errors.
- [ ] **G12-B023-03** Build an immutable local-network snapshot model containing interface identity, link state, addresses/prefixes, DNS configuration, route metrics, MTU, gateway, VPN/tunnel state, and network cost/metering attributes where available.
- [ ] **G12-B023-04** Consume operating-system network-change notifications and reconcile them with periodic full snapshots so missed or coalesced events cannot leave stale routing state indefinitely.
- [ ] **G12-B023-05** Define event coalescing, debounce, hysteresis, and minimum-stability intervals so transient Wi-Fi/cellular/VPN changes do not cause path-selection thrash.
- [ ] **G12-B023-06** Make interface/route selection explicit at socket creation and probe time; verify source-address pinning remains correct after route-table churn.
- [ ] **G12-B023-07** Separate observation from mutation: diagnostics may explain local firewall, DNS, or routing conditions but must not modify host/network policy unless an authorized control explicitly permits it.
- [ ] **G12-B023-08** Test suspend/resume, interface rename, DHCP renewal, IPv6 privacy-address rotation, VPN connect/disconnect, metric changes, gateway replacement, and simultaneous multi-interface transitions.
- [ ] **G12-B023-09** Implement and document the exact behavior required by this inventory item: **DNS resolver resilience with multiple resolvers, timeout policy, and stale-answer rules**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-B023-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-B023-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-B023-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-B023-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-B023-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-B023-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-B023-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-B023-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-B023-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-B023-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-B023-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-B023-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-B023-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-B023`.

### 24. Captive-portal / walled-garden detection — P1

**Component ID:** `G12-B024`  
**Objective:** Captive-portal / walled-garden detection .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-B024-01** Build an immutable local-network snapshot model containing interface identity, link state, addresses/prefixes, DNS configuration, route metrics, MTU, gateway, VPN/tunnel state, and network cost/metering attributes where available.
- [ ] **G12-B024-02** Consume operating-system network-change notifications and reconcile them with periodic full snapshots so missed or coalesced events cannot leave stale routing state indefinitely.
- [ ] **G12-B024-03** Define event coalescing, debounce, hysteresis, and minimum-stability intervals so transient Wi-Fi/cellular/VPN changes do not cause path-selection thrash.
- [ ] **G12-B024-04** Make interface/route selection explicit at socket creation and probe time; verify source-address pinning remains correct after route-table churn.
- [ ] **G12-B024-05** Separate observation from mutation: diagnostics may explain local firewall, DNS, or routing conditions but must not modify host/network policy unless an authorized control explicitly permits it.
- [ ] **G12-B024-06** Test suspend/resume, interface rename, DHCP renewal, IPv6 privacy-address rotation, VPN connect/disconnect, metric changes, gateway replacement, and simultaneous multi-interface transitions.
- [ ] **G12-B024-07** Implement and document the exact behavior required by this inventory item: **Captive-portal / walled-garden detection **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-B024-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-B024-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-B024-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-B024-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-B024-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-B024-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-B024-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-B024-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-B024-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-B024-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-B024-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-B024-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-B024-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-B024`.

### 25. Path MTU discovery and black-hole detection — P0

**Component ID:** `G12-B025`  
**Objective:** Path MTU discovery and black-hole detection .  
**Standards/compatibility note:** Use transport-appropriate PMTUD/PLPMTUD mechanisms; IPv6 PMTUD is defined in RFC 8201 and PLPMTUD in RFC 8899.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-B025-01** Implement PMTU/PLPMTUD behavior appropriate to each transport, cache PMTU by path identity with safe expiry, and detect black holes where ICMP feedback is filtered.
- [ ] **G12-B025-02** Test encapsulation overhead for VPN/tunnel/relay paths and ensure packetization never assumes the physical-interface MTU is the usable end-to-end MTU.
- [ ] **G12-B025-03** Build an immutable local-network snapshot model containing interface identity, link state, addresses/prefixes, DNS configuration, route metrics, MTU, gateway, VPN/tunnel state, and network cost/metering attributes where available.
- [ ] **G12-B025-04** Consume operating-system network-change notifications and reconcile them with periodic full snapshots so missed or coalesced events cannot leave stale routing state indefinitely.
- [ ] **G12-B025-05** Define event coalescing, debounce, hysteresis, and minimum-stability intervals so transient Wi-Fi/cellular/VPN changes do not cause path-selection thrash.
- [ ] **G12-B025-06** Make interface/route selection explicit at socket creation and probe time; verify source-address pinning remains correct after route-table churn.
- [ ] **G12-B025-07** Separate observation from mutation: diagnostics may explain local firewall, DNS, or routing conditions but must not modify host/network policy unless an authorized control explicitly permits it.
- [ ] **G12-B025-08** Test suspend/resume, interface rename, DHCP renewal, IPv6 privacy-address rotation, VPN connect/disconnect, metric changes, gateway replacement, and simultaneous multi-interface transitions.
- [ ] **G12-B025-09** Implement and document the exact behavior required by this inventory item: **Path MTU discovery and black-hole detection **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-B025-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-B025-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-B025-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-B025-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-B025-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-B025-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-B025-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-B025-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-B025-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-B025-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-B025-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-B025-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-B025-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-B025`.

### 26. MSS/MTU policy integration — P1

**Component ID:** `G12-B026`  
**Objective:** MSS/MTU policy integration for tunnel/relay paths.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-B026-01** Build an immutable local-network snapshot model containing interface identity, link state, addresses/prefixes, DNS configuration, route metrics, MTU, gateway, VPN/tunnel state, and network cost/metering attributes where available.
- [ ] **G12-B026-02** Consume operating-system network-change notifications and reconcile them with periodic full snapshots so missed or coalesced events cannot leave stale routing state indefinitely.
- [ ] **G12-B026-03** Define event coalescing, debounce, hysteresis, and minimum-stability intervals so transient Wi-Fi/cellular/VPN changes do not cause path-selection thrash.
- [ ] **G12-B026-04** Make interface/route selection explicit at socket creation and probe time; verify source-address pinning remains correct after route-table churn.
- [ ] **G12-B026-05** Separate observation from mutation: diagnostics may explain local firewall, DNS, or routing conditions but must not modify host/network policy unless an authorized control explicitly permits it.
- [ ] **G12-B026-06** Test suspend/resume, interface rename, DHCP renewal, IPv6 privacy-address rotation, VPN connect/disconnect, metric changes, gateway replacement, and simultaneous multi-interface transitions.
- [ ] **G12-B026-07** Implement and document the exact behavior required by this inventory item: **MSS/MTU policy integration for tunnel/relay paths**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-B026-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-B026-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-B026-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-B026-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-B026-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-B026-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-B026-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-B026-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-B026-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-B026-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-B026-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-B026-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-B026-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-B026`.

### 27. Local firewall reachability diagnostics — P1

**Component ID:** `G12-B027`  
**Objective:** Local firewall reachability diagnostics that explain blocked ingress/egress without modifying policy implicitly.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-B027-01** Build an immutable local-network snapshot model containing interface identity, link state, addresses/prefixes, DNS configuration, route metrics, MTU, gateway, VPN/tunnel state, and network cost/metering attributes where available.
- [ ] **G12-B027-02** Consume operating-system network-change notifications and reconcile them with periodic full snapshots so missed or coalesced events cannot leave stale routing state indefinitely.
- [ ] **G12-B027-03** Define event coalescing, debounce, hysteresis, and minimum-stability intervals so transient Wi-Fi/cellular/VPN changes do not cause path-selection thrash.
- [ ] **G12-B027-04** Make interface/route selection explicit at socket creation and probe time; verify source-address pinning remains correct after route-table churn.
- [ ] **G12-B027-05** Separate observation from mutation: diagnostics may explain local firewall, DNS, or routing conditions but must not modify host/network policy unless an authorized control explicitly permits it.
- [ ] **G12-B027-06** Test suspend/resume, interface rename, DHCP renewal, IPv6 privacy-address rotation, VPN connect/disconnect, metric changes, gateway replacement, and simultaneous multi-interface transitions.
- [ ] **G12-B027-07** Implement and document the exact behavior required by this inventory item: **Local firewall reachability diagnostics that explain blocked ingress/egress without modifying policy implicitly**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-B027-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-B027-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-B027-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-B027-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-B027-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-B027-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-B027-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-B027-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-B027-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-B027-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-B027-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-B027-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-B027-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-B027`.

## C. Path-quality, selection, and session lifecycle

### 28. Per-strategy attempt deadlines and cancellation — P0

**Component ID:** `G12-C028`  
**Objective:** Per-strategy attempt deadlines and cancellation so a hung prober cannot block escalation.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-C028-01** Wrap every strategy attempt in a hard deadline/cancellation scope and require adapters to release sockets/tasks on timeout; do not rely solely on cooperative adapter return.
- [ ] **G12-C028-02** Record start, deadline, completion, cancellation cause, elapsed duration, and whether cleanup finished; late completions must be ignored safely.
- [ ] **G12-C028-03** Define the component state machine, legal transitions, triggering signals, timers, cancellation behavior, terminal conditions, and invariants; reject impossible transitions in tests.
- [ ] **G12-C028-04** Separate liveness, reachability, quality, readiness, and policy eligibility so a low-latency probe cannot by itself certify a path for sustained application traffic.
- [ ] **G12-C028-05** Use monotonic time for durations and deadlines; explicitly define freshness windows, smoothing windows, retry budgets, and hysteresis thresholds as versioned policy.
- [ ] **G12-C028-06** Prevent noisy measurements from causing oscillation through bounded sampling, robust aggregation, hysteresis, hold-down timers, and deterministic tie-breaking.
- [ ] **G12-C028-07** Ensure relay cost, quota, path quality, identity/trust, residency, and policy constraints are inputs to path selection rather than post-selection annotations.
- [ ] **G12-C028-08** Test recovery from transient loss, prolonged partition, partial dependency failure, flapping links, stale candidate data, delayed probe completion, and concurrent path changes.
- [ ] **G12-C028-09** Implement and document the exact behavior required by this inventory item: **Per-strategy attempt deadlines and cancellation so a hung prober cannot block escalation**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-C028-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-C028-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-C028-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-C028-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-C028-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-C028-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-C028-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-C028-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-C028-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-C028-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-C028-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-C028-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-C028-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-C028`.

### 29. Health-probe scheduler — P0

**Component ID:** `G12-C029`  
**Objective:** Health-probe scheduler independent of caller traffic.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-C029-01** Define the component state machine, legal transitions, triggering signals, timers, cancellation behavior, terminal conditions, and invariants; reject impossible transitions in tests.
- [ ] **G12-C029-02** Separate liveness, reachability, quality, readiness, and policy eligibility so a low-latency probe cannot by itself certify a path for sustained application traffic.
- [ ] **G12-C029-03** Use monotonic time for durations and deadlines; explicitly define freshness windows, smoothing windows, retry budgets, and hysteresis thresholds as versioned policy.
- [ ] **G12-C029-04** Prevent noisy measurements from causing oscillation through bounded sampling, robust aggregation, hysteresis, hold-down timers, and deterministic tie-breaking.
- [ ] **G12-C029-05** Ensure relay cost, quota, path quality, identity/trust, residency, and policy constraints are inputs to path selection rather than post-selection annotations.
- [ ] **G12-C029-06** Test recovery from transient loss, prolonged partition, partial dependency failure, flapping links, stale candidate data, delayed probe completion, and concurrent path changes.
- [ ] **G12-C029-07** Implement and document the exact behavior required by this inventory item: **Health-probe scheduler independent of caller traffic**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-C029-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-C029-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-C029-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-C029-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-C029-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-C029-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-C029-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-C029-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-C029-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-C029-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-C029-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-C029-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-C029-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-C029`.

### 30. Bulk-transfer readiness probe — P0

**Component ID:** `G12-C030`  
**Objective:** Bulk-transfer readiness probe separate from small liveness probes.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-C030-01** Define the component state machine, legal transitions, triggering signals, timers, cancellation behavior, terminal conditions, and invariants; reject impossible transitions in tests.
- [ ] **G12-C030-02** Separate liveness, reachability, quality, readiness, and policy eligibility so a low-latency probe cannot by itself certify a path for sustained application traffic.
- [ ] **G12-C030-03** Use monotonic time for durations and deadlines; explicitly define freshness windows, smoothing windows, retry budgets, and hysteresis thresholds as versioned policy.
- [ ] **G12-C030-04** Prevent noisy measurements from causing oscillation through bounded sampling, robust aggregation, hysteresis, hold-down timers, and deterministic tie-breaking.
- [ ] **G12-C030-05** Ensure relay cost, quota, path quality, identity/trust, residency, and policy constraints are inputs to path selection rather than post-selection annotations.
- [ ] **G12-C030-06** Test recovery from transient loss, prolonged partition, partial dependency failure, flapping links, stale candidate data, delayed probe completion, and concurrent path changes.
- [ ] **G12-C030-07** Implement and document the exact behavior required by this inventory item: **Bulk-transfer readiness probe separate from small liveness probes**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-C030-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-C030-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-C030-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-C030-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-C030-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-C030-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-C030-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-C030-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-C030-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-C030-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-C030-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-C030-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-C030-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-C030`.

### 31. Latency/loss/jitter measurement — P0

**Component ID:** `G12-C031`  
**Objective:** Latency/loss/jitter measurement for usable-path quality decisions.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-C031-01** Define probe packet size/rate, sampling cadence, rolling windows, outlier policy, minimum samples, and confidence/unknown-state semantics.
- [ ] **G12-C031-02** Separate one-way metrics from round-trip metrics unless clocks are synchronized and validated; never infer one-way delay from RTT without explicit modeling.
- [ ] **G12-C031-03** Define the component state machine, legal transitions, triggering signals, timers, cancellation behavior, terminal conditions, and invariants; reject impossible transitions in tests.
- [ ] **G12-C031-04** Separate liveness, reachability, quality, readiness, and policy eligibility so a low-latency probe cannot by itself certify a path for sustained application traffic.
- [ ] **G12-C031-05** Use monotonic time for durations and deadlines; explicitly define freshness windows, smoothing windows, retry budgets, and hysteresis thresholds as versioned policy.
- [ ] **G12-C031-06** Prevent noisy measurements from causing oscillation through bounded sampling, robust aggregation, hysteresis, hold-down timers, and deterministic tie-breaking.
- [ ] **G12-C031-07** Ensure relay cost, quota, path quality, identity/trust, residency, and policy constraints are inputs to path selection rather than post-selection annotations.
- [ ] **G12-C031-08** Test recovery from transient loss, prolonged partition, partial dependency failure, flapping links, stale candidate data, delayed probe completion, and concurrent path changes.
- [ ] **G12-C031-09** Implement and document the exact behavior required by this inventory item: **Latency/loss/jitter measurement for usable-path quality decisions**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-C031-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-C031-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-C031-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-C031-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-C031-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-C031-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-C031-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-C031-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-C031-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-C031-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-C031-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-C031-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-C031-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-C031`.

### 32. Available-bandwidth estimation — P1

**Component ID:** `G12-C032`  
**Objective:** Available-bandwidth estimation .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-C032-01** Use a bounded, non-disruptive estimator and define how estimates age, how active traffic biases samples, and when the result is unknown rather than zero.
- [ ] **G12-C032-02** Cap probe traffic and disable/scale estimation on metered, power-constrained, or policy-restricted links.
- [ ] **G12-C032-03** Define the component state machine, legal transitions, triggering signals, timers, cancellation behavior, terminal conditions, and invariants; reject impossible transitions in tests.
- [ ] **G12-C032-04** Separate liveness, reachability, quality, readiness, and policy eligibility so a low-latency probe cannot by itself certify a path for sustained application traffic.
- [ ] **G12-C032-05** Use monotonic time for durations and deadlines; explicitly define freshness windows, smoothing windows, retry budgets, and hysteresis thresholds as versioned policy.
- [ ] **G12-C032-06** Prevent noisy measurements from causing oscillation through bounded sampling, robust aggregation, hysteresis, hold-down timers, and deterministic tie-breaking.
- [ ] **G12-C032-07** Ensure relay cost, quota, path quality, identity/trust, residency, and policy constraints are inputs to path selection rather than post-selection annotations.
- [ ] **G12-C032-08** Test recovery from transient loss, prolonged partition, partial dependency failure, flapping links, stale candidate data, delayed probe completion, and concurrent path changes.
- [ ] **G12-C032-09** Implement and document the exact behavior required by this inventory item: **Available-bandwidth estimation **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-C032-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-C032-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-C032-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-C032-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-C032-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-C032-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-C032-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-C032-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-C032-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-C032-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-C032-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-C032-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-C032-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-C032`.

### 33. Path scoring with hysteresis — P1

**Component ID:** `G12-C033`  
**Objective:** Path scoring with hysteresis to prevent route thrash.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-C033-01** Define the component state machine, legal transitions, triggering signals, timers, cancellation behavior, terminal conditions, and invariants; reject impossible transitions in tests.
- [ ] **G12-C033-02** Separate liveness, reachability, quality, readiness, and policy eligibility so a low-latency probe cannot by itself certify a path for sustained application traffic.
- [ ] **G12-C033-03** Use monotonic time for durations and deadlines; explicitly define freshness windows, smoothing windows, retry budgets, and hysteresis thresholds as versioned policy.
- [ ] **G12-C033-04** Prevent noisy measurements from causing oscillation through bounded sampling, robust aggregation, hysteresis, hold-down timers, and deterministic tie-breaking.
- [ ] **G12-C033-05** Ensure relay cost, quota, path quality, identity/trust, residency, and policy constraints are inputs to path selection rather than post-selection annotations.
- [ ] **G12-C033-06** Test recovery from transient loss, prolonged partition, partial dependency failure, flapping links, stale candidate data, delayed probe completion, and concurrent path changes.
- [ ] **G12-C033-07** Implement and document the exact behavior required by this inventory item: **Path scoring with hysteresis to prevent route thrash**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-C033-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-C033-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-C033-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-C033-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-C033-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-C033-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-C033-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-C033-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-C033-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-C033-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-C033-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-C033-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-C033-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-C033`.

### 34. Session keepalive manager — P1

**Component ID:** `G12-C034`  
**Objective:** Session keepalive manager with NAT mapping refresh policy.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-C034-01** Define the component state machine, legal transitions, triggering signals, timers, cancellation behavior, terminal conditions, and invariants; reject impossible transitions in tests.
- [ ] **G12-C034-02** Separate liveness, reachability, quality, readiness, and policy eligibility so a low-latency probe cannot by itself certify a path for sustained application traffic.
- [ ] **G12-C034-03** Use monotonic time for durations and deadlines; explicitly define freshness windows, smoothing windows, retry budgets, and hysteresis thresholds as versioned policy.
- [ ] **G12-C034-04** Prevent noisy measurements from causing oscillation through bounded sampling, robust aggregation, hysteresis, hold-down timers, and deterministic tie-breaking.
- [ ] **G12-C034-05** Ensure relay cost, quota, path quality, identity/trust, residency, and policy constraints are inputs to path selection rather than post-selection annotations.
- [ ] **G12-C034-06** Test recovery from transient loss, prolonged partition, partial dependency failure, flapping links, stale candidate data, delayed probe completion, and concurrent path changes.
- [ ] **G12-C034-07** Implement and document the exact behavior required by this inventory item: **Session keepalive manager with NAT mapping refresh policy**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-C034-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-C034-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-C034-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-C034-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-C034-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-C034-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-C034-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-C034-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-C034-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-C034-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-C034-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-C034-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-C034-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-C034`.

### 35. Connection/session resumption — P1

**Component ID:** `G12-C035`  
**Objective:** Connection/session resumption after brief disconnects.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-C035-01** Define the component state machine, legal transitions, triggering signals, timers, cancellation behavior, terminal conditions, and invariants; reject impossible transitions in tests.
- [ ] **G12-C035-02** Separate liveness, reachability, quality, readiness, and policy eligibility so a low-latency probe cannot by itself certify a path for sustained application traffic.
- [ ] **G12-C035-03** Use monotonic time for durations and deadlines; explicitly define freshness windows, smoothing windows, retry budgets, and hysteresis thresholds as versioned policy.
- [ ] **G12-C035-04** Prevent noisy measurements from causing oscillation through bounded sampling, robust aggregation, hysteresis, hold-down timers, and deterministic tie-breaking.
- [ ] **G12-C035-05** Ensure relay cost, quota, path quality, identity/trust, residency, and policy constraints are inputs to path selection rather than post-selection annotations.
- [ ] **G12-C035-06** Test recovery from transient loss, prolonged partition, partial dependency failure, flapping links, stale candidate data, delayed probe completion, and concurrent path changes.
- [ ] **G12-C035-07** Implement and document the exact behavior required by this inventory item: **Connection/session resumption after brief disconnects**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-C035-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-C035-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-C035-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-C035-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-C035-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-C035-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-C035-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-C035-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-C035-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-C035-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-C035-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-C035-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-C035-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-C035`.

### 36. Candidate cache with safe expiry — P1

**Component ID:** `G12-C036`  
**Objective:** Candidate cache with safe expiry .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-C036-01** Define the component state machine, legal transitions, triggering signals, timers, cancellation behavior, terminal conditions, and invariants; reject impossible transitions in tests.
- [ ] **G12-C036-02** Separate liveness, reachability, quality, readiness, and policy eligibility so a low-latency probe cannot by itself certify a path for sustained application traffic.
- [ ] **G12-C036-03** Use monotonic time for durations and deadlines; explicitly define freshness windows, smoothing windows, retry budgets, and hysteresis thresholds as versioned policy.
- [ ] **G12-C036-04** Prevent noisy measurements from causing oscillation through bounded sampling, robust aggregation, hysteresis, hold-down timers, and deterministic tie-breaking.
- [ ] **G12-C036-05** Ensure relay cost, quota, path quality, identity/trust, residency, and policy constraints are inputs to path selection rather than post-selection annotations.
- [ ] **G12-C036-06** Test recovery from transient loss, prolonged partition, partial dependency failure, flapping links, stale candidate data, delayed probe completion, and concurrent path changes.
- [ ] **G12-C036-07** Implement and document the exact behavior required by this inventory item: **Candidate cache with safe expiry **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-C036-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-C036-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-C036-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-C036-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-C036-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-C036-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-C036-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-C036-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-C036-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-C036-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-C036-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-C036-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-C036-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-C036`.

### 37. Relay pre-warming policy — P1

**Component ID:** `G12-C037`  
**Objective:** Relay pre-warming policy for sites with repeatedly failed direct traversal.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-C037-01** Define the component state machine, legal transitions, triggering signals, timers, cancellation behavior, terminal conditions, and invariants; reject impossible transitions in tests.
- [ ] **G12-C037-02** Separate liveness, reachability, quality, readiness, and policy eligibility so a low-latency probe cannot by itself certify a path for sustained application traffic.
- [ ] **G12-C037-03** Use monotonic time for durations and deadlines; explicitly define freshness windows, smoothing windows, retry budgets, and hysteresis thresholds as versioned policy.
- [ ] **G12-C037-04** Prevent noisy measurements from causing oscillation through bounded sampling, robust aggregation, hysteresis, hold-down timers, and deterministic tie-breaking.
- [ ] **G12-C037-05** Ensure relay cost, quota, path quality, identity/trust, residency, and policy constraints are inputs to path selection rather than post-selection annotations.
- [ ] **G12-C037-06** Test recovery from transient loss, prolonged partition, partial dependency failure, flapping links, stale candidate data, delayed probe completion, and concurrent path changes.
- [ ] **G12-C037-07** Implement and document the exact behavior required by this inventory item: **Relay pre-warming policy for sites with repeatedly failed direct traversal**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-C037-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-C037-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-C037-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-C037-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-C037-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-C037-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-C037-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-C037-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-C037-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-C037-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-C037-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-C037-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-C037-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-C037`.

### 38. Relay region selection — P1

**Component ID:** `G12-C038`  
**Objective:** Relay region selection based on topology, latency, residency, and cost.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-C038-01** Define the component state machine, legal transitions, triggering signals, timers, cancellation behavior, terminal conditions, and invariants; reject impossible transitions in tests.
- [ ] **G12-C038-02** Separate liveness, reachability, quality, readiness, and policy eligibility so a low-latency probe cannot by itself certify a path for sustained application traffic.
- [ ] **G12-C038-03** Use monotonic time for durations and deadlines; explicitly define freshness windows, smoothing windows, retry budgets, and hysteresis thresholds as versioned policy.
- [ ] **G12-C038-04** Prevent noisy measurements from causing oscillation through bounded sampling, robust aggregation, hysteresis, hold-down timers, and deterministic tie-breaking.
- [ ] **G12-C038-05** Ensure relay cost, quota, path quality, identity/trust, residency, and policy constraints are inputs to path selection rather than post-selection annotations.
- [ ] **G12-C038-06** Test recovery from transient loss, prolonged partition, partial dependency failure, flapping links, stale candidate data, delayed probe completion, and concurrent path changes.
- [ ] **G12-C038-07** Implement and document the exact behavior required by this inventory item: **Relay region selection based on topology, latency, residency, and cost**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-C038-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-C038-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-C038-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-C038-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-C038-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-C038-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-C038-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-C038-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-C038-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-C038-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-C038-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-C038-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-C038-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-C038`.

### 39. Relay quota/budget enforcement — P0

**Component ID:** `G12-C039`  
**Objective:** Relay quota/budget enforcement to prevent billing abuse.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-C039-01** Enforce quota before and during allocation/use using atomic counters or authoritative service checks; define behavior at soft limit, hard limit, telemetry outage, and counter disagreement.
- [ ] **G12-C039-02** Prevent tenant/peer evasion through reconnects or region changes and preserve accounting lineage across failover.
- [ ] **G12-C039-03** Define the component state machine, legal transitions, triggering signals, timers, cancellation behavior, terminal conditions, and invariants; reject impossible transitions in tests.
- [ ] **G12-C039-04** Separate liveness, reachability, quality, readiness, and policy eligibility so a low-latency probe cannot by itself certify a path for sustained application traffic.
- [ ] **G12-C039-05** Use monotonic time for durations and deadlines; explicitly define freshness windows, smoothing windows, retry budgets, and hysteresis thresholds as versioned policy.
- [ ] **G12-C039-06** Prevent noisy measurements from causing oscillation through bounded sampling, robust aggregation, hysteresis, hold-down timers, and deterministic tie-breaking.
- [ ] **G12-C039-07** Ensure relay cost, quota, path quality, identity/trust, residency, and policy constraints are inputs to path selection rather than post-selection annotations.
- [ ] **G12-C039-08** Test recovery from transient loss, prolonged partition, partial dependency failure, flapping links, stale candidate data, delayed probe completion, and concurrent path changes.
- [ ] **G12-C039-09** Implement and document the exact behavior required by this inventory item: **Relay quota/budget enforcement to prevent billing abuse**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-C039-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-C039-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-C039-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-C039-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-C039-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-C039-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-C039-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-C039-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-C039-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-C039-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-C039-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-C039-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-C039-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-C039`.

### 40. Automatic relay-byte instrumentation — P0

**Component ID:** `G12-C040`  
**Objective:** Automatic relay-byte instrumentation wired to the actual transport rather than manual accounting calls.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-C040-01** Instrument ingress and egress bytes at the actual relay/data-plane boundary with clear treatment of retransmissions, protocol overhead, encryption overhead, and double-count prevention.
- [ ] **G12-C040-02** Reconcile local counters against provider/server usage where available and alert on material divergence.
- [ ] **G12-C040-03** Define the component state machine, legal transitions, triggering signals, timers, cancellation behavior, terminal conditions, and invariants; reject impossible transitions in tests.
- [ ] **G12-C040-04** Separate liveness, reachability, quality, readiness, and policy eligibility so a low-latency probe cannot by itself certify a path for sustained application traffic.
- [ ] **G12-C040-05** Use monotonic time for durations and deadlines; explicitly define freshness windows, smoothing windows, retry budgets, and hysteresis thresholds as versioned policy.
- [ ] **G12-C040-06** Prevent noisy measurements from causing oscillation through bounded sampling, robust aggregation, hysteresis, hold-down timers, and deterministic tie-breaking.
- [ ] **G12-C040-07** Ensure relay cost, quota, path quality, identity/trust, residency, and policy constraints are inputs to path selection rather than post-selection annotations.
- [ ] **G12-C040-08** Test recovery from transient loss, prolonged partition, partial dependency failure, flapping links, stale candidate data, delayed probe completion, and concurrent path changes.
- [ ] **G12-C040-09** Implement and document the exact behavior required by this inventory item: **Automatic relay-byte instrumentation wired to the actual transport rather than manual accounting calls**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-C040-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-C040-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-C040-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-C040-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-C040-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-C040-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-C040-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-C040-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-C040-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-C040-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-C040-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-C040-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-C040-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-C040`.

### 41. Multipath failover/striping — P2

**Component ID:** `G12-C041`  
**Objective:** Multipath failover/striping where semantics and transport support it.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-C041-01** Define the component state machine, legal transitions, triggering signals, timers, cancellation behavior, terminal conditions, and invariants; reject impossible transitions in tests.
- [ ] **G12-C041-02** Separate liveness, reachability, quality, readiness, and policy eligibility so a low-latency probe cannot by itself certify a path for sustained application traffic.
- [ ] **G12-C041-03** Use monotonic time for durations and deadlines; explicitly define freshness windows, smoothing windows, retry budgets, and hysteresis thresholds as versioned policy.
- [ ] **G12-C041-04** Prevent noisy measurements from causing oscillation through bounded sampling, robust aggregation, hysteresis, hold-down timers, and deterministic tie-breaking.
- [ ] **G12-C041-05** Ensure relay cost, quota, path quality, identity/trust, residency, and policy constraints are inputs to path selection rather than post-selection annotations.
- [ ] **G12-C041-06** Test recovery from transient loss, prolonged partition, partial dependency failure, flapping links, stale candidate data, delayed probe completion, and concurrent path changes.
- [ ] **G12-C041-07** Implement and document the exact behavior required by this inventory item: **Multipath failover/striping where semantics and transport support it**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-C041-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-C041-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-C041-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-C041-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-C041-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-C041-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-C041-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-C041-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-C041-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-C041-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-C041-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-C041-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-C041-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-C041`.

### 42. Predictive path switching — P2

**Component ID:** `G12-C042`  
**Objective:** Predictive path switching based on deteriorating quality signals.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-C042-01** Define the component state machine, legal transitions, triggering signals, timers, cancellation behavior, terminal conditions, and invariants; reject impossible transitions in tests.
- [ ] **G12-C042-02** Separate liveness, reachability, quality, readiness, and policy eligibility so a low-latency probe cannot by itself certify a path for sustained application traffic.
- [ ] **G12-C042-03** Use monotonic time for durations and deadlines; explicitly define freshness windows, smoothing windows, retry budgets, and hysteresis thresholds as versioned policy.
- [ ] **G12-C042-04** Prevent noisy measurements from causing oscillation through bounded sampling, robust aggregation, hysteresis, hold-down timers, and deterministic tie-breaking.
- [ ] **G12-C042-05** Ensure relay cost, quota, path quality, identity/trust, residency, and policy constraints are inputs to path selection rather than post-selection annotations.
- [ ] **G12-C042-06** Test recovery from transient loss, prolonged partition, partial dependency failure, flapping links, stale candidate data, delayed probe completion, and concurrent path changes.
- [ ] **G12-C042-07** Implement and document the exact behavior required by this inventory item: **Predictive path switching based on deteriorating quality signals**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-C042-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-C042-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-C042-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-C042-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-C042-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-C042-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-C042-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-C042-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-C042-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-C042-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-C042-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-C042-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-C042-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-C042`.

## D. Identity, encryption, trust, and abuse resistance

### 43. GAP-06 peer identity/attestation enforcement — P0

**Component ID:** `G12-D043`  
**Objective:** GAP-06 peer identity/attestation enforcement before accepting a path as trusted.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-D043-01** Bind the accepted data-plane peer to GAP-06 identity/attestation evidence and a freshness policy before marking a path trusted.
- [ ] **G12-D043-02** Define revocation and re-attestation behavior for long-lived sessions and ensure cached network reachability cannot outlive trust validity.
- [ ] **G12-D043-03** Create a component-specific threat model identifying assets, trust boundaries, attacker capabilities, spoofing/replay/amplification/resource-exhaustion paths, and required mitigations.
- [ ] **G12-D043-04** Bind authorization decisions to authenticated peer/service identity and current policy; do not trust network address, NAT mapping, relay allocation, or caller-supplied labels as identity.
- [ ] **G12-D043-05** Use cryptographically authenticated control messages where required and define nonce/sequence/expiry semantics that make replay and cross-session substitution detectable.
- [ ] **G12-D043-06** Define credential/key lifecycle behavior for issuance, distribution, rotation, revocation, compromise, expiry, clock skew, and emergency invalidation.
- [ ] **G12-D043-07** Enforce bounded memory, CPU, sockets, allocations, retries, and logging per peer/source/tenant to resist deliberate resource exhaustion and fleet-wide retry amplification.
- [ ] **G12-D043-08** Generate security audit events with stable reason codes, actor/subject identifiers, configuration lineage, and tamper-evident retention appropriate to the parent platform.
- [ ] **G12-D043-09** Implement and document the exact behavior required by this inventory item: **GAP-06 peer identity/attestation enforcement before accepting a path as trusted**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-D043-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-D043-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-D043-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-D043-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-D043-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-D043-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-D043-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-D043-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-D043-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-D043-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-D043-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-D043-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-D043-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-D043`.

### 44. End-to-end authenticated encryption integration — P0

**Component ID:** `G12-D044`  
**Objective:** End-to-end authenticated encryption integration across direct, punched, and relayed paths.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-D044-01** Define cryptographic context binding to peer identity, session, protocol version, and role; use separate keys/nonces for directions/epochs as required by the selected construction.
- [ ] **G12-D044-02** Test direct-to-relay and relay-to-direct transitions to prove intermediaries cannot terminate or downgrade end-to-end confidentiality/integrity.
- [ ] **G12-D044-03** Create a component-specific threat model identifying assets, trust boundaries, attacker capabilities, spoofing/replay/amplification/resource-exhaustion paths, and required mitigations.
- [ ] **G12-D044-04** Bind authorization decisions to authenticated peer/service identity and current policy; do not trust network address, NAT mapping, relay allocation, or caller-supplied labels as identity.
- [ ] **G12-D044-05** Use cryptographically authenticated control messages where required and define nonce/sequence/expiry semantics that make replay and cross-session substitution detectable.
- [ ] **G12-D044-06** Define credential/key lifecycle behavior for issuance, distribution, rotation, revocation, compromise, expiry, clock skew, and emergency invalidation.
- [ ] **G12-D044-07** Enforce bounded memory, CPU, sockets, allocations, retries, and logging per peer/source/tenant to resist deliberate resource exhaustion and fleet-wide retry amplification.
- [ ] **G12-D044-08** Generate security audit events with stable reason codes, actor/subject identifiers, configuration lineage, and tamper-evident retention appropriate to the parent platform.
- [ ] **G12-D044-09** Implement and document the exact behavior required by this inventory item: **End-to-end authenticated encryption integration across direct, punched, and relayed paths**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-D044-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-D044-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-D044-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-D044-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-D044-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-D044-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-D044-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-D044-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-D044-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-D044-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-D044-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-D044-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-D044-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-D044`.

### 45. Key acquisition/rotation/revocation behavior — P0

**Component ID:** `G12-D045`  
**Objective:** Key acquisition/rotation/revocation behavior for WAN sessions.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-D045-01** Create a component-specific threat model identifying assets, trust boundaries, attacker capabilities, spoofing/replay/amplification/resource-exhaustion paths, and required mitigations.
- [ ] **G12-D045-02** Bind authorization decisions to authenticated peer/service identity and current policy; do not trust network address, NAT mapping, relay allocation, or caller-supplied labels as identity.
- [ ] **G12-D045-03** Use cryptographically authenticated control messages where required and define nonce/sequence/expiry semantics that make replay and cross-session substitution detectable.
- [ ] **G12-D045-04** Define credential/key lifecycle behavior for issuance, distribution, rotation, revocation, compromise, expiry, clock skew, and emergency invalidation.
- [ ] **G12-D045-05** Enforce bounded memory, CPU, sockets, allocations, retries, and logging per peer/source/tenant to resist deliberate resource exhaustion and fleet-wide retry amplification.
- [ ] **G12-D045-06** Generate security audit events with stable reason codes, actor/subject identifiers, configuration lineage, and tamper-evident retention appropriate to the parent platform.
- [ ] **G12-D045-07** Implement and document the exact behavior required by this inventory item: **Key acquisition/rotation/revocation behavior for WAN sessions**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-D045-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-D045-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-D045-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-D045-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-D045-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-D045-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-D045-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-D045-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-D045-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-D045-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-D045-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-D045-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-D045-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-D045`.

### 46. Replay protection — P0

**Component ID:** `G12-D046`  
**Objective:** Replay protection for traversal/control messages.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-D046-01** Define nonce/sequence windows, epoch changes, persistence/restart behavior, maximum skew, duplicate handling, and memory bounds for replay state.
- [ ] **G12-D046-02** Test reordered, duplicated, delayed, cross-session, cross-peer, and post-restart message replay.
- [ ] **G12-D046-03** Create a component-specific threat model identifying assets, trust boundaries, attacker capabilities, spoofing/replay/amplification/resource-exhaustion paths, and required mitigations.
- [ ] **G12-D046-04** Bind authorization decisions to authenticated peer/service identity and current policy; do not trust network address, NAT mapping, relay allocation, or caller-supplied labels as identity.
- [ ] **G12-D046-05** Use cryptographically authenticated control messages where required and define nonce/sequence/expiry semantics that make replay and cross-session substitution detectable.
- [ ] **G12-D046-06** Define credential/key lifecycle behavior for issuance, distribution, rotation, revocation, compromise, expiry, clock skew, and emergency invalidation.
- [ ] **G12-D046-07** Enforce bounded memory, CPU, sockets, allocations, retries, and logging per peer/source/tenant to resist deliberate resource exhaustion and fleet-wide retry amplification.
- [ ] **G12-D046-08** Generate security audit events with stable reason codes, actor/subject identifiers, configuration lineage, and tamper-evident retention appropriate to the parent platform.
- [ ] **G12-D046-09** Implement and document the exact behavior required by this inventory item: **Replay protection for traversal/control messages**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-D046-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-D046-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-D046-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-D046-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-D046-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-D046-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-D046-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-D046-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-D046-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-D046-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-D046-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-D046-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-D046-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-D046`.

### 47. TURN credential lifecycle and rotation — P0

**Component ID:** `G12-D047`  
**Objective:** TURN credential lifecycle and rotation .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-D047-01** Implement Allocate, Refresh, CreatePermission, ChannelBind, Send/Data indications, channel-data framing, allocation expiry, and deterministic teardown; enforce authenticated access and realm/nonce handling.
- [ ] **G12-D047-02** Validate UDP/TCP/TLS TURN transports required by policy, permission/channel refresh timers, quota accounting, server failover, and credential rotation without orphaning allocations.
- [ ] **G12-D047-03** Create a component-specific threat model identifying assets, trust boundaries, attacker capabilities, spoofing/replay/amplification/resource-exhaustion paths, and required mitigations.
- [ ] **G12-D047-04** Bind authorization decisions to authenticated peer/service identity and current policy; do not trust network address, NAT mapping, relay allocation, or caller-supplied labels as identity.
- [ ] **G12-D047-05** Use cryptographically authenticated control messages where required and define nonce/sequence/expiry semantics that make replay and cross-session substitution detectable.
- [ ] **G12-D047-06** Define credential/key lifecycle behavior for issuance, distribution, rotation, revocation, compromise, expiry, clock skew, and emergency invalidation.
- [ ] **G12-D047-07** Enforce bounded memory, CPU, sockets, allocations, retries, and logging per peer/source/tenant to resist deliberate resource exhaustion and fleet-wide retry amplification.
- [ ] **G12-D047-08** Generate security audit events with stable reason codes, actor/subject identifiers, configuration lineage, and tamper-evident retention appropriate to the parent platform.
- [ ] **G12-D047-09** Implement and document the exact behavior required by this inventory item: **TURN credential lifecycle and rotation **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-D047-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-D047-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-D047-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-D047-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-D047-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-D047-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-D047-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-D047-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-D047-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-D047-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-D047-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-D047-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-D047-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-D047`.

### 48. Relay authorization and tenancy isolation — P0

**Component ID:** `G12-D048`  
**Objective:** Relay authorization and tenancy isolation .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-D048-01** Create a component-specific threat model identifying assets, trust boundaries, attacker capabilities, spoofing/replay/amplification/resource-exhaustion paths, and required mitigations.
- [ ] **G12-D048-02** Bind authorization decisions to authenticated peer/service identity and current policy; do not trust network address, NAT mapping, relay allocation, or caller-supplied labels as identity.
- [ ] **G12-D048-03** Use cryptographically authenticated control messages where required and define nonce/sequence/expiry semantics that make replay and cross-session substitution detectable.
- [ ] **G12-D048-04** Define credential/key lifecycle behavior for issuance, distribution, rotation, revocation, compromise, expiry, clock skew, and emergency invalidation.
- [ ] **G12-D048-05** Enforce bounded memory, CPU, sockets, allocations, retries, and logging per peer/source/tenant to resist deliberate resource exhaustion and fleet-wide retry amplification.
- [ ] **G12-D048-06** Generate security audit events with stable reason codes, actor/subject identifiers, configuration lineage, and tamper-evident retention appropriate to the parent platform.
- [ ] **G12-D048-07** Implement and document the exact behavior required by this inventory item: **Relay authorization and tenancy isolation **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-D048-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-D048-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-D048-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-D048-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-D048-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-D048-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-D048-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-D048-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-D048-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-D048-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-D048-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-D048-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-D048-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-D048`.

### 49. Per-peer/IP/range rate limiting — P0

**Component ID:** `G12-D049`  
**Objective:** Per-peer/IP/range rate limiting for traversal attempts.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-D049-01** Define token/leaky-bucket or equivalent limits at source, peer, tenant, destination, and global levels with bounded state and eviction policy.
- [ ] **G12-D049-02** Make limiter outcomes observable and resistant to attacker-driven high-cardinality key creation.
- [ ] **G12-D049-03** Create a component-specific threat model identifying assets, trust boundaries, attacker capabilities, spoofing/replay/amplification/resource-exhaustion paths, and required mitigations.
- [ ] **G12-D049-04** Bind authorization decisions to authenticated peer/service identity and current policy; do not trust network address, NAT mapping, relay allocation, or caller-supplied labels as identity.
- [ ] **G12-D049-05** Use cryptographically authenticated control messages where required and define nonce/sequence/expiry semantics that make replay and cross-session substitution detectable.
- [ ] **G12-D049-06** Define credential/key lifecycle behavior for issuance, distribution, rotation, revocation, compromise, expiry, clock skew, and emergency invalidation.
- [ ] **G12-D049-07** Enforce bounded memory, CPU, sockets, allocations, retries, and logging per peer/source/tenant to resist deliberate resource exhaustion and fleet-wide retry amplification.
- [ ] **G12-D049-08** Generate security audit events with stable reason codes, actor/subject identifiers, configuration lineage, and tamper-evident retention appropriate to the parent platform.
- [ ] **G12-D049-09** Implement and document the exact behavior required by this inventory item: **Per-peer/IP/range rate limiting for traversal attempts**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-D049-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-D049-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-D049-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-D049-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-D049-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-D049-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-D049-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-D049-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-D049-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-D049-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-D049-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-D049-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-D049-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-D049`.

### 50. Circuit breaker / retry budget — P0

**Component ID:** `G12-D050`  
**Objective:** Circuit breaker / retry budget beyond per-path backoff to prevent fleet-wide failure cascades.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-D050-01** Implement closed/open/half-open behavior with fleet/site/peer scoping, bounded probe admission, recovery hysteresis, and operator override/disable semantics.
- [ ] **G12-D050-02** Coordinate breaker policy with per-path exponential backoff so nested retry systems cannot multiply attempt volume.
- [ ] **G12-D050-03** Create a component-specific threat model identifying assets, trust boundaries, attacker capabilities, spoofing/replay/amplification/resource-exhaustion paths, and required mitigations.
- [ ] **G12-D050-04** Bind authorization decisions to authenticated peer/service identity and current policy; do not trust network address, NAT mapping, relay allocation, or caller-supplied labels as identity.
- [ ] **G12-D050-05** Use cryptographically authenticated control messages where required and define nonce/sequence/expiry semantics that make replay and cross-session substitution detectable.
- [ ] **G12-D050-06** Define credential/key lifecycle behavior for issuance, distribution, rotation, revocation, compromise, expiry, clock skew, and emergency invalidation.
- [ ] **G12-D050-07** Enforce bounded memory, CPU, sockets, allocations, retries, and logging per peer/source/tenant to resist deliberate resource exhaustion and fleet-wide retry amplification.
- [ ] **G12-D050-08** Generate security audit events with stable reason codes, actor/subject identifiers, configuration lineage, and tamper-evident retention appropriate to the parent platform.
- [ ] **G12-D050-09** Implement and document the exact behavior required by this inventory item: **Circuit breaker / retry budget beyond per-path backoff to prevent fleet-wide failure cascades**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-D050-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-D050-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-D050-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-D050-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-D050-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-D050-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-D050-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-D050-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-D050-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-D050-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-D050-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-D050-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-D050-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-D050`.

### 51. Egress/peer policy enforcement — P0

**Component ID:** `G12-D051`  
**Objective:** Egress/peer policy enforcement defining where the subsystem may connect.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-D051-01** Create a component-specific threat model identifying assets, trust boundaries, attacker capabilities, spoofing/replay/amplification/resource-exhaustion paths, and required mitigations.
- [ ] **G12-D051-02** Bind authorization decisions to authenticated peer/service identity and current policy; do not trust network address, NAT mapping, relay allocation, or caller-supplied labels as identity.
- [ ] **G12-D051-03** Use cryptographically authenticated control messages where required and define nonce/sequence/expiry semantics that make replay and cross-session substitution detectable.
- [ ] **G12-D051-04** Define credential/key lifecycle behavior for issuance, distribution, rotation, revocation, compromise, expiry, clock skew, and emergency invalidation.
- [ ] **G12-D051-05** Enforce bounded memory, CPU, sockets, allocations, retries, and logging per peer/source/tenant to resist deliberate resource exhaustion and fleet-wide retry amplification.
- [ ] **G12-D051-06** Generate security audit events with stable reason codes, actor/subject identifiers, configuration lineage, and tamper-evident retention appropriate to the parent platform.
- [ ] **G12-D051-07** Implement and document the exact behavior required by this inventory item: **Egress/peer policy enforcement defining where the subsystem may connect**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-D051-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-D051-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-D051-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-D051-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-D051-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-D051-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-D051-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-D051-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-D051-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-D051-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-D051-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-D051-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-D051-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-D051`.

### 52. Secrets manager integration — P0

**Component ID:** `G12-D052`  
**Objective:** Secrets manager integration ; no long-lived credentials in ordinary config/logs.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-D052-01** Reference secrets by opaque identifier; load them through the platform secret provider with least privilege, rotation notifications, and memory/log redaction.
- [ ] **G12-D052-02** Prohibit secret material from configuration snapshots, metrics labels, exception strings, crash dumps/support bundles, and persisted path history.
- [ ] **G12-D052-03** Create a component-specific threat model identifying assets, trust boundaries, attacker capabilities, spoofing/replay/amplification/resource-exhaustion paths, and required mitigations.
- [ ] **G12-D052-04** Bind authorization decisions to authenticated peer/service identity and current policy; do not trust network address, NAT mapping, relay allocation, or caller-supplied labels as identity.
- [ ] **G12-D052-05** Use cryptographically authenticated control messages where required and define nonce/sequence/expiry semantics that make replay and cross-session substitution detectable.
- [ ] **G12-D052-06** Define credential/key lifecycle behavior for issuance, distribution, rotation, revocation, compromise, expiry, clock skew, and emergency invalidation.
- [ ] **G12-D052-07** Enforce bounded memory, CPU, sockets, allocations, retries, and logging per peer/source/tenant to resist deliberate resource exhaustion and fleet-wide retry amplification.
- [ ] **G12-D052-08** Generate security audit events with stable reason codes, actor/subject identifiers, configuration lineage, and tamper-evident retention appropriate to the parent platform.
- [ ] **G12-D052-09** Implement and document the exact behavior required by this inventory item: **Secrets manager integration ; no long-lived credentials in ordinary config/logs**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-D052-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-D052-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-D052-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-D052-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-D052-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-D052-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-D052-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-D052-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-D052-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-D052-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-D052-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-D052-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-D052-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-D052`.

### 53. Endpoint privacy controls — P1

**Component ID:** `G12-D053`  
**Objective:** Endpoint privacy controls for logs, metrics, traces, and support bundles.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-D053-01** Create a component-specific threat model identifying assets, trust boundaries, attacker capabilities, spoofing/replay/amplification/resource-exhaustion paths, and required mitigations.
- [ ] **G12-D053-02** Bind authorization decisions to authenticated peer/service identity and current policy; do not trust network address, NAT mapping, relay allocation, or caller-supplied labels as identity.
- [ ] **G12-D053-03** Use cryptographically authenticated control messages where required and define nonce/sequence/expiry semantics that make replay and cross-session substitution detectable.
- [ ] **G12-D053-04** Define credential/key lifecycle behavior for issuance, distribution, rotation, revocation, compromise, expiry, clock skew, and emergency invalidation.
- [ ] **G12-D053-05** Enforce bounded memory, CPU, sockets, allocations, retries, and logging per peer/source/tenant to resist deliberate resource exhaustion and fleet-wide retry amplification.
- [ ] **G12-D053-06** Generate security audit events with stable reason codes, actor/subject identifiers, configuration lineage, and tamper-evident retention appropriate to the parent platform.
- [ ] **G12-D053-07** Implement and document the exact behavior required by this inventory item: **Endpoint privacy controls for logs, metrics, traces, and support bundles**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-D053-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-D053-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-D053-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-D053-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-D053-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-D053-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-D053-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-D053-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-D053-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-D053-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-D053-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-D053-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-D053-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-D053`.

### 54. Abuse/anomaly detection — P1

**Component ID:** `G12-D054`  
**Objective:** Abuse/anomaly detection for forced-relay attacks, scanning, amplification, or credential misuse.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-D054-01** Create a component-specific threat model identifying assets, trust boundaries, attacker capabilities, spoofing/replay/amplification/resource-exhaustion paths, and required mitigations.
- [ ] **G12-D054-02** Bind authorization decisions to authenticated peer/service identity and current policy; do not trust network address, NAT mapping, relay allocation, or caller-supplied labels as identity.
- [ ] **G12-D054-03** Use cryptographically authenticated control messages where required and define nonce/sequence/expiry semantics that make replay and cross-session substitution detectable.
- [ ] **G12-D054-04** Define credential/key lifecycle behavior for issuance, distribution, rotation, revocation, compromise, expiry, clock skew, and emergency invalidation.
- [ ] **G12-D054-05** Enforce bounded memory, CPU, sockets, allocations, retries, and logging per peer/source/tenant to resist deliberate resource exhaustion and fleet-wide retry amplification.
- [ ] **G12-D054-06** Generate security audit events with stable reason codes, actor/subject identifiers, configuration lineage, and tamper-evident retention appropriate to the parent platform.
- [ ] **G12-D054-07** Implement and document the exact behavior required by this inventory item: **Abuse/anomaly detection for forced-relay attacks, scanning, amplification, or credential misuse**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-D054-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-D054-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-D054-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-D054-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-D054-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-D054-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-D054-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-D054-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-D054-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-D054-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-D054-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-D054-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-D054-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-D054`.

### 55. Tamper-evident security audit events — P1

**Component ID:** `G12-D055`  
**Objective:** Tamper-evident security audit events linked to identity and configuration lineage.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-D055-01** Create a component-specific threat model identifying assets, trust boundaries, attacker capabilities, spoofing/replay/amplification/resource-exhaustion paths, and required mitigations.
- [ ] **G12-D055-02** Bind authorization decisions to authenticated peer/service identity and current policy; do not trust network address, NAT mapping, relay allocation, or caller-supplied labels as identity.
- [ ] **G12-D055-03** Use cryptographically authenticated control messages where required and define nonce/sequence/expiry semantics that make replay and cross-session substitution detectable.
- [ ] **G12-D055-04** Define credential/key lifecycle behavior for issuance, distribution, rotation, revocation, compromise, expiry, clock skew, and emergency invalidation.
- [ ] **G12-D055-05** Enforce bounded memory, CPU, sockets, allocations, retries, and logging per peer/source/tenant to resist deliberate resource exhaustion and fleet-wide retry amplification.
- [ ] **G12-D055-06** Generate security audit events with stable reason codes, actor/subject identifiers, configuration lineage, and tamper-evident retention appropriate to the parent platform.
- [ ] **G12-D055-07** Implement and document the exact behavior required by this inventory item: **Tamper-evident security audit events linked to identity and configuration lineage**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-D055-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-D055-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-D055-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-D055-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-D055-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-D055-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-D055-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-D055-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-D055-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-D055-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-D055-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-D055-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-D055-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-D055`.

## E. State, concurrency, persistence, and failure containment

### 56. Thread/async safety model — P0

**Component ID:** `G12-E056`  
**Objective:** Thread/async safety model for shared `Path` state.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-E056-01** Enumerate every mutable field and assign ownership/locking/serialization rules; document which callbacks may run concurrently and which public methods are thread/async safe.
- [ ] **G12-E056-02** Use stress tests and instrumentation to detect deadlocks, double-completion, lost wakeups, use-after-close, and inconsistent snapshots.
- [ ] **G12-E056-03** Choose and document the concurrency model (single-threaded event loop, actor, lock-based, structured concurrency, or equivalent) and identify the sole owner of each mutable state object.
- [ ] **G12-E056-04** Make all externally visible state transitions atomic and orderable; prevent torn reads between probe completion, timers, route events, disconnects, and configuration reloads.
- [ ] **G12-E056-05** Define idempotency and duplicate-event semantics for repeated callbacks, retried commands, late timers, process restarts, and control-plane redelivery.
- [ ] **G12-E056-06** Bound queues, histories, caches, task counts, descriptors, and retained diagnostics; define backpressure behavior rather than permitting unbounded growth.
- [ ] **G12-E056-07** Specify crash/restart recovery: which state is durable, reconstructable, discarded, or revalidated, and how stale ownership/session records are detected.
- [ ] **G12-E056-08** Exercise race detectors/stress tests with simultaneous success/failure, cancellation, shutdown, config changes, clock/suspend events, and dependency recovery.
- [ ] **G12-E056-09** Implement and document the exact behavior required by this inventory item: **Thread/async safety model for shared `Path` state**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-E056-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-E056-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-E056-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-E056-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-E056-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-E056-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-E056-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-E056-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-E056-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-E056-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-E056-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-E056-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-E056-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-E056`.

### 57. Atomic state-transition implementation — P0

**Component ID:** `G12-E057`  
**Objective:** Atomic state-transition implementation for concurrent probe/timer events.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-E057-01** Choose and document the concurrency model (single-threaded event loop, actor, lock-based, structured concurrency, or equivalent) and identify the sole owner of each mutable state object.
- [ ] **G12-E057-02** Make all externally visible state transitions atomic and orderable; prevent torn reads between probe completion, timers, route events, disconnects, and configuration reloads.
- [ ] **G12-E057-03** Define idempotency and duplicate-event semantics for repeated callbacks, retried commands, late timers, process restarts, and control-plane redelivery.
- [ ] **G12-E057-04** Bound queues, histories, caches, task counts, descriptors, and retained diagnostics; define backpressure behavior rather than permitting unbounded growth.
- [ ] **G12-E057-05** Specify crash/restart recovery: which state is durable, reconstructable, discarded, or revalidated, and how stale ownership/session records are detected.
- [ ] **G12-E057-06** Exercise race detectors/stress tests with simultaneous success/failure, cancellation, shutdown, config changes, clock/suspend events, and dependency recovery.
- [ ] **G12-E057-07** Implement and document the exact behavior required by this inventory item: **Atomic state-transition implementation for concurrent probe/timer events**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-E057-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-E057-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-E057-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-E057-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-E057-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-E057-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-E057-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-E057-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-E057-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-E057-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-E057-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-E057-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-E057-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-E057`.

### 58. Durable or reconstructable path/session state policy — P0

**Component ID:** `G12-E058`  
**Objective:** Durable or reconstructable path/session state policy after process/node restart.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-E058-01** Choose and document the concurrency model (single-threaded event loop, actor, lock-based, structured concurrency, or equivalent) and identify the sole owner of each mutable state object.
- [ ] **G12-E058-02** Make all externally visible state transitions atomic and orderable; prevent torn reads between probe completion, timers, route events, disconnects, and configuration reloads.
- [ ] **G12-E058-03** Define idempotency and duplicate-event semantics for repeated callbacks, retried commands, late timers, process restarts, and control-plane redelivery.
- [ ] **G12-E058-04** Bound queues, histories, caches, task counts, descriptors, and retained diagnostics; define backpressure behavior rather than permitting unbounded growth.
- [ ] **G12-E058-05** Specify crash/restart recovery: which state is durable, reconstructable, discarded, or revalidated, and how stale ownership/session records are detected.
- [ ] **G12-E058-06** Exercise race detectors/stress tests with simultaneous success/failure, cancellation, shutdown, config changes, clock/suspend events, and dependency recovery.
- [ ] **G12-E058-07** Implement and document the exact behavior required by this inventory item: **Durable or reconstructable path/session state policy after process/node restart**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-E058-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-E058-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-E058-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-E058-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-E058-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-E058-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-E058-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-E058-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-E058-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-E058-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-E058-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-E058-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-E058-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-E058`.

### 59. Monotonic clock abstraction — P0

**Component ID:** `G12-E059`  
**Objective:** Monotonic clock abstraction injected by the runtime and test harness.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-E059-01** Provide a clock interface returning monotonic instants/durations for deadlines and a separate wall clock for audit timestamps; never subtract wall-clock values for retry timing.
- [ ] **G12-E059-02** Inject deterministic fake clocks in unit tests to advance timers without sleeps and to cover boundary conditions exactly.
- [ ] **G12-E059-03** Choose and document the concurrency model (single-threaded event loop, actor, lock-based, structured concurrency, or equivalent) and identify the sole owner of each mutable state object.
- [ ] **G12-E059-04** Make all externally visible state transitions atomic and orderable; prevent torn reads between probe completion, timers, route events, disconnects, and configuration reloads.
- [ ] **G12-E059-05** Define idempotency and duplicate-event semantics for repeated callbacks, retried commands, late timers, process restarts, and control-plane redelivery.
- [ ] **G12-E059-06** Bound queues, histories, caches, task counts, descriptors, and retained diagnostics; define backpressure behavior rather than permitting unbounded growth.
- [ ] **G12-E059-07** Specify crash/restart recovery: which state is durable, reconstructable, discarded, or revalidated, and how stale ownership/session records are detected.
- [ ] **G12-E059-08** Exercise race detectors/stress tests with simultaneous success/failure, cancellation, shutdown, config changes, clock/suspend events, and dependency recovery.
- [ ] **G12-E059-09** Implement and document the exact behavior required by this inventory item: **Monotonic clock abstraction injected by the runtime and test harness**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-E059-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-E059-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-E059-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-E059-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-E059-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-E059-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-E059-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-E059-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-E059-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-E059-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-E059-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-E059-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-E059-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-E059`.

### 60. Clock-jump/suspend-resume handling — P0

**Component ID:** `G12-E060`  
**Objective:** Clock-jump/suspend-resume handling .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-E060-01** Choose and document the concurrency model (single-threaded event loop, actor, lock-based, structured concurrency, or equivalent) and identify the sole owner of each mutable state object.
- [ ] **G12-E060-02** Make all externally visible state transitions atomic and orderable; prevent torn reads between probe completion, timers, route events, disconnects, and configuration reloads.
- [ ] **G12-E060-03** Define idempotency and duplicate-event semantics for repeated callbacks, retried commands, late timers, process restarts, and control-plane redelivery.
- [ ] **G12-E060-04** Bound queues, histories, caches, task counts, descriptors, and retained diagnostics; define backpressure behavior rather than permitting unbounded growth.
- [ ] **G12-E060-05** Specify crash/restart recovery: which state is durable, reconstructable, discarded, or revalidated, and how stale ownership/session records are detected.
- [ ] **G12-E060-06** Exercise race detectors/stress tests with simultaneous success/failure, cancellation, shutdown, config changes, clock/suspend events, and dependency recovery.
- [ ] **G12-E060-07** Implement and document the exact behavior required by this inventory item: **Clock-jump/suspend-resume handling **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-E060-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-E060-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-E060-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-E060-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-E060-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-E060-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-E060-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-E060-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-E060-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-E060-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-E060-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-E060-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-E060-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-E060`.

### 61. Process supervision and restart policy — P0

**Component ID:** `G12-E061`  
**Objective:** Process supervision and restart policy .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-E061-01** Choose and document the concurrency model (single-threaded event loop, actor, lock-based, structured concurrency, or equivalent) and identify the sole owner of each mutable state object.
- [ ] **G12-E061-02** Make all externally visible state transitions atomic and orderable; prevent torn reads between probe completion, timers, route events, disconnects, and configuration reloads.
- [ ] **G12-E061-03** Define idempotency and duplicate-event semantics for repeated callbacks, retried commands, late timers, process restarts, and control-plane redelivery.
- [ ] **G12-E061-04** Bound queues, histories, caches, task counts, descriptors, and retained diagnostics; define backpressure behavior rather than permitting unbounded growth.
- [ ] **G12-E061-05** Specify crash/restart recovery: which state is durable, reconstructable, discarded, or revalidated, and how stale ownership/session records are detected.
- [ ] **G12-E061-06** Exercise race detectors/stress tests with simultaneous success/failure, cancellation, shutdown, config changes, clock/suspend events, and dependency recovery.
- [ ] **G12-E061-07** Implement and document the exact behavior required by this inventory item: **Process supervision and restart policy **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-E061-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-E061-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-E061-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-E061-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-E061-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-E061-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-E061-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-E061-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-E061-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-E061-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-E061-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-E061-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-E061-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-E061`.

### 62. Dependency health model — P0

**Component ID:** `G12-E062`  
**Objective:** Dependency health model for STUN, TURN, DNS, identity, keys, observability, and control plane.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-E062-01** Implement RFC 8489-compatible Binding transactions, transaction-ID matching, XOR-MAPPED-ADDRESS parsing, MESSAGE-INTEGRITY/FINGERPRINT handling when configured, and retransmission timing appropriate to the selected transport.
- [ ] **G12-E062-02** Verify discovery against multiple independent STUN servers and distinguish server failure, DNS failure, blocked UDP, malformed response, and mapping inconsistency.
- [ ] **G12-E062-03** Implement Allocate, Refresh, CreatePermission, ChannelBind, Send/Data indications, channel-data framing, allocation expiry, and deterministic teardown; enforce authenticated access and realm/nonce handling.
- [ ] **G12-E062-04** Validate UDP/TCP/TLS TURN transports required by policy, permission/channel refresh timers, quota accounting, server failover, and credential rotation without orphaning allocations.
- [ ] **G12-E062-05** Choose and document the concurrency model (single-threaded event loop, actor, lock-based, structured concurrency, or equivalent) and identify the sole owner of each mutable state object.
- [ ] **G12-E062-06** Make all externally visible state transitions atomic and orderable; prevent torn reads between probe completion, timers, route events, disconnects, and configuration reloads.
- [ ] **G12-E062-07** Define idempotency and duplicate-event semantics for repeated callbacks, retried commands, late timers, process restarts, and control-plane redelivery.
- [ ] **G12-E062-08** Bound queues, histories, caches, task counts, descriptors, and retained diagnostics; define backpressure behavior rather than permitting unbounded growth.
- [ ] **G12-E062-09** Specify crash/restart recovery: which state is durable, reconstructable, discarded, or revalidated, and how stale ownership/session records are detected.
- [ ] **G12-E062-10** Exercise race detectors/stress tests with simultaneous success/failure, cancellation, shutdown, config changes, clock/suspend events, and dependency recovery.
- [ ] **G12-E062-11** Implement and document the exact behavior required by this inventory item: **Dependency health model for STUN, TURN, DNS, identity, keys, observability, and control plane**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-E062-12** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-E062-13** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-E062-14** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-E062-15** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-E062-16** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-E062-17** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-E062-18** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-E062-19** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-E062-20** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-E062-21** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-E062-22** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-E062-23** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-E062-24** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-E062`.

### 63. Degraded-control-plane policy — P0

**Component ID:** `G12-E063`  
**Objective:** Degraded-control-plane policy defining which existing sessions may continue.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-E063-01** Choose and document the concurrency model (single-threaded event loop, actor, lock-based, structured concurrency, or equivalent) and identify the sole owner of each mutable state object.
- [ ] **G12-E063-02** Make all externally visible state transitions atomic and orderable; prevent torn reads between probe completion, timers, route events, disconnects, and configuration reloads.
- [ ] **G12-E063-03** Define idempotency and duplicate-event semantics for repeated callbacks, retried commands, late timers, process restarts, and control-plane redelivery.
- [ ] **G12-E063-04** Bound queues, histories, caches, task counts, descriptors, and retained diagnostics; define backpressure behavior rather than permitting unbounded growth.
- [ ] **G12-E063-05** Specify crash/restart recovery: which state is durable, reconstructable, discarded, or revalidated, and how stale ownership/session records are detected.
- [ ] **G12-E063-06** Exercise race detectors/stress tests with simultaneous success/failure, cancellation, shutdown, config changes, clock/suspend events, and dependency recovery.
- [ ] **G12-E063-07** Implement and document the exact behavior required by this inventory item: **Degraded-control-plane policy defining which existing sessions may continue**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-E063-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-E063-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-E063-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-E063-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-E063-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-E063-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-E063-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-E063-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-E063-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-E063-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-E063-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-E063-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-E063-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-E063`.

### 64. Quarantine/disable control — P0

**Component ID:** `G12-E064`  
**Objective:** Quarantine/disable control for a faulty traversal backend or peer.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-E064-01** Choose and document the concurrency model (single-threaded event loop, actor, lock-based, structured concurrency, or equivalent) and identify the sole owner of each mutable state object.
- [ ] **G12-E064-02** Make all externally visible state transitions atomic and orderable; prevent torn reads between probe completion, timers, route events, disconnects, and configuration reloads.
- [ ] **G12-E064-03** Define idempotency and duplicate-event semantics for repeated callbacks, retried commands, late timers, process restarts, and control-plane redelivery.
- [ ] **G12-E064-04** Bound queues, histories, caches, task counts, descriptors, and retained diagnostics; define backpressure behavior rather than permitting unbounded growth.
- [ ] **G12-E064-05** Specify crash/restart recovery: which state is durable, reconstructable, discarded, or revalidated, and how stale ownership/session records are detected.
- [ ] **G12-E064-06** Exercise race detectors/stress tests with simultaneous success/failure, cancellation, shutdown, config changes, clock/suspend events, and dependency recovery.
- [ ] **G12-E064-07** Implement and document the exact behavior required by this inventory item: **Quarantine/disable control for a faulty traversal backend or peer**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-E064-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-E064-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-E064-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-E064-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-E064-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-E064-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-E064-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-E064-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-E064-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-E064-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-E064-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-E064-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-E064-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-E064`.

### 65. Stale-controller/duplicate-owner protection — P1

**Component ID:** `G12-E065`  
**Objective:** Stale-controller/duplicate-owner protection if path decisions can be made by multiple controllers.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-E065-01** Choose and document the concurrency model (single-threaded event loop, actor, lock-based, structured concurrency, or equivalent) and identify the sole owner of each mutable state object.
- [ ] **G12-E065-02** Make all externally visible state transitions atomic and orderable; prevent torn reads between probe completion, timers, route events, disconnects, and configuration reloads.
- [ ] **G12-E065-03** Define idempotency and duplicate-event semantics for repeated callbacks, retried commands, late timers, process restarts, and control-plane redelivery.
- [ ] **G12-E065-04** Bound queues, histories, caches, task counts, descriptors, and retained diagnostics; define backpressure behavior rather than permitting unbounded growth.
- [ ] **G12-E065-05** Specify crash/restart recovery: which state is durable, reconstructable, discarded, or revalidated, and how stale ownership/session records are detected.
- [ ] **G12-E065-06** Exercise race detectors/stress tests with simultaneous success/failure, cancellation, shutdown, config changes, clock/suspend events, and dependency recovery.
- [ ] **G12-E065-07** Implement and document the exact behavior required by this inventory item: **Stale-controller/duplicate-owner protection if path decisions can be made by multiple controllers**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-E065-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-E065-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-E065-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-E065-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-E065-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-E065-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-E065-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-E065-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-E065-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-E065-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-E065-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-E065-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-E065-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-E065`.

### 66. State migration/versioning — P1

**Component ID:** `G12-E066`  
**Objective:** State migration/versioning across software upgrades.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-E066-01** Choose and document the concurrency model (single-threaded event loop, actor, lock-based, structured concurrency, or equivalent) and identify the sole owner of each mutable state object.
- [ ] **G12-E066-02** Make all externally visible state transitions atomic and orderable; prevent torn reads between probe completion, timers, route events, disconnects, and configuration reloads.
- [ ] **G12-E066-03** Define idempotency and duplicate-event semantics for repeated callbacks, retried commands, late timers, process restarts, and control-plane redelivery.
- [ ] **G12-E066-04** Bound queues, histories, caches, task counts, descriptors, and retained diagnostics; define backpressure behavior rather than permitting unbounded growth.
- [ ] **G12-E066-05** Specify crash/restart recovery: which state is durable, reconstructable, discarded, or revalidated, and how stale ownership/session records are detected.
- [ ] **G12-E066-06** Exercise race detectors/stress tests with simultaneous success/failure, cancellation, shutdown, config changes, clock/suspend events, and dependency recovery.
- [ ] **G12-E066-07** Implement and document the exact behavior required by this inventory item: **State migration/versioning across software upgrades**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-E066-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-E066-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-E066-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-E066-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-E066-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-E066-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-E066-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-E066-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-E066-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-E066-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-E066-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-E066-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-E066-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-E066`.

## F. Configuration and policy plane

### 67. Versioned configuration schema — P0

**Component ID:** `G12-F067`  
**Objective:** Versioned configuration schema for strategies, servers, timeouts, freshness, retry ceilings, and policy.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-F067-01** Assign explicit schema version semantics and migration rules; reject unsupported future major versions while allowing documented compatible extensions.
- [ ] **G12-F067-02** Generate schema documentation and validation fixtures directly from the authoritative schema to prevent prose/code drift.
- [ ] **G12-F067-03** Define a versioned machine-readable schema with type/range/enum constraints, defaults, deprecations, unknown-field behavior, and forward/backward compatibility rules.
- [ ] **G12-F067-04** Perform semantic validation before activation, including cross-field constraints, endpoint syntax, credential references, timeout relationships, policy conflicts, and trust-sensitive fail-closed checks.
- [ ] **G12-F067-05** Separate immutable artifact configuration from environment/site overlays and secret references; record the fully resolved effective configuration fingerprint.
- [ ] **G12-F067-06** Apply configuration changes atomically with preflight, staged activation, health verification, rollback, and clear behavior for in-flight sessions.
- [ ] **G12-F067-07** Record provenance for every effective configuration: source, author/automation identity, version, generation, activation timestamp, approval/waiver references, and cryptographic digest where supported.
- [ ] **G12-F067-08** Test malformed input, unknown fields, rollback, partial dependency availability, concurrent reload, downgrade, secret rotation, and recovery after failed activation.
- [ ] **G12-F067-09** Implement and document the exact behavior required by this inventory item: **Versioned configuration schema for strategies, servers, timeouts, freshness, retry ceilings, and policy**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-F067-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-F067-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-F067-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-F067-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-F067-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-F067-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-F067-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-F067-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-F067-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-F067-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-F067-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-F067-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-F067-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-F067`.

### 68. Configuration validation before activation — P0

**Component ID:** `G12-F068`  
**Objective:** Configuration validation before activation with fail-closed rules for trust-sensitive fields.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-F068-01** Define a versioned machine-readable schema with type/range/enum constraints, defaults, deprecations, unknown-field behavior, and forward/backward compatibility rules.
- [ ] **G12-F068-02** Perform semantic validation before activation, including cross-field constraints, endpoint syntax, credential references, timeout relationships, policy conflicts, and trust-sensitive fail-closed checks.
- [ ] **G12-F068-03** Separate immutable artifact configuration from environment/site overlays and secret references; record the fully resolved effective configuration fingerprint.
- [ ] **G12-F068-04** Apply configuration changes atomically with preflight, staged activation, health verification, rollback, and clear behavior for in-flight sessions.
- [ ] **G12-F068-05** Record provenance for every effective configuration: source, author/automation identity, version, generation, activation timestamp, approval/waiver references, and cryptographic digest where supported.
- [ ] **G12-F068-06** Test malformed input, unknown fields, rollback, partial dependency availability, concurrent reload, downgrade, secret rotation, and recovery after failed activation.
- [ ] **G12-F068-07** Implement and document the exact behavior required by this inventory item: **Configuration validation before activation with fail-closed rules for trust-sensitive fields**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-F068-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-F068-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-F068-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-F068-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-F068-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-F068-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-F068-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-F068-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-F068-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-F068-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-F068-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-F068-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-F068-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-F068`.

### 69. Environment/site overlays — P0

**Component ID:** `G12-F069`  
**Objective:** Environment/site overlays without rebuilding immutable artifacts.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-F069-01** Define a versioned machine-readable schema with type/range/enum constraints, defaults, deprecations, unknown-field behavior, and forward/backward compatibility rules.
- [ ] **G12-F069-02** Perform semantic validation before activation, including cross-field constraints, endpoint syntax, credential references, timeout relationships, policy conflicts, and trust-sensitive fail-closed checks.
- [ ] **G12-F069-03** Separate immutable artifact configuration from environment/site overlays and secret references; record the fully resolved effective configuration fingerprint.
- [ ] **G12-F069-04** Apply configuration changes atomically with preflight, staged activation, health verification, rollback, and clear behavior for in-flight sessions.
- [ ] **G12-F069-05** Record provenance for every effective configuration: source, author/automation identity, version, generation, activation timestamp, approval/waiver references, and cryptographic digest where supported.
- [ ] **G12-F069-06** Test malformed input, unknown fields, rollback, partial dependency availability, concurrent reload, downgrade, secret rotation, and recovery after failed activation.
- [ ] **G12-F069-07** Implement and document the exact behavior required by this inventory item: **Environment/site overlays without rebuilding immutable artifacts**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-F069-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-F069-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-F069-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-F069-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-F069-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-F069-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-F069-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-F069-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-F069-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-F069-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-F069-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-F069-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-F069-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-F069`.

### 70. Atomic configuration reload/rollback — P0

**Component ID:** `G12-F070`  
**Objective:** Atomic configuration reload/rollback .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-F070-01** Define a versioned machine-readable schema with type/range/enum constraints, defaults, deprecations, unknown-field behavior, and forward/backward compatibility rules.
- [ ] **G12-F070-02** Perform semantic validation before activation, including cross-field constraints, endpoint syntax, credential references, timeout relationships, policy conflicts, and trust-sensitive fail-closed checks.
- [ ] **G12-F070-03** Separate immutable artifact configuration from environment/site overlays and secret references; record the fully resolved effective configuration fingerprint.
- [ ] **G12-F070-04** Apply configuration changes atomically with preflight, staged activation, health verification, rollback, and clear behavior for in-flight sessions.
- [ ] **G12-F070-05** Record provenance for every effective configuration: source, author/automation identity, version, generation, activation timestamp, approval/waiver references, and cryptographic digest where supported.
- [ ] **G12-F070-06** Test malformed input, unknown fields, rollback, partial dependency availability, concurrent reload, downgrade, secret rotation, and recovery after failed activation.
- [ ] **G12-F070-07** Implement and document the exact behavior required by this inventory item: **Atomic configuration reload/rollback **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-F070-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-F070-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-F070-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-F070-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-F070-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-F070-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-F070-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-F070-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-F070-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-F070-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-F070-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-F070-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-F070-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-F070`.

### 71. Configuration provenance — P0

**Component ID:** `G12-F071`  
**Objective:** Configuration provenance including author/source/version/activation time.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-F071-01** Define a versioned machine-readable schema with type/range/enum constraints, defaults, deprecations, unknown-field behavior, and forward/backward compatibility rules.
- [ ] **G12-F071-02** Perform semantic validation before activation, including cross-field constraints, endpoint syntax, credential references, timeout relationships, policy conflicts, and trust-sensitive fail-closed checks.
- [ ] **G12-F071-03** Separate immutable artifact configuration from environment/site overlays and secret references; record the fully resolved effective configuration fingerprint.
- [ ] **G12-F071-04** Apply configuration changes atomically with preflight, staged activation, health verification, rollback, and clear behavior for in-flight sessions.
- [ ] **G12-F071-05** Record provenance for every effective configuration: source, author/automation identity, version, generation, activation timestamp, approval/waiver references, and cryptographic digest where supported.
- [ ] **G12-F071-06** Test malformed input, unknown fields, rollback, partial dependency availability, concurrent reload, downgrade, secret rotation, and recovery after failed activation.
- [ ] **G12-F071-07** Implement and document the exact behavior required by this inventory item: **Configuration provenance including author/source/version/activation time**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-F071-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-F071-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-F071-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-F071-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-F071-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-F071-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-F071-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-F071-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-F071-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-F071-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-F071-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-F071-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-F071-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-F071`.

### 72. Policy for enabling/disabling traversal mechanisms — P1

**Component ID:** `G12-F072`  
**Objective:** Policy for enabling/disabling traversal mechanisms per environment or network zone.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-F072-01** Define a versioned machine-readable schema with type/range/enum constraints, defaults, deprecations, unknown-field behavior, and forward/backward compatibility rules.
- [ ] **G12-F072-02** Perform semantic validation before activation, including cross-field constraints, endpoint syntax, credential references, timeout relationships, policy conflicts, and trust-sensitive fail-closed checks.
- [ ] **G12-F072-03** Separate immutable artifact configuration from environment/site overlays and secret references; record the fully resolved effective configuration fingerprint.
- [ ] **G12-F072-04** Apply configuration changes atomically with preflight, staged activation, health verification, rollback, and clear behavior for in-flight sessions.
- [ ] **G12-F072-05** Record provenance for every effective configuration: source, author/automation identity, version, generation, activation timestamp, approval/waiver references, and cryptographic digest where supported.
- [ ] **G12-F072-06** Test malformed input, unknown fields, rollback, partial dependency availability, concurrent reload, downgrade, secret rotation, and recovery after failed activation.
- [ ] **G12-F072-07** Implement and document the exact behavior required by this inventory item: **Policy for enabling/disabling traversal mechanisms per environment or network zone**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-F072-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-F072-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-F072-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-F072-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-F072-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-F072-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-F072-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-F072-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-F072-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-F072-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-F072-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-F072-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-F072-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-F072`.

### 73. Relay cost policy — P1

**Component ID:** `G12-F073`  
**Objective:** Relay cost policy including regional price/budget metadata.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-F073-01** Define a versioned machine-readable schema with type/range/enum constraints, defaults, deprecations, unknown-field behavior, and forward/backward compatibility rules.
- [ ] **G12-F073-02** Perform semantic validation before activation, including cross-field constraints, endpoint syntax, credential references, timeout relationships, policy conflicts, and trust-sensitive fail-closed checks.
- [ ] **G12-F073-03** Separate immutable artifact configuration from environment/site overlays and secret references; record the fully resolved effective configuration fingerprint.
- [ ] **G12-F073-04** Apply configuration changes atomically with preflight, staged activation, health verification, rollback, and clear behavior for in-flight sessions.
- [ ] **G12-F073-05** Record provenance for every effective configuration: source, author/automation identity, version, generation, activation timestamp, approval/waiver references, and cryptographic digest where supported.
- [ ] **G12-F073-06** Test malformed input, unknown fields, rollback, partial dependency availability, concurrent reload, downgrade, secret rotation, and recovery after failed activation.
- [ ] **G12-F073-07** Implement and document the exact behavior required by this inventory item: **Relay cost policy including regional price/budget metadata**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-F073-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-F073-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-F073-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-F073-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-F073-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-F073-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-F073-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-F073-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-F073-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-F073-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-F073-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-F073-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-F073-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-F073`.

### 74. Feature flags with expiry/ownership — P1

**Component ID:** `G12-F074`  
**Objective:** Feature flags with expiry/ownership for staged rollout of traversal methods.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-F074-01** Define a versioned machine-readable schema with type/range/enum constraints, defaults, deprecations, unknown-field behavior, and forward/backward compatibility rules.
- [ ] **G12-F074-02** Perform semantic validation before activation, including cross-field constraints, endpoint syntax, credential references, timeout relationships, policy conflicts, and trust-sensitive fail-closed checks.
- [ ] **G12-F074-03** Separate immutable artifact configuration from environment/site overlays and secret references; record the fully resolved effective configuration fingerprint.
- [ ] **G12-F074-04** Apply configuration changes atomically with preflight, staged activation, health verification, rollback, and clear behavior for in-flight sessions.
- [ ] **G12-F074-05** Record provenance for every effective configuration: source, author/automation identity, version, generation, activation timestamp, approval/waiver references, and cryptographic digest where supported.
- [ ] **G12-F074-06** Test malformed input, unknown fields, rollback, partial dependency availability, concurrent reload, downgrade, secret rotation, and recovery after failed activation.
- [ ] **G12-F074-07** Implement and document the exact behavior required by this inventory item: **Feature flags with expiry/ownership for staged rollout of traversal methods**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-F074-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-F074-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-F074-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-F074-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-F074-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-F074-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-F074-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-F074-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-F074-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-F074-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-F074-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-F074-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-F074-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-F074`.

## G. Observability and operator experience

### 75. Metrics exporter — P0

**Component ID:** `G12-G075`  
**Objective:** Metrics exporter for attempts, outcomes, latency, backoff, partitions, relay bytes, and dependency health.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-G075-01** Define metric name/type/unit/help text, label set, cardinality budget, aggregation ownership, reset semantics, and histogram bucket strategy.
- [ ] **G12-G075-02** Include explicit counters/gauges/histograms for attempt outcomes, establishment latency, active paths, partitions, retries/backoff, relay bytes/cost, dependency health, and policy/security rejections.
- [ ] **G12-G075-03** Define a stable telemetry vocabulary for component state, decisions, failures, dependency status, policy outcomes, and lifecycle events; version externally consumed schemas.
- [ ] **G12-G075-04** Control metric label/cardinality growth; never use raw peer IDs, IPs, candidate strings, exceptions, or arbitrary URLs as unbounded metric dimensions.
- [ ] **G12-G075-05** Apply structured endpoint/identity redaction and privacy policy consistently to logs, traces, metrics, diagnostics bundles, and operator UIs.
- [ ] **G12-G075-06** Propagate operation/correlation identifiers across control-plane and data-plane establishment while preserving tenant boundaries and sampling policy.
- [ ] **G12-G075-07** Expose reason codes that distinguish network failure, dependency failure, policy rejection, authentication failure, quota/budget exhaustion, software defect, cancellation, and operator action.
- [ ] **G12-G075-08** Validate dashboards and alerts using synthetic failure injection so operators can distinguish ordinary load from a retry storm, relay saturation, DNS failure, traversal regression, or security event.
- [ ] **G12-G075-09** Implement and document the exact behavior required by this inventory item: **Metrics exporter for attempts, outcomes, latency, backoff, partitions, relay bytes, and dependency health**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-G075-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-G075-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-G075-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-G075-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-G075-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-G075-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-G075-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-G075-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-G075-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-G075-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-G075-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-G075-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-G075-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-G075`.

### 76. Structured logging — P0

**Component ID:** `G12-G076`  
**Objective:** Structured logging with stable site/peer/operation identifiers and endpoint redaction.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-G076-01** Emit machine-parseable events with stable event IDs/severity/reason codes and bounded fields; prohibit free-form dumps of endpoint/candidate/credential objects.
- [ ] **G12-G076-02** Define sampling/rate suppression for repeated failures while retaining aggregate counts and first/last occurrence evidence.
- [ ] **G12-G076-03** Define a stable telemetry vocabulary for component state, decisions, failures, dependency status, policy outcomes, and lifecycle events; version externally consumed schemas.
- [ ] **G12-G076-04** Control metric label/cardinality growth; never use raw peer IDs, IPs, candidate strings, exceptions, or arbitrary URLs as unbounded metric dimensions.
- [ ] **G12-G076-05** Apply structured endpoint/identity redaction and privacy policy consistently to logs, traces, metrics, diagnostics bundles, and operator UIs.
- [ ] **G12-G076-06** Propagate operation/correlation identifiers across control-plane and data-plane establishment while preserving tenant boundaries and sampling policy.
- [ ] **G12-G076-07** Expose reason codes that distinguish network failure, dependency failure, policy rejection, authentication failure, quota/budget exhaustion, software defect, cancellation, and operator action.
- [ ] **G12-G076-08** Validate dashboards and alerts using synthetic failure injection so operators can distinguish ordinary load from a retry storm, relay saturation, DNS failure, traversal regression, or security event.
- [ ] **G12-G076-09** Implement and document the exact behavior required by this inventory item: **Structured logging with stable site/peer/operation identifiers and endpoint redaction**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-G076-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-G076-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-G076-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-G076-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-G076-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-G076-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-G076-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-G076-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-G076-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-G076-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-G076-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-G076-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-G076-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-G076`.

### 77. Distributed trace propagation — P0

**Component ID:** `G12-G077`  
**Objective:** Distributed trace propagation across control and data-plane path establishment.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-G077-01** Define span boundaries for request, candidate gathering, each strategy attempt, authentication, relay allocation, path validation, migration, and teardown.
- [ ] **G12-G077-02** Propagate trace context only across trusted boundaries and prevent untrusted peers from selecting arbitrary internal trace identifiers.
- [ ] **G12-G077-03** Define a stable telemetry vocabulary for component state, decisions, failures, dependency status, policy outcomes, and lifecycle events; version externally consumed schemas.
- [ ] **G12-G077-04** Control metric label/cardinality growth; never use raw peer IDs, IPs, candidate strings, exceptions, or arbitrary URLs as unbounded metric dimensions.
- [ ] **G12-G077-05** Apply structured endpoint/identity redaction and privacy policy consistently to logs, traces, metrics, diagnostics bundles, and operator UIs.
- [ ] **G12-G077-06** Propagate operation/correlation identifiers across control-plane and data-plane establishment while preserving tenant boundaries and sampling policy.
- [ ] **G12-G077-07** Expose reason codes that distinguish network failure, dependency failure, policy rejection, authentication failure, quota/budget exhaustion, software defect, cancellation, and operator action.
- [ ] **G12-G077-08** Validate dashboards and alerts using synthetic failure injection so operators can distinguish ordinary load from a retry storm, relay saturation, DNS failure, traversal regression, or security event.
- [ ] **G12-G077-09** Implement and document the exact behavior required by this inventory item: **Distributed trace propagation across control and data-plane path establishment**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-G077-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-G077-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-G077-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-G077-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-G077-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-G077-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-G077-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-G077-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-G077-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-G077-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-G077-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-G077-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-G077-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-G077`.

### 78. Health/readiness endpoint — P0

**Component ID:** `G12-G078`  
**Objective:** Health/readiness endpoint exposing version, configuration generation, dependencies, and active capabilities.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-G078-01** Define a stable telemetry vocabulary for component state, decisions, failures, dependency status, policy outcomes, and lifecycle events; version externally consumed schemas.
- [ ] **G12-G078-02** Control metric label/cardinality growth; never use raw peer IDs, IPs, candidate strings, exceptions, or arbitrary URLs as unbounded metric dimensions.
- [ ] **G12-G078-03** Apply structured endpoint/identity redaction and privacy policy consistently to logs, traces, metrics, diagnostics bundles, and operator UIs.
- [ ] **G12-G078-04** Propagate operation/correlation identifiers across control-plane and data-plane establishment while preserving tenant boundaries and sampling policy.
- [ ] **G12-G078-05** Expose reason codes that distinguish network failure, dependency failure, policy rejection, authentication failure, quota/budget exhaustion, software defect, cancellation, and operator action.
- [ ] **G12-G078-06** Validate dashboards and alerts using synthetic failure injection so operators can distinguish ordinary load from a retry storm, relay saturation, DNS failure, traversal regression, or security event.
- [ ] **G12-G078-07** Implement and document the exact behavior required by this inventory item: **Health/readiness endpoint exposing version, configuration generation, dependencies, and active capabilities**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-G078-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-G078-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-G078-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-G078-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-G078-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-G078-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-G078-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-G078-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-G078-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-G078-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-G078-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-G078-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-G078-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-G078`.

### 79. Reason codes — P0

**Component ID:** `G12-G079`  
**Objective:** Reason codes for every automated path-selection/failover decision.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-G079-01** Define a stable telemetry vocabulary for component state, decisions, failures, dependency status, policy outcomes, and lifecycle events; version externally consumed schemas.
- [ ] **G12-G079-02** Control metric label/cardinality growth; never use raw peer IDs, IPs, candidate strings, exceptions, or arbitrary URLs as unbounded metric dimensions.
- [ ] **G12-G079-03** Apply structured endpoint/identity redaction and privacy policy consistently to logs, traces, metrics, diagnostics bundles, and operator UIs.
- [ ] **G12-G079-04** Propagate operation/correlation identifiers across control-plane and data-plane establishment while preserving tenant boundaries and sampling policy.
- [ ] **G12-G079-05** Expose reason codes that distinguish network failure, dependency failure, policy rejection, authentication failure, quota/budget exhaustion, software defect, cancellation, and operator action.
- [ ] **G12-G079-06** Validate dashboards and alerts using synthetic failure injection so operators can distinguish ordinary load from a retry storm, relay saturation, DNS failure, traversal regression, or security event.
- [ ] **G12-G079-07** Implement and document the exact behavior required by this inventory item: **Reason codes for every automated path-selection/failover decision**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-G079-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-G079-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-G079-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-G079-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-G079-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-G079-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-G079-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-G079-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-G079-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-G079-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-G079-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-G079-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-G079-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-G079`.

### 80. Operator explain view — P1

**Component ID:** `G12-G080`  
**Objective:** Operator explain view linking selected strategy to probe outcomes and constraints.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-G080-01** Define a stable telemetry vocabulary for component state, decisions, failures, dependency status, policy outcomes, and lifecycle events; version externally consumed schemas.
- [ ] **G12-G080-02** Control metric label/cardinality growth; never use raw peer IDs, IPs, candidate strings, exceptions, or arbitrary URLs as unbounded metric dimensions.
- [ ] **G12-G080-03** Apply structured endpoint/identity redaction and privacy policy consistently to logs, traces, metrics, diagnostics bundles, and operator UIs.
- [ ] **G12-G080-04** Propagate operation/correlation identifiers across control-plane and data-plane establishment while preserving tenant boundaries and sampling policy.
- [ ] **G12-G080-05** Expose reason codes that distinguish network failure, dependency failure, policy rejection, authentication failure, quota/budget exhaustion, software defect, cancellation, and operator action.
- [ ] **G12-G080-06** Validate dashboards and alerts using synthetic failure injection so operators can distinguish ordinary load from a retry storm, relay saturation, DNS failure, traversal regression, or security event.
- [ ] **G12-G080-07** Implement and document the exact behavior required by this inventory item: **Operator explain view linking selected strategy to probe outcomes and constraints**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-G080-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-G080-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-G080-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-G080-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-G080-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-G080-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-G080-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-G080-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-G080-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-G080-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-G080-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-G080-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-G080-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-G080`.

### 81. Dashboards — P0

**Component ID:** `G12-G081`  
**Objective:** Dashboards separating ordinary load, network degradation, dependency failure, policy rejection, attack, and software defect.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-G081-01** Define a stable telemetry vocabulary for component state, decisions, failures, dependency status, policy outcomes, and lifecycle events; version externally consumed schemas.
- [ ] **G12-G081-02** Control metric label/cardinality growth; never use raw peer IDs, IPs, candidate strings, exceptions, or arbitrary URLs as unbounded metric dimensions.
- [ ] **G12-G081-03** Apply structured endpoint/identity redaction and privacy policy consistently to logs, traces, metrics, diagnostics bundles, and operator UIs.
- [ ] **G12-G081-04** Propagate operation/correlation identifiers across control-plane and data-plane establishment while preserving tenant boundaries and sampling policy.
- [ ] **G12-G081-05** Expose reason codes that distinguish network failure, dependency failure, policy rejection, authentication failure, quota/budget exhaustion, software defect, cancellation, and operator action.
- [ ] **G12-G081-06** Validate dashboards and alerts using synthetic failure injection so operators can distinguish ordinary load from a retry storm, relay saturation, DNS failure, traversal regression, or security event.
- [ ] **G12-G081-07** Implement and document the exact behavior required by this inventory item: **Dashboards separating ordinary load, network degradation, dependency failure, policy rejection, attack, and software defect**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-G081-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-G081-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-G081-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-G081-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-G081-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-G081-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-G081-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-G081-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-G081-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-G081-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-G081-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-G081-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-G081-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-G081`.

### 82. Alerts/SLO burn rules — P0

**Component ID:** `G12-G082`  
**Objective:** Alerts/SLO burn rules for partition rate, establishment latency, retry storms, and relay saturation/cost.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-G082-01** Define a stable telemetry vocabulary for component state, decisions, failures, dependency status, policy outcomes, and lifecycle events; version externally consumed schemas.
- [ ] **G12-G082-02** Control metric label/cardinality growth; never use raw peer IDs, IPs, candidate strings, exceptions, or arbitrary URLs as unbounded metric dimensions.
- [ ] **G12-G082-03** Apply structured endpoint/identity redaction and privacy policy consistently to logs, traces, metrics, diagnostics bundles, and operator UIs.
- [ ] **G12-G082-04** Propagate operation/correlation identifiers across control-plane and data-plane establishment while preserving tenant boundaries and sampling policy.
- [ ] **G12-G082-05** Expose reason codes that distinguish network failure, dependency failure, policy rejection, authentication failure, quota/budget exhaustion, software defect, cancellation, and operator action.
- [ ] **G12-G082-06** Validate dashboards and alerts using synthetic failure injection so operators can distinguish ordinary load from a retry storm, relay saturation, DNS failure, traversal regression, or security event.
- [ ] **G12-G082-07** Implement and document the exact behavior required by this inventory item: **Alerts/SLO burn rules for partition rate, establishment latency, retry storms, and relay saturation/cost**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-G082-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-G082-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-G082-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-G082-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-G082-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-G082-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-G082-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-G082-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-G082-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-G082-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-G082-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-G082-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-G082-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-G082`.

### 83. Telemetry retention/sampling/privacy policy — P1

**Component ID:** `G12-G083`  
**Objective:** Telemetry retention/sampling/privacy policy .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-G083-01** Define a stable telemetry vocabulary for component state, decisions, failures, dependency status, policy outcomes, and lifecycle events; version externally consumed schemas.
- [ ] **G12-G083-02** Control metric label/cardinality growth; never use raw peer IDs, IPs, candidate strings, exceptions, or arbitrary URLs as unbounded metric dimensions.
- [ ] **G12-G083-03** Apply structured endpoint/identity redaction and privacy policy consistently to logs, traces, metrics, diagnostics bundles, and operator UIs.
- [ ] **G12-G083-04** Propagate operation/correlation identifiers across control-plane and data-plane establishment while preserving tenant boundaries and sampling policy.
- [ ] **G12-G083-05** Expose reason codes that distinguish network failure, dependency failure, policy rejection, authentication failure, quota/budget exhaustion, software defect, cancellation, and operator action.
- [ ] **G12-G083-06** Validate dashboards and alerts using synthetic failure injection so operators can distinguish ordinary load from a retry storm, relay saturation, DNS failure, traversal regression, or security event.
- [ ] **G12-G083-07** Implement and document the exact behavior required by this inventory item: **Telemetry retention/sampling/privacy policy **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-G083-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-G083-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-G083-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-G083-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-G083-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-G083-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-G083-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-G083-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-G083-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-G083-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-G083-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-G083-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-G083-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-G083`.

### 84. Correlation with deployment/release lineage and topology graph — P1

**Component ID:** `G12-G084`  
**Objective:** Correlation with deployment/release lineage and topology graph .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-G084-01** Define a stable telemetry vocabulary for component state, decisions, failures, dependency status, policy outcomes, and lifecycle events; version externally consumed schemas.
- [ ] **G12-G084-02** Control metric label/cardinality growth; never use raw peer IDs, IPs, candidate strings, exceptions, or arbitrary URLs as unbounded metric dimensions.
- [ ] **G12-G084-03** Apply structured endpoint/identity redaction and privacy policy consistently to logs, traces, metrics, diagnostics bundles, and operator UIs.
- [ ] **G12-G084-04** Propagate operation/correlation identifiers across control-plane and data-plane establishment while preserving tenant boundaries and sampling policy.
- [ ] **G12-G084-05** Expose reason codes that distinguish network failure, dependency failure, policy rejection, authentication failure, quota/budget exhaustion, software defect, cancellation, and operator action.
- [ ] **G12-G084-06** Validate dashboards and alerts using synthetic failure injection so operators can distinguish ordinary load from a retry storm, relay saturation, DNS failure, traversal regression, or security event.
- [ ] **G12-G084-07** Implement and document the exact behavior required by this inventory item: **Correlation with deployment/release lineage and topology graph **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-G084-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-G084-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-G084-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-G084-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-G084-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-G084-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-G084-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-G084-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-G084-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-G084-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-G084-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-G084-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-G084-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-G084`.

## H. Testing, emulation, and certification

### 85. Unit tests for every transition and boundary value — P0

**Component ID:** `G12-H085`  
**Objective:** Unit tests for every transition and boundary value beyond the included reference tests.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-H085-01** Define deterministic test topology, fixtures, seeds, clocks, packet impairment parameters, dependency versions, and pass/fail assertions so failures are reproducible.
- [ ] **G12-H085-02** Cover happy path, every documented failure branch, boundary values, timeout edges, cancellation, duplicate/late events, malformed inputs, and cleanup/resource-release behavior.
- [ ] **G12-H085-03** Run tests under IPv4, IPv6, dual-stack, NAT variants, CGNAT-like topologies, UDP-blocked/TCP-only paths, DNS impairment, route churn, and relay/direct combinations as applicable.
- [ ] **G12-H085-04** Add negative security cases for spoofing, replay, unauthorized relay use, malicious candidates/configuration, parser abuse, retry amplification, and resource exhaustion.
- [ ] **G12-H085-05** Produce machine-readable results containing build ID, configuration digest, dependency versions, topology description, test seed, timing data, failures, and retained artifacts.
- [ ] **G12-H085-06** Gate release on zero skipped mandatory tests; an absent dependency or unavailable environment must produce NOT-EVIDENCED/FAIL status rather than an implicit pass.
- [ ] **G12-H085-07** Implement and document the exact behavior required by this inventory item: **Unit tests for every transition and boundary value beyond the included reference tests**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-H085-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-H085-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-H085-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-H085-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-H085-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-H085-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-H085-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-H085-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-H085-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-H085-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-H085-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-H085-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-H085-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-H085`.

### 86. Contract/schema tests for `PK_PATH_REQUEST/1`, `PK_PATH_STATE/1`, `PK_BACKOFF/1`, and relay accounting — P0

**Component ID:** `G12-H086`  
**Objective:** Contract/schema tests for `PK_PATH_REQUEST/1`, `PK_PATH_STATE/1`, `PK_BACKOFF/1`, and relay accounting .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-H086-01** Define deterministic test topology, fixtures, seeds, clocks, packet impairment parameters, dependency versions, and pass/fail assertions so failures are reproducible.
- [ ] **G12-H086-02** Cover happy path, every documented failure branch, boundary values, timeout edges, cancellation, duplicate/late events, malformed inputs, and cleanup/resource-release behavior.
- [ ] **G12-H086-03** Run tests under IPv4, IPv6, dual-stack, NAT variants, CGNAT-like topologies, UDP-blocked/TCP-only paths, DNS impairment, route churn, and relay/direct combinations as applicable.
- [ ] **G12-H086-04** Add negative security cases for spoofing, replay, unauthorized relay use, malicious candidates/configuration, parser abuse, retry amplification, and resource exhaustion.
- [ ] **G12-H086-05** Produce machine-readable results containing build ID, configuration digest, dependency versions, topology description, test seed, timing data, failures, and retained artifacts.
- [ ] **G12-H086-06** Gate release on zero skipped mandatory tests; an absent dependency or unavailable environment must produce NOT-EVIDENCED/FAIL status rather than an implicit pass.
- [ ] **G12-H086-07** Implement and document the exact behavior required by this inventory item: **Contract/schema tests for `PK_PATH_REQUEST/1`, `PK_PATH_STATE/1`, `PK_BACKOFF/1`, and relay accounting **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-H086-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-H086-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-H086-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-H086-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-H086-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-H086-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-H086-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-H086-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-H086-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-H086-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-H086-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-H086-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-H086-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-H086`.

### 87. Integration tests against real STUN/TURN implementations — P0

**Component ID:** `G12-H087`  
**Objective:** Integration tests against real STUN/TURN implementations .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-H087-01** Implement RFC 8489-compatible Binding transactions, transaction-ID matching, XOR-MAPPED-ADDRESS parsing, MESSAGE-INTEGRITY/FINGERPRINT handling when configured, and retransmission timing appropriate to the selected transport.
- [ ] **G12-H087-02** Verify discovery against multiple independent STUN servers and distinguish server failure, DNS failure, blocked UDP, malformed response, and mapping inconsistency.
- [ ] **G12-H087-03** Implement Allocate, Refresh, CreatePermission, ChannelBind, Send/Data indications, channel-data framing, allocation expiry, and deterministic teardown; enforce authenticated access and realm/nonce handling.
- [ ] **G12-H087-04** Validate UDP/TCP/TLS TURN transports required by policy, permission/channel refresh timers, quota accounting, server failover, and credential rotation without orphaning allocations.
- [ ] **G12-H087-05** Define deterministic test topology, fixtures, seeds, clocks, packet impairment parameters, dependency versions, and pass/fail assertions so failures are reproducible.
- [ ] **G12-H087-06** Cover happy path, every documented failure branch, boundary values, timeout edges, cancellation, duplicate/late events, malformed inputs, and cleanup/resource-release behavior.
- [ ] **G12-H087-07** Run tests under IPv4, IPv6, dual-stack, NAT variants, CGNAT-like topologies, UDP-blocked/TCP-only paths, DNS impairment, route churn, and relay/direct combinations as applicable.
- [ ] **G12-H087-08** Add negative security cases for spoofing, replay, unauthorized relay use, malicious candidates/configuration, parser abuse, retry amplification, and resource exhaustion.
- [ ] **G12-H087-09** Produce machine-readable results containing build ID, configuration digest, dependency versions, topology description, test seed, timing data, failures, and retained artifacts.
- [ ] **G12-H087-10** Gate release on zero skipped mandatory tests; an absent dependency or unavailable environment must produce NOT-EVIDENCED/FAIL status rather than an implicit pass.
- [ ] **G12-H087-11** Implement and document the exact behavior required by this inventory item: **Integration tests against real STUN/TURN implementations **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-H087-12** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-H087-13** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-H087-14** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-H087-15** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-H087-16** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-H087-17** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-H087-18** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-H087-19** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-H087-20** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-H087-21** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-H087-22** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-H087-23** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-H087-24** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-H087`.

### 88. NAT matrix test lab — P0

**Component ID:** `G12-H088`  
**Objective:** NAT matrix test lab covering full-cone/restricted/port-restricted/symmetric/CGNAT behavior.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-H088-01** Build reproducible topologies representing mapping and filtering combinations rather than relying only on NAT marketing labels; encode each topology as version-controlled infrastructure.
- [ ] **G12-H088-02** Capture gateway rules/configuration, packet traces, expected external mappings, filtering behavior, and teardown state as test evidence.
- [ ] **G12-H088-03** Define deterministic test topology, fixtures, seeds, clocks, packet impairment parameters, dependency versions, and pass/fail assertions so failures are reproducible.
- [ ] **G12-H088-04** Cover happy path, every documented failure branch, boundary values, timeout edges, cancellation, duplicate/late events, malformed inputs, and cleanup/resource-release behavior.
- [ ] **G12-H088-05** Run tests under IPv4, IPv6, dual-stack, NAT variants, CGNAT-like topologies, UDP-blocked/TCP-only paths, DNS impairment, route churn, and relay/direct combinations as applicable.
- [ ] **G12-H088-06** Add negative security cases for spoofing, replay, unauthorized relay use, malicious candidates/configuration, parser abuse, retry amplification, and resource exhaustion.
- [ ] **G12-H088-07** Produce machine-readable results containing build ID, configuration digest, dependency versions, topology description, test seed, timing data, failures, and retained artifacts.
- [ ] **G12-H088-08** Gate release on zero skipped mandatory tests; an absent dependency or unavailable environment must produce NOT-EVIDENCED/FAIL status rather than an implicit pass.
- [ ] **G12-H088-09** Implement and document the exact behavior required by this inventory item: **NAT matrix test lab covering full-cone/restricted/port-restricted/symmetric/CGNAT behavior**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-H088-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-H088-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-H088-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-H088-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-H088-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-H088-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-H088-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-H088-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-H088-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-H088-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-H088-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-H088-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-H088-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-H088`.

### 89. Network-namespace/container emulation — P0

**Component ID:** `G12-H089`  
**Objective:** Network-namespace/container emulation for packet loss, latency, jitter, reordering, duplication, and corruption.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-H089-01** Automate namespaces/containers/virtual links with deterministic impairment controls for delay, loss, jitter, duplication, reordering, corruption, bandwidth, queue depth, and MTU.
- [ ] **G12-H089-02** Ensure test cleanup removes routes, namespaces, firewall rules, qdiscs, sockets, and temporary credentials even after aborted runs.
- [ ] **G12-H089-03** Define deterministic test topology, fixtures, seeds, clocks, packet impairment parameters, dependency versions, and pass/fail assertions so failures are reproducible.
- [ ] **G12-H089-04** Cover happy path, every documented failure branch, boundary values, timeout edges, cancellation, duplicate/late events, malformed inputs, and cleanup/resource-release behavior.
- [ ] **G12-H089-05** Run tests under IPv4, IPv6, dual-stack, NAT variants, CGNAT-like topologies, UDP-blocked/TCP-only paths, DNS impairment, route churn, and relay/direct combinations as applicable.
- [ ] **G12-H089-06** Add negative security cases for spoofing, replay, unauthorized relay use, malicious candidates/configuration, parser abuse, retry amplification, and resource exhaustion.
- [ ] **G12-H089-07** Produce machine-readable results containing build ID, configuration digest, dependency versions, topology description, test seed, timing data, failures, and retained artifacts.
- [ ] **G12-H089-08** Gate release on zero skipped mandatory tests; an absent dependency or unavailable environment must produce NOT-EVIDENCED/FAIL status rather than an implicit pass.
- [ ] **G12-H089-09** Implement and document the exact behavior required by this inventory item: **Network-namespace/container emulation for packet loss, latency, jitter, reordering, duplication, and corruption**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-H089-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-H089-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-H089-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-H089-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-H089-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-H089-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-H089-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-H089-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-H089-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-H089-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-H089-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-H089-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-H089-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-H089`.

### 90. Partition/reconnect/flap tests — P0

**Component ID:** `G12-H090`  
**Objective:** Partition/reconnect/flap tests with exact recovery objectives.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-H090-01** Define deterministic test topology, fixtures, seeds, clocks, packet impairment parameters, dependency versions, and pass/fail assertions so failures are reproducible.
- [ ] **G12-H090-02** Cover happy path, every documented failure branch, boundary values, timeout edges, cancellation, duplicate/late events, malformed inputs, and cleanup/resource-release behavior.
- [ ] **G12-H090-03** Run tests under IPv4, IPv6, dual-stack, NAT variants, CGNAT-like topologies, UDP-blocked/TCP-only paths, DNS impairment, route churn, and relay/direct combinations as applicable.
- [ ] **G12-H090-04** Add negative security cases for spoofing, replay, unauthorized relay use, malicious candidates/configuration, parser abuse, retry amplification, and resource exhaustion.
- [ ] **G12-H090-05** Produce machine-readable results containing build ID, configuration digest, dependency versions, topology description, test seed, timing data, failures, and retained artifacts.
- [ ] **G12-H090-06** Gate release on zero skipped mandatory tests; an absent dependency or unavailable environment must produce NOT-EVIDENCED/FAIL status rather than an implicit pass.
- [ ] **G12-H090-07** Implement and document the exact behavior required by this inventory item: **Partition/reconnect/flap tests with exact recovery objectives**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-H090-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-H090-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-H090-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-H090-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-H090-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-H090-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-H090-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-H090-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-H090-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-H090-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-H090-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-H090-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-H090-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-H090`.

### 91. DNS outage/poison/stale-cache tests — P0

**Component ID:** `G12-H091`  
**Objective:** DNS outage/poison/stale-cache tests .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-H091-01** Define deterministic test topology, fixtures, seeds, clocks, packet impairment parameters, dependency versions, and pass/fail assertions so failures are reproducible.
- [ ] **G12-H091-02** Cover happy path, every documented failure branch, boundary values, timeout edges, cancellation, duplicate/late events, malformed inputs, and cleanup/resource-release behavior.
- [ ] **G12-H091-03** Run tests under IPv4, IPv6, dual-stack, NAT variants, CGNAT-like topologies, UDP-blocked/TCP-only paths, DNS impairment, route churn, and relay/direct combinations as applicable.
- [ ] **G12-H091-04** Add negative security cases for spoofing, replay, unauthorized relay use, malicious candidates/configuration, parser abuse, retry amplification, and resource exhaustion.
- [ ] **G12-H091-05** Produce machine-readable results containing build ID, configuration digest, dependency versions, topology description, test seed, timing data, failures, and retained artifacts.
- [ ] **G12-H091-06** Gate release on zero skipped mandatory tests; an absent dependency or unavailable environment must produce NOT-EVIDENCED/FAIL status rather than an implicit pass.
- [ ] **G12-H091-07** Implement and document the exact behavior required by this inventory item: **DNS outage/poison/stale-cache tests **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-H091-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-H091-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-H091-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-H091-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-H091-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-H091-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-H091-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-H091-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-H091-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-H091-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-H091-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-H091-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-H091-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-H091`.

### 92. IPv4/IPv6/NAT64 compatibility matrix — P0

**Component ID:** `G12-H092`  
**Objective:** IPv4/IPv6/NAT64 compatibility matrix .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-H092-01** Define deterministic test topology, fixtures, seeds, clocks, packet impairment parameters, dependency versions, and pass/fail assertions so failures are reproducible.
- [ ] **G12-H092-02** Cover happy path, every documented failure branch, boundary values, timeout edges, cancellation, duplicate/late events, malformed inputs, and cleanup/resource-release behavior.
- [ ] **G12-H092-03** Run tests under IPv4, IPv6, dual-stack, NAT variants, CGNAT-like topologies, UDP-blocked/TCP-only paths, DNS impairment, route churn, and relay/direct combinations as applicable.
- [ ] **G12-H092-04** Add negative security cases for spoofing, replay, unauthorized relay use, malicious candidates/configuration, parser abuse, retry amplification, and resource exhaustion.
- [ ] **G12-H092-05** Produce machine-readable results containing build ID, configuration digest, dependency versions, topology description, test seed, timing data, failures, and retained artifacts.
- [ ] **G12-H092-06** Gate release on zero skipped mandatory tests; an absent dependency or unavailable environment must produce NOT-EVIDENCED/FAIL status rather than an implicit pass.
- [ ] **G12-H092-07** Implement and document the exact behavior required by this inventory item: **IPv4/IPv6/NAT64 compatibility matrix **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-H092-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-H092-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-H092-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-H092-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-H092-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-H092-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-H092-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-H092-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-H092-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-H092-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-H092-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-H092-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-H092-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-H092`.

### 93. Firewall/UDP-blocked/captive-portal test scenarios — P0

**Component ID:** `G12-H093`  
**Objective:** Firewall/UDP-blocked/captive-portal test scenarios .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-H093-01** Define deterministic test topology, fixtures, seeds, clocks, packet impairment parameters, dependency versions, and pass/fail assertions so failures are reproducible.
- [ ] **G12-H093-02** Cover happy path, every documented failure branch, boundary values, timeout edges, cancellation, duplicate/late events, malformed inputs, and cleanup/resource-release behavior.
- [ ] **G12-H093-03** Run tests under IPv4, IPv6, dual-stack, NAT variants, CGNAT-like topologies, UDP-blocked/TCP-only paths, DNS impairment, route churn, and relay/direct combinations as applicable.
- [ ] **G12-H093-04** Add negative security cases for spoofing, replay, unauthorized relay use, malicious candidates/configuration, parser abuse, retry amplification, and resource exhaustion.
- [ ] **G12-H093-05** Produce machine-readable results containing build ID, configuration digest, dependency versions, topology description, test seed, timing data, failures, and retained artifacts.
- [ ] **G12-H093-06** Gate release on zero skipped mandatory tests; an absent dependency or unavailable environment must produce NOT-EVIDENCED/FAIL status rather than an implicit pass.
- [ ] **G12-H093-07** Implement and document the exact behavior required by this inventory item: **Firewall/UDP-blocked/captive-portal test scenarios **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-H093-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-H093-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-H093-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-H093-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-H093-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-H093-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-H093-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-H093-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-H093-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-H093-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-H093-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-H093-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-H093-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-H093`.

### 94. Fuzz tests — P0

**Component ID:** `G12-H094`  
**Objective:** Fuzz tests for config, control messages, candidate parsing, and untrusted adapter results.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-H094-01** Use structure-aware generators for configuration, candidates, protocol/control messages, adapter-return objects, and serialized state; preserve crashing/minimal corpora.
- [ ] **G12-H094-02** Run fuzz targets with memory/time/resource limits and sanitizers or equivalent runtime diagnostics where the implementation language permits.
- [ ] **G12-H094-03** Define deterministic test topology, fixtures, seeds, clocks, packet impairment parameters, dependency versions, and pass/fail assertions so failures are reproducible.
- [ ] **G12-H094-04** Cover happy path, every documented failure branch, boundary values, timeout edges, cancellation, duplicate/late events, malformed inputs, and cleanup/resource-release behavior.
- [ ] **G12-H094-05** Run tests under IPv4, IPv6, dual-stack, NAT variants, CGNAT-like topologies, UDP-blocked/TCP-only paths, DNS impairment, route churn, and relay/direct combinations as applicable.
- [ ] **G12-H094-06** Add negative security cases for spoofing, replay, unauthorized relay use, malicious candidates/configuration, parser abuse, retry amplification, and resource exhaustion.
- [ ] **G12-H094-07** Produce machine-readable results containing build ID, configuration digest, dependency versions, topology description, test seed, timing data, failures, and retained artifacts.
- [ ] **G12-H094-08** Gate release on zero skipped mandatory tests; an absent dependency or unavailable environment must produce NOT-EVIDENCED/FAIL status rather than an implicit pass.
- [ ] **G12-H094-09** Implement and document the exact behavior required by this inventory item: **Fuzz tests for config, control messages, candidate parsing, and untrusted adapter results**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-H094-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-H094-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-H094-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-H094-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-H094-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-H094-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-H094-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-H094-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-H094-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-H094-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-H094-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-H094-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-H094-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-H094`.

### 95. Concurrency/race tests — P0

**Component ID:** `G12-H095`  
**Objective:** Concurrency/race tests for simultaneous probes, timers, disconnects, and config reloads.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-H095-01** Define deterministic test topology, fixtures, seeds, clocks, packet impairment parameters, dependency versions, and pass/fail assertions so failures are reproducible.
- [ ] **G12-H095-02** Cover happy path, every documented failure branch, boundary values, timeout edges, cancellation, duplicate/late events, malformed inputs, and cleanup/resource-release behavior.
- [ ] **G12-H095-03** Run tests under IPv4, IPv6, dual-stack, NAT variants, CGNAT-like topologies, UDP-blocked/TCP-only paths, DNS impairment, route churn, and relay/direct combinations as applicable.
- [ ] **G12-H095-04** Add negative security cases for spoofing, replay, unauthorized relay use, malicious candidates/configuration, parser abuse, retry amplification, and resource exhaustion.
- [ ] **G12-H095-05** Produce machine-readable results containing build ID, configuration digest, dependency versions, topology description, test seed, timing data, failures, and retained artifacts.
- [ ] **G12-H095-06** Gate release on zero skipped mandatory tests; an absent dependency or unavailable environment must produce NOT-EVIDENCED/FAIL status rather than an implicit pass.
- [ ] **G12-H095-07** Implement and document the exact behavior required by this inventory item: **Concurrency/race tests for simultaneous probes, timers, disconnects, and config reloads**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-H095-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-H095-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-H095-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-H095-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-H095-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-H095-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-H095-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-H095-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-H095-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-H095-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-H095-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-H095-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-H095-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-H095`.

### 96. Security tests — P0

**Component ID:** `G12-H096`  
**Objective:** Security tests for replay, spoofing, forced relay, credential abuse, and resource exhaustion.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-H096-01** Define deterministic test topology, fixtures, seeds, clocks, packet impairment parameters, dependency versions, and pass/fail assertions so failures are reproducible.
- [ ] **G12-H096-02** Cover happy path, every documented failure branch, boundary values, timeout edges, cancellation, duplicate/late events, malformed inputs, and cleanup/resource-release behavior.
- [ ] **G12-H096-03** Run tests under IPv4, IPv6, dual-stack, NAT variants, CGNAT-like topologies, UDP-blocked/TCP-only paths, DNS impairment, route churn, and relay/direct combinations as applicable.
- [ ] **G12-H096-04** Add negative security cases for spoofing, replay, unauthorized relay use, malicious candidates/configuration, parser abuse, retry amplification, and resource exhaustion.
- [ ] **G12-H096-05** Produce machine-readable results containing build ID, configuration digest, dependency versions, topology description, test seed, timing data, failures, and retained artifacts.
- [ ] **G12-H096-06** Gate release on zero skipped mandatory tests; an absent dependency or unavailable environment must produce NOT-EVIDENCED/FAIL status rather than an implicit pass.
- [ ] **G12-H096-07** Implement and document the exact behavior required by this inventory item: **Security tests for replay, spoofing, forced relay, credential abuse, and resource exhaustion**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-H096-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-H096-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-H096-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-H096-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-H096-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-H096-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-H096-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-H096-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-H096-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-H096-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-H096-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-H096-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-H096-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-H096`.

### 97. Long-duration soak tests — P1

**Component ID:** `G12-H097`  
**Objective:** Long-duration soak tests for NAT mapping churn and memory/history stability.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-H097-01** Define deterministic test topology, fixtures, seeds, clocks, packet impairment parameters, dependency versions, and pass/fail assertions so failures are reproducible.
- [ ] **G12-H097-02** Cover happy path, every documented failure branch, boundary values, timeout edges, cancellation, duplicate/late events, malformed inputs, and cleanup/resource-release behavior.
- [ ] **G12-H097-03** Run tests under IPv4, IPv6, dual-stack, NAT variants, CGNAT-like topologies, UDP-blocked/TCP-only paths, DNS impairment, route churn, and relay/direct combinations as applicable.
- [ ] **G12-H097-04** Add negative security cases for spoofing, replay, unauthorized relay use, malicious candidates/configuration, parser abuse, retry amplification, and resource exhaustion.
- [ ] **G12-H097-05** Produce machine-readable results containing build ID, configuration digest, dependency versions, topology description, test seed, timing data, failures, and retained artifacts.
- [ ] **G12-H097-06** Gate release on zero skipped mandatory tests; an absent dependency or unavailable environment must produce NOT-EVIDENCED/FAIL status rather than an implicit pass.
- [ ] **G12-H097-07** Implement and document the exact behavior required by this inventory item: **Long-duration soak tests for NAT mapping churn and memory/history stability**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-H097-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-H097-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-H097-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-H097-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-H097-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-H097-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-H097-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-H097-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-H097-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-H097-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-H097-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-H097-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-H097-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-H097`.

### 98. Fleet-scale retry-storm test — P1

**Component ID:** `G12-H098`  
**Objective:** Fleet-scale retry-storm test proving jitter/circuit-breaking behavior.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-H098-01** Define deterministic test topology, fixtures, seeds, clocks, packet impairment parameters, dependency versions, and pass/fail assertions so failures are reproducible.
- [ ] **G12-H098-02** Cover happy path, every documented failure branch, boundary values, timeout edges, cancellation, duplicate/late events, malformed inputs, and cleanup/resource-release behavior.
- [ ] **G12-H098-03** Run tests under IPv4, IPv6, dual-stack, NAT variants, CGNAT-like topologies, UDP-blocked/TCP-only paths, DNS impairment, route churn, and relay/direct combinations as applicable.
- [ ] **G12-H098-04** Add negative security cases for spoofing, replay, unauthorized relay use, malicious candidates/configuration, parser abuse, retry amplification, and resource exhaustion.
- [ ] **G12-H098-05** Produce machine-readable results containing build ID, configuration digest, dependency versions, topology description, test seed, timing data, failures, and retained artifacts.
- [ ] **G12-H098-06** Gate release on zero skipped mandatory tests; an absent dependency or unavailable environment must produce NOT-EVIDENCED/FAIL status rather than an implicit pass.
- [ ] **G12-H098-07** Implement and document the exact behavior required by this inventory item: **Fleet-scale retry-storm test proving jitter/circuit-breaking behavior**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-H098-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-H098-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-H098-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-H098-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-H098-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-H098-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-H098-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-H098-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-H098-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-H098-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-H098-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-H098-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-H098-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-H098`.

### 99. Benchmarks — P1

**Component ID:** `G12-H099`  
**Objective:** Benchmarks for establishment latency, CPU, memory, packets/bytes, relay overhead, and power on edge hardware.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-H099-01** Define deterministic test topology, fixtures, seeds, clocks, packet impairment parameters, dependency versions, and pass/fail assertions so failures are reproducible.
- [ ] **G12-H099-02** Cover happy path, every documented failure branch, boundary values, timeout edges, cancellation, duplicate/late events, malformed inputs, and cleanup/resource-release behavior.
- [ ] **G12-H099-03** Run tests under IPv4, IPv6, dual-stack, NAT variants, CGNAT-like topologies, UDP-blocked/TCP-only paths, DNS impairment, route churn, and relay/direct combinations as applicable.
- [ ] **G12-H099-04** Add negative security cases for spoofing, replay, unauthorized relay use, malicious candidates/configuration, parser abuse, retry amplification, and resource exhaustion.
- [ ] **G12-H099-05** Produce machine-readable results containing build ID, configuration digest, dependency versions, topology description, test seed, timing data, failures, and retained artifacts.
- [ ] **G12-H099-06** Gate release on zero skipped mandatory tests; an absent dependency or unavailable environment must produce NOT-EVIDENCED/FAIL status rather than an implicit pass.
- [ ] **G12-H099-07** Implement and document the exact behavior required by this inventory item: **Benchmarks for establishment latency, CPU, memory, packets/bytes, relay overhead, and power on edge hardware**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-H099-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-H099-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-H099-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-H099-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-H099-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-H099-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-H099-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-H099-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-H099-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-H099-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-H099-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-H099-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-H099-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-H099`.

### 100. Machine-readable production acceptance evidence — P0

**Component ID:** `G12-H100`  
**Objective:** Machine-readable production acceptance evidence generated by the parent architecture gate with all dependencies present.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-H100-01** Define deterministic test topology, fixtures, seeds, clocks, packet impairment parameters, dependency versions, and pass/fail assertions so failures are reproducible.
- [ ] **G12-H100-02** Cover happy path, every documented failure branch, boundary values, timeout edges, cancellation, duplicate/late events, malformed inputs, and cleanup/resource-release behavior.
- [ ] **G12-H100-03** Run tests under IPv4, IPv6, dual-stack, NAT variants, CGNAT-like topologies, UDP-blocked/TCP-only paths, DNS impairment, route churn, and relay/direct combinations as applicable.
- [ ] **G12-H100-04** Add negative security cases for spoofing, replay, unauthorized relay use, malicious candidates/configuration, parser abuse, retry amplification, and resource exhaustion.
- [ ] **G12-H100-05** Produce machine-readable results containing build ID, configuration digest, dependency versions, topology description, test seed, timing data, failures, and retained artifacts.
- [ ] **G12-H100-06** Gate release on zero skipped mandatory tests; an absent dependency or unavailable environment must produce NOT-EVIDENCED/FAIL status rather than an implicit pass.
- [ ] **G12-H100-07** Implement and document the exact behavior required by this inventory item: **Machine-readable production acceptance evidence generated by the parent architecture gate with all dependencies present**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-H100-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-H100-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-H100-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-H100-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-H100-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-H100-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-H100-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-H100-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-H100-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-H100-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-H100-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-H100-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-H100-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-H100`.

## I. Packaging, deployment, and operations

### 101. Declared supported Python/runtime/platform matrix — P0

**Component ID:** `G12-I101`  
**Objective:** Declared supported Python/runtime/platform matrix .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-I101-01** Define the supported platform/runtime/dependency matrix and encode it in build metadata and CI jobs rather than maintaining it only in prose.
- [ ] **G12-I101-02** Make builds reproducible and attributable with locked dependencies, generated SBOM, provenance/attestation, artifact digest, version, source revision, and signing policy.
- [ ] **G12-I101-03** Implement staged deployment with canary health criteria, compatibility checks, automatic/manual rollback, and emergency disable controls for risky traversal mechanisms.
- [ ] **G12-I101-04** Create runbooks with preconditions, exact diagnostics, decision points, safe mitigations, rollback criteria, escalation contacts/roles, and evidence to retain after incidents.
- [ ] **G12-I101-05** Define vulnerability intake, severity, remediation SLA, dependency update cadence, release revocation, and end-of-life policy.
- [ ] **G12-I101-06** Require a formal production gate that aggregates mandatory test evidence, dependency health, security findings, waivers, runbook readiness, rollback proof, and artifact provenance.
- [ ] **G12-I101-07** Implement and document the exact behavior required by this inventory item: **Declared supported Python/runtime/platform matrix **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-I101-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-I101-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-I101-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-I101-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-I101-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-I101-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-I101-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-I101-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-I101-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-I101-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-I101-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-I101-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-I101-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-I101`.

### 102. Reproducible package metadata/build — P0

**Component ID:** `G12-I102`  
**Objective:** Reproducible package metadata/build (`pyproject.toml` or parent-repository equivalent).  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-I102-01** Define the supported platform/runtime/dependency matrix and encode it in build metadata and CI jobs rather than maintaining it only in prose.
- [ ] **G12-I102-02** Make builds reproducible and attributable with locked dependencies, generated SBOM, provenance/attestation, artifact digest, version, source revision, and signing policy.
- [ ] **G12-I102-03** Implement staged deployment with canary health criteria, compatibility checks, automatic/manual rollback, and emergency disable controls for risky traversal mechanisms.
- [ ] **G12-I102-04** Create runbooks with preconditions, exact diagnostics, decision points, safe mitigations, rollback criteria, escalation contacts/roles, and evidence to retain after incidents.
- [ ] **G12-I102-05** Define vulnerability intake, severity, remediation SLA, dependency update cadence, release revocation, and end-of-life policy.
- [ ] **G12-I102-06** Require a formal production gate that aggregates mandatory test evidence, dependency health, security findings, waivers, runbook readiness, rollback proof, and artifact provenance.
- [ ] **G12-I102-07** Implement and document the exact behavior required by this inventory item: **Reproducible package metadata/build (`pyproject.toml` or parent-repository equivalent)**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-I102-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-I102-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-I102-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-I102-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-I102-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-I102-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-I102-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-I102-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-I102-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-I102-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-I102-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-I102-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-I102-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-I102`.

### 103. Pinned external dependency versions — P0

**Component ID:** `G12-I103`  
**Objective:** Pinned external dependency versions for concrete network adapters.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-I103-01** Define the supported platform/runtime/dependency matrix and encode it in build metadata and CI jobs rather than maintaining it only in prose.
- [ ] **G12-I103-02** Make builds reproducible and attributable with locked dependencies, generated SBOM, provenance/attestation, artifact digest, version, source revision, and signing policy.
- [ ] **G12-I103-03** Implement staged deployment with canary health criteria, compatibility checks, automatic/manual rollback, and emergency disable controls for risky traversal mechanisms.
- [ ] **G12-I103-04** Create runbooks with preconditions, exact diagnostics, decision points, safe mitigations, rollback criteria, escalation contacts/roles, and evidence to retain after incidents.
- [ ] **G12-I103-05** Define vulnerability intake, severity, remediation SLA, dependency update cadence, release revocation, and end-of-life policy.
- [ ] **G12-I103-06** Require a formal production gate that aggregates mandatory test evidence, dependency health, security findings, waivers, runbook readiness, rollback proof, and artifact provenance.
- [ ] **G12-I103-07** Implement and document the exact behavior required by this inventory item: **Pinned external dependency versions for concrete network adapters**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-I103-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-I103-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-I103-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-I103-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-I103-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-I103-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-I103-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-I103-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-I103-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-I103-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-I103-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-I103-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-I103-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-I103`.

### 104. SBOM and provenance/signature generation — P0

**Component ID:** `G12-I104`  
**Objective:** SBOM and provenance/signature generation for release artifacts.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-I104-01** Generate an SBOM from the resolved build graph, include direct/transitive dependencies and licenses, and bind it to the exact release artifact digest.
- [ ] **G12-I104-02** Generate signed provenance/attestation identifying source revision, builder identity, build parameters, dependency lock, tests, and artifact digests.
- [ ] **G12-I104-03** Define the supported platform/runtime/dependency matrix and encode it in build metadata and CI jobs rather than maintaining it only in prose.
- [ ] **G12-I104-04** Make builds reproducible and attributable with locked dependencies, generated SBOM, provenance/attestation, artifact digest, version, source revision, and signing policy.
- [ ] **G12-I104-05** Implement staged deployment with canary health criteria, compatibility checks, automatic/manual rollback, and emergency disable controls for risky traversal mechanisms.
- [ ] **G12-I104-06** Create runbooks with preconditions, exact diagnostics, decision points, safe mitigations, rollback criteria, escalation contacts/roles, and evidence to retain after incidents.
- [ ] **G12-I104-07** Define vulnerability intake, severity, remediation SLA, dependency update cadence, release revocation, and end-of-life policy.
- [ ] **G12-I104-08** Require a formal production gate that aggregates mandatory test evidence, dependency health, security findings, waivers, runbook readiness, rollback proof, and artifact provenance.
- [ ] **G12-I104-09** Implement and document the exact behavior required by this inventory item: **SBOM and provenance/signature generation for release artifacts**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-I104-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-I104-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-I104-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-I104-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-I104-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-I104-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-I104-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-I104-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-I104-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-I104-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-I104-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-I104-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-I104-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-I104`.

### 105. CI pipeline — P0

**Component ID:** `G12-I105`  
**Objective:** CI pipeline running unit, integration, security, compatibility, and optimized-mode tests.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-I105-01** Separate fast unit/schema gates from privileged network-emulation/integration/security jobs while keeping all mandatory results linked to the same source revision and artifact digest.
- [ ] **G12-I105-02** Make skipped mandatory jobs fail the production evidence gate and retain logs/pcaps/test reports long enough for release audit and incident comparison.
- [ ] **G12-I105-03** Define the supported platform/runtime/dependency matrix and encode it in build metadata and CI jobs rather than maintaining it only in prose.
- [ ] **G12-I105-04** Make builds reproducible and attributable with locked dependencies, generated SBOM, provenance/attestation, artifact digest, version, source revision, and signing policy.
- [ ] **G12-I105-05** Implement staged deployment with canary health criteria, compatibility checks, automatic/manual rollback, and emergency disable controls for risky traversal mechanisms.
- [ ] **G12-I105-06** Create runbooks with preconditions, exact diagnostics, decision points, safe mitigations, rollback criteria, escalation contacts/roles, and evidence to retain after incidents.
- [ ] **G12-I105-07** Define vulnerability intake, severity, remediation SLA, dependency update cadence, release revocation, and end-of-life policy.
- [ ] **G12-I105-08** Require a formal production gate that aggregates mandatory test evidence, dependency health, security findings, waivers, runbook readiness, rollback proof, and artifact provenance.
- [ ] **G12-I105-09** Implement and document the exact behavior required by this inventory item: **CI pipeline running unit, integration, security, compatibility, and optimized-mode tests**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-I105-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-I105-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-I105-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-I105-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-I105-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-I105-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-I105-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-I105-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-I105-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-I105-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-I105-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-I105-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-I105-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-I105`.

### 106. Vulnerability scanning and patch SLA — P0

**Component ID:** `G12-I106`  
**Objective:** Vulnerability scanning and patch SLA .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-I106-01** Define the supported platform/runtime/dependency matrix and encode it in build metadata and CI jobs rather than maintaining it only in prose.
- [ ] **G12-I106-02** Make builds reproducible and attributable with locked dependencies, generated SBOM, provenance/attestation, artifact digest, version, source revision, and signing policy.
- [ ] **G12-I106-03** Implement staged deployment with canary health criteria, compatibility checks, automatic/manual rollback, and emergency disable controls for risky traversal mechanisms.
- [ ] **G12-I106-04** Create runbooks with preconditions, exact diagnostics, decision points, safe mitigations, rollback criteria, escalation contacts/roles, and evidence to retain after incidents.
- [ ] **G12-I106-05** Define vulnerability intake, severity, remediation SLA, dependency update cadence, release revocation, and end-of-life policy.
- [ ] **G12-I106-06** Require a formal production gate that aggregates mandatory test evidence, dependency health, security findings, waivers, runbook readiness, rollback proof, and artifact provenance.
- [ ] **G12-I106-07** Implement and document the exact behavior required by this inventory item: **Vulnerability scanning and patch SLA **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-I106-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-I106-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-I106-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-I106-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-I106-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-I106-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-I106-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-I106-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-I106-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-I106-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-I106-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-I106-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-I106-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-I106`.

### 107. Canary/staged rollout/rollback mechanism — P0

**Component ID:** `G12-I107`  
**Objective:** Canary/staged rollout/rollback mechanism .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-I107-01** Define the supported platform/runtime/dependency matrix and encode it in build metadata and CI jobs rather than maintaining it only in prose.
- [ ] **G12-I107-02** Make builds reproducible and attributable with locked dependencies, generated SBOM, provenance/attestation, artifact digest, version, source revision, and signing policy.
- [ ] **G12-I107-03** Implement staged deployment with canary health criteria, compatibility checks, automatic/manual rollback, and emergency disable controls for risky traversal mechanisms.
- [ ] **G12-I107-04** Create runbooks with preconditions, exact diagnostics, decision points, safe mitigations, rollback criteria, escalation contacts/roles, and evidence to retain after incidents.
- [ ] **G12-I107-05** Define vulnerability intake, severity, remediation SLA, dependency update cadence, release revocation, and end-of-life policy.
- [ ] **G12-I107-06** Require a formal production gate that aggregates mandatory test evidence, dependency health, security findings, waivers, runbook readiness, rollback proof, and artifact provenance.
- [ ] **G12-I107-07** Implement and document the exact behavior required by this inventory item: **Canary/staged rollout/rollback mechanism **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-I107-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-I107-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-I107-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-I107-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-I107-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-I107-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-I107-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-I107-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-I107-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-I107-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-I107-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-I107-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-I107-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-I107`.

### 108. Emergency-disable/kill switch — P0

**Component ID:** `G12-I108`  
**Objective:** Emergency-disable/kill switch for unsafe traversal methods.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-I108-01** Design the kill switch as authenticated, authorized, auditable, scoped, reversible, rapidly distributable control with safe default behavior if the control plane is unavailable.
- [ ] **G12-I108-02** Test disabling each risky traversal mechanism during active and new sessions, including rollback and stale-node behavior.
- [ ] **G12-I108-03** Define the supported platform/runtime/dependency matrix and encode it in build metadata and CI jobs rather than maintaining it only in prose.
- [ ] **G12-I108-04** Make builds reproducible and attributable with locked dependencies, generated SBOM, provenance/attestation, artifact digest, version, source revision, and signing policy.
- [ ] **G12-I108-05** Implement staged deployment with canary health criteria, compatibility checks, automatic/manual rollback, and emergency disable controls for risky traversal mechanisms.
- [ ] **G12-I108-06** Create runbooks with preconditions, exact diagnostics, decision points, safe mitigations, rollback criteria, escalation contacts/roles, and evidence to retain after incidents.
- [ ] **G12-I108-07** Define vulnerability intake, severity, remediation SLA, dependency update cadence, release revocation, and end-of-life policy.
- [ ] **G12-I108-08** Require a formal production gate that aggregates mandatory test evidence, dependency health, security findings, waivers, runbook readiness, rollback proof, and artifact provenance.
- [ ] **G12-I108-09** Implement and document the exact behavior required by this inventory item: **Emergency-disable/kill switch for unsafe traversal methods**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-I108-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-I108-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-I108-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-I108-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-I108-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-I108-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-I108-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-I108-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-I108-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-I108-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-I108-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-I108-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-I108-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-I108`.

### 109. Day-0 bootstrap runbook — P0

**Component ID:** `G12-I109`  
**Objective:** Day-0 bootstrap runbook including STUN/TURN/identity/config dependencies.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-I109-01** Implement RFC 8489-compatible Binding transactions, transaction-ID matching, XOR-MAPPED-ADDRESS parsing, MESSAGE-INTEGRITY/FINGERPRINT handling when configured, and retransmission timing appropriate to the selected transport.
- [ ] **G12-I109-02** Verify discovery against multiple independent STUN servers and distinguish server failure, DNS failure, blocked UDP, malformed response, and mapping inconsistency.
- [ ] **G12-I109-03** Implement Allocate, Refresh, CreatePermission, ChannelBind, Send/Data indications, channel-data framing, allocation expiry, and deterministic teardown; enforce authenticated access and realm/nonce handling.
- [ ] **G12-I109-04** Validate UDP/TCP/TLS TURN transports required by policy, permission/channel refresh timers, quota accounting, server failover, and credential rotation without orphaning allocations.
- [ ] **G12-I109-05** Define the supported platform/runtime/dependency matrix and encode it in build metadata and CI jobs rather than maintaining it only in prose.
- [ ] **G12-I109-06** Make builds reproducible and attributable with locked dependencies, generated SBOM, provenance/attestation, artifact digest, version, source revision, and signing policy.
- [ ] **G12-I109-07** Implement staged deployment with canary health criteria, compatibility checks, automatic/manual rollback, and emergency disable controls for risky traversal mechanisms.
- [ ] **G12-I109-08** Create runbooks with preconditions, exact diagnostics, decision points, safe mitigations, rollback criteria, escalation contacts/roles, and evidence to retain after incidents.
- [ ] **G12-I109-09** Define vulnerability intake, severity, remediation SLA, dependency update cadence, release revocation, and end-of-life policy.
- [ ] **G12-I109-10** Require a formal production gate that aggregates mandatory test evidence, dependency health, security findings, waivers, runbook readiness, rollback proof, and artifact provenance.
- [ ] **G12-I109-11** Implement and document the exact behavior required by this inventory item: **Day-0 bootstrap runbook including STUN/TURN/identity/config dependencies**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-I109-12** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-I109-13** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-I109-14** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-I109-15** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-I109-16** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-I109-17** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-I109-18** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-I109-19** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-I109-20** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-I109-21** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-I109-22** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-I109-23** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-I109-24** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-I109`.

### 110. Day-1 deployment runbook — P0

**Component ID:** `G12-I110`  
**Objective:** Day-1 deployment runbook including readiness and rollback criteria.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-I110-01** Define the supported platform/runtime/dependency matrix and encode it in build metadata and CI jobs rather than maintaining it only in prose.
- [ ] **G12-I110-02** Make builds reproducible and attributable with locked dependencies, generated SBOM, provenance/attestation, artifact digest, version, source revision, and signing policy.
- [ ] **G12-I110-03** Implement staged deployment with canary health criteria, compatibility checks, automatic/manual rollback, and emergency disable controls for risky traversal mechanisms.
- [ ] **G12-I110-04** Create runbooks with preconditions, exact diagnostics, decision points, safe mitigations, rollback criteria, escalation contacts/roles, and evidence to retain after incidents.
- [ ] **G12-I110-05** Define vulnerability intake, severity, remediation SLA, dependency update cadence, release revocation, and end-of-life policy.
- [ ] **G12-I110-06** Require a formal production gate that aggregates mandatory test evidence, dependency health, security findings, waivers, runbook readiness, rollback proof, and artifact provenance.
- [ ] **G12-I110-07** Implement and document the exact behavior required by this inventory item: **Day-1 deployment runbook including readiness and rollback criteria**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-I110-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-I110-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-I110-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-I110-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-I110-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-I110-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-I110-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-I110-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-I110-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-I110-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-I110-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-I110-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-I110-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-I110`.

### 111. Day-2 operations runbook — P0

**Component ID:** `G12-I111`  
**Objective:** Day-2 operations runbook including partitions, relay saturation, and cost incidents.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-I111-01** Define the supported platform/runtime/dependency matrix and encode it in build metadata and CI jobs rather than maintaining it only in prose.
- [ ] **G12-I111-02** Make builds reproducible and attributable with locked dependencies, generated SBOM, provenance/attestation, artifact digest, version, source revision, and signing policy.
- [ ] **G12-I111-03** Implement staged deployment with canary health criteria, compatibility checks, automatic/manual rollback, and emergency disable controls for risky traversal mechanisms.
- [ ] **G12-I111-04** Create runbooks with preconditions, exact diagnostics, decision points, safe mitigations, rollback criteria, escalation contacts/roles, and evidence to retain after incidents.
- [ ] **G12-I111-05** Define vulnerability intake, severity, remediation SLA, dependency update cadence, release revocation, and end-of-life policy.
- [ ] **G12-I111-06** Require a formal production gate that aggregates mandatory test evidence, dependency health, security findings, waivers, runbook readiness, rollback proof, and artifact provenance.
- [ ] **G12-I111-07** Implement and document the exact behavior required by this inventory item: **Day-2 operations runbook including partitions, relay saturation, and cost incidents**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-I111-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-I111-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-I111-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-I111-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-I111-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-I111-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-I111-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-I111-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-I111-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-I111-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-I111-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-I111-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-I111-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-I111`.

### 112. Incident severity/paging/escalation matrix — P0

**Component ID:** `G12-I112`  
**Objective:** Incident severity/paging/escalation matrix .  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-I112-01** Define the supported platform/runtime/dependency matrix and encode it in build metadata and CI jobs rather than maintaining it only in prose.
- [ ] **G12-I112-02** Make builds reproducible and attributable with locked dependencies, generated SBOM, provenance/attestation, artifact digest, version, source revision, and signing policy.
- [ ] **G12-I112-03** Implement staged deployment with canary health criteria, compatibility checks, automatic/manual rollback, and emergency disable controls for risky traversal mechanisms.
- [ ] **G12-I112-04** Create runbooks with preconditions, exact diagnostics, decision points, safe mitigations, rollback criteria, escalation contacts/roles, and evidence to retain after incidents.
- [ ] **G12-I112-05** Define vulnerability intake, severity, remediation SLA, dependency update cadence, release revocation, and end-of-life policy.
- [ ] **G12-I112-06** Require a formal production gate that aggregates mandatory test evidence, dependency health, security findings, waivers, runbook readiness, rollback proof, and artifact provenance.
- [ ] **G12-I112-07** Implement and document the exact behavior required by this inventory item: **Incident severity/paging/escalation matrix **; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-I112-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-I112-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-I112-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-I112-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-I112-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-I112-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-I112-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-I112-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-I112-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-I112-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-I112-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-I112-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-I112-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-I112`.

### 113. Backup/reconstruction guidance — P1

**Component ID:** `G12-I113`  
**Objective:** Backup/reconstruction guidance for any durable state introduced later.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-I113-01** Define the supported platform/runtime/dependency matrix and encode it in build metadata and CI jobs rather than maintaining it only in prose.
- [ ] **G12-I113-02** Make builds reproducible and attributable with locked dependencies, generated SBOM, provenance/attestation, artifact digest, version, source revision, and signing policy.
- [ ] **G12-I113-03** Implement staged deployment with canary health criteria, compatibility checks, automatic/manual rollback, and emergency disable controls for risky traversal mechanisms.
- [ ] **G12-I113-04** Create runbooks with preconditions, exact diagnostics, decision points, safe mitigations, rollback criteria, escalation contacts/roles, and evidence to retain after incidents.
- [ ] **G12-I113-05** Define vulnerability intake, severity, remediation SLA, dependency update cadence, release revocation, and end-of-life policy.
- [ ] **G12-I113-06** Require a formal production gate that aggregates mandatory test evidence, dependency health, security findings, waivers, runbook readiness, rollback proof, and artifact provenance.
- [ ] **G12-I113-07** Implement and document the exact behavior required by this inventory item: **Backup/reconstruction guidance for any durable state introduced later**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-I113-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-I113-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-I113-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-I113-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-I113-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-I113-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-I113-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-I113-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-I113-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-I113-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-I113-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-I113-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-I113-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-I113`.

### 114. Compatibility matrix and end-of-life policy — P0

**Component ID:** `G12-I114`  
**Objective:** Compatibility matrix and end-of-life policy for protocol/runtime/dependency versions.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-I114-01** Define the supported platform/runtime/dependency matrix and encode it in build metadata and CI jobs rather than maintaining it only in prose.
- [ ] **G12-I114-02** Make builds reproducible and attributable with locked dependencies, generated SBOM, provenance/attestation, artifact digest, version, source revision, and signing policy.
- [ ] **G12-I114-03** Implement staged deployment with canary health criteria, compatibility checks, automatic/manual rollback, and emergency disable controls for risky traversal mechanisms.
- [ ] **G12-I114-04** Create runbooks with preconditions, exact diagnostics, decision points, safe mitigations, rollback criteria, escalation contacts/roles, and evidence to retain after incidents.
- [ ] **G12-I114-05** Define vulnerability intake, severity, remediation SLA, dependency update cadence, release revocation, and end-of-life policy.
- [ ] **G12-I114-06** Require a formal production gate that aggregates mandatory test evidence, dependency health, security findings, waivers, runbook readiness, rollback proof, and artifact provenance.
- [ ] **G12-I114-07** Implement and document the exact behavior required by this inventory item: **Compatibility matrix and end-of-life policy for protocol/runtime/dependency versions**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-I114-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-I114-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-I114-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-I114-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-I114-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-I114-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-I114-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-I114-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-I114-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-I114-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-I114-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-I114-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-I114-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-I114`.

### 115. Exception/waiver/technical-debt register — P0

**Component ID:** `G12-I115`  
**Objective:** Exception/waiver/technical-debt register with owners and expiry dates.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-I115-01** Define the supported platform/runtime/dependency matrix and encode it in build metadata and CI jobs rather than maintaining it only in prose.
- [ ] **G12-I115-02** Make builds reproducible and attributable with locked dependencies, generated SBOM, provenance/attestation, artifact digest, version, source revision, and signing policy.
- [ ] **G12-I115-03** Implement staged deployment with canary health criteria, compatibility checks, automatic/manual rollback, and emergency disable controls for risky traversal mechanisms.
- [ ] **G12-I115-04** Create runbooks with preconditions, exact diagnostics, decision points, safe mitigations, rollback criteria, escalation contacts/roles, and evidence to retain after incidents.
- [ ] **G12-I115-05** Define vulnerability intake, severity, remediation SLA, dependency update cadence, release revocation, and end-of-life policy.
- [ ] **G12-I115-06** Require a formal production gate that aggregates mandatory test evidence, dependency health, security findings, waivers, runbook readiness, rollback proof, and artifact provenance.
- [ ] **G12-I115-07** Implement and document the exact behavior required by this inventory item: **Exception/waiver/technical-debt register with owners and expiry dates**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-I115-08** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-I115-09** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-I115-10** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-I115-11** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-I115-12** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-I115-13** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-I115-14** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-I115-15** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-I115-16** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-I115-17** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-I115-18** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-I115-19** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-I115-20** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-I115`.

### 116. Formal production exit gate — P0

**Component ID:** `G12-I116`  
**Objective:** Formal production exit gate that treats absent dependencies or skipped tests as non-evidence.  
**Required evidence:** architecture/design record; implementation reference; automated test report; security/reliability review where applicable; telemetry sample; operator/runbook entry; machine-readable gate result.

- [ ] **G12-I116-01** Represent every mandatory dependency/test/control as PASS/FAIL/NOT-EVIDENCED with source artifact links and timestamps; prohibit converting SKIP/UNKNOWN into PASS.
- [ ] **G12-I116-02** Require signed/approved waivers with owner, scope, rationale, compensating control, expiration, and automatic gate failure after expiry.
- [ ] **G12-I116-03** Define the supported platform/runtime/dependency matrix and encode it in build metadata and CI jobs rather than maintaining it only in prose.
- [ ] **G12-I116-04** Make builds reproducible and attributable with locked dependencies, generated SBOM, provenance/attestation, artifact digest, version, source revision, and signing policy.
- [ ] **G12-I116-05** Implement staged deployment with canary health criteria, compatibility checks, automatic/manual rollback, and emergency disable controls for risky traversal mechanisms.
- [ ] **G12-I116-06** Create runbooks with preconditions, exact diagnostics, decision points, safe mitigations, rollback criteria, escalation contacts/roles, and evidence to retain after incidents.
- [ ] **G12-I116-07** Define vulnerability intake, severity, remediation SLA, dependency update cadence, release revocation, and end-of-life policy.
- [ ] **G12-I116-08** Require a formal production gate that aggregates mandatory test evidence, dependency health, security findings, waivers, runbook readiness, rollback proof, and artifact provenance.
- [ ] **G12-I116-09** Implement and document the exact behavior required by this inventory item: **Formal production exit gate that treats absent dependencies or skipped tests as non-evidence**; identify unsupported sub-cases explicitly rather than silently falling back or reporting success.
- [ ] **G12-I116-10** Assign a named engineering owner, security reviewer, operational owner, and escalation path; record the component lifecycle state (design / implementation / validation / production / deprecated).
- [ ] **G12-I116-11** Write a normative requirement statement describing what constitutes success, failure, degraded operation, unsupported operation, and policy rejection for this component.
- [ ] **G12-I116-12** Define public/internal interfaces, input/output schemas, error taxonomy, reason codes, resource ownership, and backward-compatibility guarantees; version externally consumed contracts.
- [ ] **G12-I116-13** Enumerate dependencies and trust boundaries; specify behavior for dependency timeout, unavailability, malformed response, stale data, partial success, and recovery.
- [ ] **G12-I116-14** Define configurable parameters with units, legal ranges, defaults, environment overrides, reload semantics, and security classification; reject unsafe/ambiguous values before activation.
- [ ] **G12-I116-15** Instrument lifecycle, success/failure, latency/duration, resource use, retry/cancellation, and degraded-mode signals with stable structured telemetry and bounded cardinality.
- [ ] **G12-I116-16** Add deterministic unit tests for nominal behavior, every state transition, boundary values, invalid inputs, timeout/cancellation, cleanup, and previously observed regressions.
- [ ] **G12-I116-17** Add integration tests using real or standards-compatible dependencies and preserve version/topology/configuration information with the test evidence.
- [ ] **G12-I116-18** Add fault-injection tests for packet loss/delay, dependency failure, stale data, concurrency, restart, configuration change, and resource pressure where applicable.
- [ ] **G12-I116-19** Measure CPU, memory, descriptor/socket/task counts, network overhead, establishment/processing latency, and steady-state cost under representative and worst-supported load; define regression budgets.
- [ ] **G12-I116-20** Document operator diagnostics, safe remediation, rollback/disable procedure, known limitations, and signals that require escalation rather than automatic retry.
- [ ] **G12-I116-21** Produce machine-readable acceptance evidence tied to source revision, artifact digest, configuration generation, test results, security findings, and approved waivers; mandatory evidence may not be satisfied by skipped tests.
- [ ] **G12-I116-22** **Component exit gate:** all mandatory sub-checks above are PASS or have an approved, unexpired waiver; no unresolved P0 defect, security-critical finding, unbounded resource behavior, or missing production evidence remains for `G12-I116`.

## Recommended implementation sequence

1. **Traversal foundation:** P0 STUN, TURN, ICE/equivalent, UDP punching, TCP fallback, IPv6/dual-stack, and hard attempt deadlines/cancellation.
2. **Trust foundation:** GAP-06 identity/attestation, end-to-end authenticated encryption, key/credential lifecycle, replay protection, relay authorization, rate limits, circuit breakers, egress policy, and secrets integration.
3. **Network-awareness foundation:** interface/route inventory, multi-WAN policy, DNS resilience, PMTU handling, flap control, and firewall/captive diagnostics.
4. **State/control foundation:** concurrency ownership, atomic transitions, restart/recovery policy, dependency health, degraded-mode behavior, quarantine, and configuration versioning/atomic reload.
5. **Observability foundation:** metrics, structured logs, tracing, readiness, reason codes, dashboards, alerting, privacy, and release/topology correlation.
6. **Certification foundation:** NAT matrix, network impairment lab, partition/reconnect scenarios, DNS/IP-family/firewall matrices, fuzz/concurrency/security tests, soak/storm tests, benchmarks, and machine-readable acceptance evidence.
7. **Production operations:** supported-runtime matrix, reproducible packaging, dependency pinning, SBOM/provenance/signing, CI/security scanning, staged rollout/rollback, kill switch, runbooks, incident model, compatibility/EOL, waivers, and formal exit gate.

## Completion summary fields

- [ ] P0 completion count recorded: `____ / ____`
- [ ] P1 completion count recorded: `____ / ____`
- [ ] P2 completion count recorded: `____ / ____`
- [ ] Open defects linked and severity-classified.
- [ ] Open waivers linked with owner and expiry.
- [ ] Latest full certification build/artifact digest recorded.
- [ ] Production gate decision and approvers recorded.
