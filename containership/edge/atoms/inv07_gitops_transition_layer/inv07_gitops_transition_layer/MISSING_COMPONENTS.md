# INV-07 Missing Components Inventory

> **5.0.0 note.** This inventory is the v4.2.0 baseline and is kept as written. Each item is now component NN of
> the 54-component checklist; its implementation, tests and per-check status (VERIFYING / IN_PROGRESS / BLOCKED --
> never PASS without a named owner and independent reviewer) are in `components/STATUS.md` and
> `components/evidence/CHECKLIST_STATUS.json`. Per the closure criteria below, no item is removed until it is
> independently verified.

**Version assessed:** 4.2.0  
**Scope:** the standalone `inv07_gitops_transition_layer` archive only.  
**Interpretation:** an item is listed when the archive does not contain a production implementation or independently verifiable artifact for the capability. An external parent repository may provide some of these items through `pk_core` or sibling components.

## P0 — production blockers

1. **Real Git transport and repository adapter** — no clone/fetch/pull/ref-resolution implementation, credential flow, shallow/full fetch policy, remote pinning, or repository availability handling.
2. **Approved-branch/ref policy enforcement** — the model stores an append-only local list but does not bind reconciliation to a configured remote repository and approved branch/ref.
3. **Asymmetric commit/tag signature verification** — the reference model uses HMAC-SHA256 for dependency-free tests; production-grade SSH/GPG/Sigstore verification, trust roots, revocation, expiry, and signer identity mapping are absent.
4. **Artifact provenance integration** — the contract names GAP-07, but there is no concrete verifier adapter, provenance statement parser, certificate-chain validator, Rekor/transparency integration, or policy binding.
5. **Argo CD/Flux/controller adapter** — no production reconciliation driver exists for Kubernetes, Argo CD, Flux, Helm, Kustomize, or another target control plane.
6. **Live-state reader and applier** — the `live` dictionary is an in-memory stand-in; no Kubernetes API, IaC backend, device control plane, or infrastructure API adapter is present.
7. **Atomic apply/transaction strategy** — no server-side apply transaction, staged apply, preflight/dry-run, partial-failure rollback, resource ordering, or dependency-aware reconciliation.
8. **Persistent controller state** — commits, applied history, drift reports, leases, cursors, and recovery state are memory-only and are lost on restart.
9. **Leader election / duplicate-controller protection** — no lease, fencing token, epoch, compare-and-swap ownership, or split-brain prevention is implemented.
10. **Authentication and authorization boundary** — no operator/service authentication, RBAC/ABAC/capability checks, tenant authorization, or least-privilege service account profile is implemented.
11. **Secret/key management integration** — signing verification keys are passed directly as process memory bytes; there is no KMS/HSM/secret-store integration, rotation workflow, revocation, or zeroization strategy.
12. **Tamper-evident audit ledger** — reports are mutable in-memory dictionaries; there is no append-only signed/hash-chained audit log, durable storage, retention policy, or export.
13. **Versioned interface schemas** — `PK_GITOPS_SYNC/1`, `PK_GITOPS_DRIFT/1`, and `PK_GITOPS_VERIFY/1` are named but no JSON Schema, Protobuf, OpenAPI, WIT, or equivalent typed schema files are bundled.
14. **Machine-readable error model** — Python exceptions exist, but stable external error codes, retryability classification, structured details, and compatibility guarantees are absent.
15. **Production bootstrap/deployment packaging** — no Helm chart, Kubernetes manifests, systemd/container package, OCI image definition, SBOM, image signing policy, or deterministic installation path is included.

## P1 — reliability, security, and operations gaps

16. **Retry/backoff/jitter policy** — no bounded retry controller, idempotency key, replay protection, cancellation, deadline, or backpressure semantics.
17. **Dependency circuit breaking / admission control** — no overload guard, queue bound, circuit breaker, rate limiter, tenant quota, or load shedding.
18. **Offline/disconnected operation policy** — branch-unavailable behavior is named in the contract but no cached-ref age limit, stale-state policy, reconnect reconciliation, or operator mode exists.
19. **Crash recovery and replay** — no journal/WAL, checkpoint, resume cursor, at-least/at-most-once definition, or crash-consistency tests.
20. **Quarantine/freeze/emergency disable** — no runtime reconciliation pause, unsafe-target quarantine, scoped freeze, kill switch, or audited override workflow.
21. **Multi-tenant hard isolation** — boundaries are documented, but there are no separate credentials, namespaces, storage partitions, network policies, or tenant-scoped controller instances enforced by code.
22. **Residency/site policy enforcement** — site/environment boundaries are descriptive only; no locality constraints, region allowlists, or cross-site failover policy is implemented.
23. **Policy engine integration** — no OPA/CEL/Rego/admission-policy evaluation, policy bundle versioning, exception/waiver model, or deny reason capture.
24. **Manifest/input parser hardening** — no YAML/JSON/Kustomize/Helm parser, schema validation, size/depth limits, duplicate-key detection, alias/anchor controls, or hostile-input fuzz corpus.
25. **Supply-chain dependency controls** — no pinned runtime dependencies, lockfile, SBOM, vulnerability scan policy, license scan, provenance verification, or reproducible-build metadata.
26. **Network security profile** — no mTLS, certificate rotation, DNS pinning policy, egress allowlist, proxy behavior, TLS minimums, or remote endpoint verification implementation.
27. **Replay/freshness protection** — the model validates state signatures but has no signed commit-time, nonce, ref freshness, protected-branch generation, or anti-replay policy for production attestations.
28. **Time service behavior** — no trusted-time dependency, clock-skew bounds, expiry validation behavior, or degraded mode when time is unavailable.
29. **Configuration system** — no typed configuration file/environment schema, secure defaults, validation command, configuration provenance, hot-reload semantics, or immutable/mutable separation.
30. **Compatibility matrix** — no explicit supported Git server, Argo CD, Flux, Kubernetes, Python, OS/architecture, schema-version, or adjacent-component matrix.
31. **Migration plan from traditional IaC** — INV-06 is named as upstream, but there is no coexistence phase, dual-run detector, authority cutover, rollback boundary, or ownership-transfer workflow.
32. **Backup/restore/reconstruction procedure** — no durable data format or tested restoration path for controller metadata and audit evidence.
33. **Incident runbook** — no severity model, paging criteria, containment steps, compromised-key response, rollback decision tree, or forensic evidence preservation procedure.
34. **Patch/EOL/vulnerability SLA** — no maintenance window, CVE response objectives, supported-version lifetime, deprecation process, or emergency patch path.

## P2 — observability, testing, and performance gaps

35. **Metrics endpoint** — no counters/histograms/gauges for sync rate, verification failures, reconcile latency, backlog, drift, saturation, dependency health, or resource use.
36. **Structured operational logging** — no stable event schema with tenant/site/workload/operation identifiers, severity, reason code, correlation ID, or redaction policy.
37. **Distributed tracing** — no trace-context propagation across Git, verifier, policy, and target-control-plane operations.
38. **Operator explain view** — no API/UI that links reconciliation decisions to commit, signer, policy, live-state delta, target resources, and constraints.
39. **Dashboards and alerts** — no shipped dashboards, SLO burn alerts, drift alerts, unsigned-ref alerts, stalled-controller alerts, or dependency-failure alerts.
40. **Telemetry retention/privacy policy** — no sampling, retention, PII/secret redaction, high-cardinality controls, or export destination contract.
41. **Integration tests against real Git and target control planes** — the archive contains only a reference-model test and a `pk_core` conformance harness that skips when `pk_core` is absent.
42. **Contract tests for all public interfaces** — no executable fixtures for `PK_GITOPS_SYNC/1`, `/DRIFT/1`, or `/VERIFY/1`.
43. **Security/adversarial test suite** — no injection, signature confusion, key compromise/revocation, replay, privilege escalation, parser bomb, resource exhaustion, or cross-tenant tests.
44. **Fuzz testing** — no fuzz harness/corpus for repository metadata, manifests, signatures, schemas, or API payloads.
45. **Fault-injection/chaos tests** — no network partition, Git outage, API timeout, process crash, stale leader, KMS outage, clock skew, or partial-apply recovery tests.
46. **Scale/soak/burst benchmarks** — no baseline for repositories, objects, tenants, reconcile fan-out, CPU, memory, storage, network, startup, p50/p95/p99, or worst case.
47. **Release regression gates** — no machine-enforced performance/security threshold comparison against a baseline.
48. **Cross-platform/runtime certification** — no declared/verified CPU architecture, OS, Python runtime, container runtime, Kubernetes version, or provider coverage.
49. **Coverage/reporting artifacts** — no coverage threshold, mutation testing, static type-checking gate, linter configuration, or test evidence bundle.
50. **Full checklist evidence bundle** — `CHECKLIST.json` contains 100 requirements, but the archive does not include the claimed `MASTER.md`, requirement-to-evidence traceability matrix, gate results, or evidence ledger needed to independently verify all 100 claims.

## Packaging/documentation gaps

51. **`MASTER.md`** — referenced by the original README but absent from the uploaded archive. The 4.2.0 README now records this honestly instead of implying it is bundled.
52. **Standalone packaging metadata** — no `pyproject.toml`, wheel metadata, dependency declaration, or package installation test. This may be intentional if INV-07 is always shipped inside a parent monorepo.
53. **License/NOTICE files** — not present in this archive; add them if the parent distribution does not supply licensing centrally.
54. **Generated API/reference documentation** — no schema/API docs, examples, or operator command reference beyond README snippets.

## Closure criteria

A missing item should be removed from this inventory only when the archive contains (or the parent release explicitly binds to) a production implementation, a versioned contract, automated verification, and machine-readable evidence sufficient to reproduce the claim.
