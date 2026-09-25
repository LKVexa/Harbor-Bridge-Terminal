# ADR-0001 — INV-04 production runtime architecture

- **Status:** Proposed (v4.3.0). Needs approval from the roles in `docs/OWNERS.md`; none are assigned yet.
- **Date:** 2026-09-22
- **Supersedes:** nothing. **Related:** ADR-0002, `docs/THREAT_MODEL.md`, `COMPONENT_STATUS.json`.

## Context

INV-04 v4.2.0 was a dependency-free behavioural model (`model.py`) of the incumbent orchestrator. `MISSING_COMPONENTS.md` listed 80 capabilities it would need to become a production-grade compatibility layer. Many of them depend on external systems: a Kubernetes API server, an identity provider, a service mesh, a signing identity, and a real-cluster CI matrix. None of those are available inside the package.

## Decision

1. **Hexagonal split.** Safety logic lives in pure, typed, stdlib-only modules under `runtime/` (policy, scheduling, drain coordinator, journal, config, security, observability). External systems are reached only through narrow ports (`runtime/api.py::ClusterAPI`). Each port ships with an in-memory reference implementation (`InMemoryClusterAPI`) that follows the documented Kubernetes semantics: UID and resourceVersion preconditions, the policy/v1 Eviction subresource with PDB checks (429), and controller refill.
2. **Keep the runtime stdlib-only.** It has no third-party dependencies, so the supply-chain surface is CPython alone. The production Kubernetes adapter will be a separate distribution that pins the official client and implements `ClusterAPI`. It is out of scope for this package and is tracked as component #1 (OPEN_EXTERNAL).
3. **Kubernetes compatibility target:** server minors 1.28–1.33 (`runtime/api.py::SUPPORTED_SERVER_MINORS`). The API must serve policy/v1 PDBs and Eviction. `check_discovery` refuses to start when a required GVR is missing.
4. **Write-ahead journal as the durability primitive.** It is hash-chained JSONL with fsync before each side effect. It records drain phases, idempotency results, config activations, and audit events. Recovery replays it. The first successful eviction is the point of no return: before it, failures roll back the cordon; after it, the node stays cordoned and the drain is recorded as `failed_cordoned`.
5. **Parity over kubectl semantics for budget preflight.** A drain is refused up front when the healthy pods *off* the node are already fewer than `desiredHealthy`. This is the v4.2 `min_available` rule, and `tests/test_properties.py::ParityHarnessTest` enforces it. The rule is stricter than `kubectl drain`, which evicts one pod, waits for its replacement, and then continues. Relaxing it is a behaviour change and needs its own ADR.
6. **Leadership.** A lease with a monotonically increasing fencing token. Mutations carry the token, and the API port rejects stale tokens. Production must enforce the token on the server-side write path. Examples: an admission webhook, or a precondition on a coordination object.
7. **Transport.** HTTP/JSON (`runtime/service.py`) carrying the PK_ORCH_*/1 schemas. Revision negotiation goes through `X-PK-Accept-Revision`, and errors use `application/problem+json` with the PK_ORCH_ERROR/1 envelope. TLS and mTLS (component #29) terminate in the deployment's mesh or sidecar. The process binds to loopback by default.
8. **Authentication.** HS256 bearer tokens with iss/aud/exp/nbf/TTL checks are the in-package reference. Production must plug in OIDC/JWKS or Kubernetes TokenReview behind the same `Principal` type.

## Consequences

- Every safety invariant has deterministic tests that run under `python -O`, with no cluster needed.
- Production readiness still depends on the external adapters. `COMPONENT_STATUS.json` records exactly which components are `OPEN_EXTERNAL`.
- The in-memory API server can drift from real API-server behaviour. The mitigation is component #58 (kind/k3s matrix), which is blocked on the adapter.

## Invalidation conditions

Revisit this ADR if any of these happen: a supported Kubernetes minor drops policy/v1 semantics used here, the estate mandates gRPC/WIT transport, the successor scheduler (SCH-01) changes the hand-off contract, or the owner decides the runtime may take third-party dependencies.
