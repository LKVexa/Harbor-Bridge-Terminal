# GAP-13 Policy Engine — Missing Components Inventory

**Baseline:** v4.2.0 after audit/hardening  
**Status (5.0.0):** every item below has been built into this package and is tracked in `COMPONENT_STATUS.json`. None is DONE, because independent acceptance is required. 47 are VERIFYING and 4 are BLOCKED: MC-033 edge hardware, MC-038 real adjacent builds, MC-041 named owners, MC-042 ADR approval. This list is kept as the 4.2.0 gap inventory for provenance.  
**Interpretation:** items below are absent or materially incomplete in the uploaded package itself. Some may intentionally live in adjacent GAP/PLN subsystems, but GAP-13 still needs explicit adapters, contracts, tests, or evidence for production certification.

## Priority 0 — security and correctness dependencies

1. **Cryptographic policy-bundle verification adapter** — an actual GAP-07 integration that validates signature, digest, signer identity, provenance, approved key/version and revocation state before `verified=True` can be trusted. Current API accepts an already-attested verification mapping. Related: C044-C045.
2. **Typed `PK_POLICY_BUNDLE/1` schema and parser** — canonical serialization, schema validation, schema-version negotiation, maximum sizes, duplicate-field handling and malformed-input rejection. C021-C022, C026, C028, C085.
3. **Typed `PK_POLICY_VERDICT/1` schema artifact** — JSON Schema/Protobuf/WIT/OpenAPI definition with compatibility rules and golden fixtures. C021-C022, C027, C029, C082.
4. **Typed `PK_POLICY_EXPLANATION/1` schema artifact** — external contract for the newly implemented explanation API, including redaction rules. C021-C022, C075, C077, C082.
5. **Trusted attribute/context provider** — canonical source for tenant, workload, site, environment, identity, attestation, residency and classification attributes so callers cannot self-assert privileged policy inputs. C006, C023-C024, C041, C044, C046.
6. **Request attribute allowlist/type system** — per-attribute type validation, namespaces, normalization, unknown-attribute policy and injection resistance. C011-C019, C041, C050.
7. **Stale-policy enforcement mode** — configurable fail-closed/freeze behavior once the cached bundle exceeds the permitted staleness window; current engine reports staleness but still evaluates normally. C018, C048, C056-C059.
8. **Replay/downgrade protection for bundles** — monotonic bundle generation/epoch, anti-rollback policy, issuer sequence validation and replay detection. C016, C045, C048, C050, C058.
9. **Secure administrative authorization boundary** — explicit capability required to load/replace bundles and access sensitive explanations/diagnostics. C023-C024, C042-C044.
10. **Tamper-evident security audit log** — append-only/chained records for bundle activation, rejection, rollback, administrative actions and security-sensitive verdicts. C036, C049, C090.

## Priority 1 — production service and integration layer

11. **Policy distribution client/controller** — fetch/watch mechanism for new bundles, authenticated transport, backoff, jitter, cancellation, idempotency and controlled activation. C003, C018, C025, C037, C053.
12. **Persistent bundle cache** — durable last-known-good bundle, metadata, checksum, load time and restart reconstruction for disconnected operation. C018, C032, C057, C095.
13. **Rollback manager** — previous-known-good retention, operator rollback, automatic rollback after failed activation and rollback audit evidence. C038, C092, C095.
14. **Atomic concurrent policy swap mechanism** — explicit synchronization/read-copy-update strategy and race tests for multi-threaded or multi-worker deployments. C037, C058, C086.
15. **Service/RPC transport** — versioned local/remote API for load/evaluate/explain with authentication, authorization, deadlines, cancellation and backpressure. C021-C028.
16. **Structured error model** — stable error codes and machine-readable details for invalid bundle, verification failure, scope escalation, stale-policy refusal, schema mismatch and dependency outage. C026.
17. **Compatibility/version matrix** — supported bundle schemas, verdict/explanation schemas, Python/runtime versions and adjacent GAP/PLN interfaces. C016, C027, C084, C093.
18. **Environment/site configuration model** — declarative configuration for staleness limits, maximum rule count, resource limits, dependency endpoints and safe defaults. C033-C036.
19. **Configuration provenance record** — author, source, version, signature/digest, activation time and previous configuration linkage. C036.
20. **Explicit emergency disable/freeze/quarantine control** — operator mechanism to freeze updates, disable evaluation service, force deny-only mode or isolate a bad policy version. C059, C092.

## Priority 2 — observability and operations

21. **Health/readiness/status endpoint** — current version, bundle age, dependency state, verification state, active capability set and readiness reason. C052, C071.
22. **Metrics subsystem** — verdict rate, default-deny rate, rule hits, tie-breaks, errors, latency distributions, saturation, bundle age and resource consumption. C061-C064, C069, C072.
23. **Structured logging subsystem** — stable component/operation/node/site/tenant/workload identifiers with privacy-safe fields. C073, C075.
24. **Distributed tracing hooks** — trace-context propagation across policy distribution and evaluate/explain boundaries. C074.
25. **Telemetry redaction/privacy policy** — sensitive/high-cardinality field classification, retention, sampling, export and tenant-data protections. C075, C079.
26. **Release-lineage/infrastructure-graph correlation** — bind verdicts and policy versions to application release provenance and live topology. C078.
27. **Dashboards and alert rules** — distinguish normal load, default denials, policy rejection, stale policy, dependency failure, attack indicators and software faults. C080.
28. **Incident runbooks and severity model** — paging, escalation, containment, rollback, freeze, recovery and post-incident evidence. C096-C097.

## Priority 3 — performance, resilience and certification

29. **Compiled/indexed matcher** — trie/index/DAG or equivalent for large rule sets; current evaluation scans every rule (`O(n)`) per request. C061-C070.
30. **Capacity and hard-limit controls** — maximum rules, attributes, request size, explanation size, concurrency and memory bounds. C017, C028, C067, C069.
31. **Admission control/load shedding** — bounded concurrency/queues and overload behavior if exposed as a service. C054, C067.
32. **Performance benchmark suite** — reproducible p50/p95/p99/worst-case latency, throughput, startup, memory and CPU baselines under steady/burst/overload. C061-C064, C070, C088.
33. **Edge power/thermal benchmark** — constrained-node impact measurement where GAP-13 runs at far edge. C068.
34. **Fault-injection suite** — dependency outage, corrupt cache, partial write, network partition, stale controller, clock anomaly and restart tests. C051-C060, C089.
35. **Fuzz/property-based tests** — malformed schemas, adversarial match values, Unicode keys/names, giant payloads, parser edge cases and deterministic-order properties. C050, C085.
36. **Concurrency/race test suite** — simultaneous evaluations and bundle swaps across threads/processes. C086.
37. **Security test suite from threat model** — privilege escalation, attribute injection, spoofing, replay, downgrade, resource exhaustion and cross-tenant isolation tests. C041, C050, C087.
38. **Integration tests with adjacent components** — GAP-07 signing/provenance, GAP-04 disconnected operation, PLN-01 intent, PLN-06 data and PLN-07 security. C030, C083, C089.
39. **Machine-readable certification evidence** — reproducible evidence bundle proving each applicable checklist item rather than contract-only declarations. C020, C090, C100.
40. **Release regression gate** — fail CI/release when security, correctness, latency, throughput, compatibility or evidence thresholds regress. C070, C090, C100.

## Priority 4 — architecture and governance artifacts

41. **Named accountable owner and escalation path** — absent from the uploaded package. C009.
42. **Approved ADR** — architecture decision record for evaluator model, conflict semantics, distribution, caching, trust boundary and deployment form. C010.
43. **SHALL-level requirements specification** — testable functional/non-functional semantics beyond the generic checklist. C011-C019.
44. **Requirements traceability matrix** — requirement -> design -> code -> test -> evidence mapping. C020.
45. **Deployment-pattern support matrix** — cloud/datacenter/near-edge/far-edge supported and unsupported patterns. C012, C008.
46. **Production SLO/error-budget specification** — current contract contains conceptual SLOs but lacks measurable latency/availability/support commitments. C013, C091.
47. **Day-0/day-1/day-2 executable runbooks** — README provides a sketch, but not complete operational procedures with prerequisites, validation, failure paths and recovery. C040, C096.
48. **Vulnerability/patch/EOL policy** — response SLAs, supported branches, dependency patch cadence and EOL rules. C094.
49. **Exception/waiver/technical-debt registry** — owners, rationale, compensating controls and expiry dates. C099.
50. **Formal production-exit gate artifact** — signed/recorded gate combining architecture, security, performance, resilience, integration, rollback and ownership evidence. C100.
51. **`MASTER.md` audit source** — README previously claimed this 100-item master prompt/workflow document was bundled, but it is absent from the uploaded archive.

## Components intentionally outside GAP-13 but requiring explicit integration contracts

- Policy authoring UI/language and approval workflow.
- Enforcement point implementation at callers/data plane.
- Identity and attestation subsystem.
- Artifact signing/key custody subsystem.
- General infrastructure topology system.

These can remain separate systems, but GAP-13 still needs authenticated, versioned, tested adapters to them before production certification.
