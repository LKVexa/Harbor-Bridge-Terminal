# INV-58 Normative Requirements (v4.3.0)

Keywords SHALL / SHALL NOT / SHOULD follow RFC 2119. Every requirement has a stable id
`INV58-<class>-<nnn>`; ids are never reused. `governance/RTM.json` links each checklist
item (INV-58-C001..C100) to these requirements, implementation symbols, tests and evidence.

## Functional

Source function: *Network routing/security* — coexistence with the incumbent mesh (INV-58-C011).

| Id | Requirement | Acceptance |
|---|---|---|
| INV58-FR-001 | For each route, INV-58 SHALL assign retries to at most one layer (app or mesh) and SHALL NOT return a policy where both layers retry. | `mesh_logic.reconcile`; fuzz invariant `app>1 ∧ mesh>1` never holds |
| INV58-FR-002 | Effective attempts (app × mesh) SHALL NOT exceed the route budget; the budget SHALL NOT exceed the configured `max_budget` (≤10). | `E_BUDGET_EXCEEDED` above max; soak invariant |
| INV58-FR-003 | A mesh certificate SAN SHALL map to a runtime identity only if it is a strict SPIFFE ID in the configured trust domain; otherwise mapping SHALL fail with `E_IDENTITY_UNMAPPABLE`. No normalisation is performed. | fuzz bijection test |
| INV58-FR-004 | A mapped identity SHALL belong to the tenant named in the request (`ns/<tenant>/…`), else `E_TENANT_SCOPE`. | cross-tenant identity test |
| INV58-FR-005 | Plaintext (non-mTLS) flows to a meshed destination SHALL be flagged, retained in bounded per-tenant evidence, counted and audited. | bypass tests |
| INV58-FR-006 | Route policy migration SHALL be route-by-route, revisioned, copy-on-write, idempotent by key, and fenced by a monotonic controller token. | mutation-safety tests |
| INV58-FR-007 | Every public operation SHALL pass the boundary pipeline: validate → authenticate → authorize → lifecycle/freeze/quarantine → admission → execute → journal/audit/metrics. | `service.MeshLayerService._guard` |

## Deployment contexts

| Context | Applicability | Differences |
|---|---|---|
| Cloud | Full | Default limits. |
| Datacenter | Full | Same; site overlay sets `meshed_destinations`. |
| Near-edge | Full | Lower `limits.max_inflight`, `admission.rate_per_s` via site overlay. |
| Far-edge | Conditional | Only if an incumbent mesh runs there. Key/identity service loss is expected: security operations fail closed; the data plane keeps last-known-good policy (see Connectivity). |

## Non-functional

| Id | Class | Requirement |
|---|---|---|
| INV58-NFR-001 | Latency | p99 identity mapping < 100 µs (contract SLO "handoff cost"); boundary-service p99 ceilings in `tools/bench.py::GATE`. |
| INV58-NFR-002 | Availability | Readiness is false while any fail-closed dependency is down; liveness is false when stalled or failed. |
| INV58-NFR-003 | Durability | Route policy, fencing and controls are reconstructable from a sealed snapshot; audit is durable when a JSONL sink is configured. |
| INV58-NFR-004 | Consistency | Config activation is a single atomic swap; restore is all-or-nothing; revisions are monotonic. |
| INV58-NFR-005 | Isolation | State, journals, evidence, quotas and metrics labels are tenant-keyed; cross-tenant access is refused before state access. |
| INV58-NFR-006 | Determinism | `reconcile` and `map_identity` are pure functions of their inputs; behaviour is identical under `python -O`. |

## Outcome model

| Outcome | Meaning | Surface |
|---|---|---|
| success | Operation completed, result returned. | response object |
| partial success | Not produced by any INV-58 operation: every mutation is all-or-nothing (atomic config swap, atomic restore). | — |
| degraded | Completed while a non-critical dependency is down; lifecycle `degraded`; route mutation refused. | `status.health.state` |
| retryable failure | `retryable: true` codes: `E_CONFLICT`, `E_CAPACITY`, `E_OVERLOADED`, `E_CIRCUIT_OPEN`, `E_DEADLINE_EXCEEDED`, `E_DEPENDENCY_UNAVAILABLE`, `E_NOT_READY`. | `PK_MESH_ERROR/1` |
| terminal failure | Everything else; the caller must change the request. | `PK_MESH_ERROR/1` |

## Lifecycle

States: `created → bootstrapping → ready ⇄ degraded`, `ready|degraded → frozen → ready`,
`→ draining → stopped`, `→ failed → bootstrapping`. The legal transition table is
`resilience.LEGAL_TRANSITIONS`; the operation classes each state accepts are
`resilience.STATE_ACCEPTS`. Illegal transitions raise `E_NOT_READY` and every transition is audited.

## Versioning

- Semantic versioning for the component. Interfaces are versioned by name (`PK_MESH_*/<n>`); a breaking change creates `/<n+1>` and both are served for one minor release.
- Unknown requested versions fail with `E_UNSUPPORTED_VERSION` listing the supported set; omitted versions resolve to the newest supported.
- Error codes, audit event types, metric names and decision codes are append-only.
- 4.3.0 tightens SPIFFE path validation (DEP-01) — the only intentionally stricter behaviour.

## Capacity

Every collection has a ceiling (`config.SECURE_DEFAULTS.limits`): routes (global and per tenant), bypass evidence, meshed destinations, in-flight requests, label cardinality, audit/journal/log rings, idempotency cache, quarantine table, replay-nonce cache. Fairness: one tenant may hold at most `admission.tenant_share` of in-flight capacity; excess is shed with `E_OVERLOADED`.

## Connectivity

| Lost dependency | Behaviour |
|---|---|
| Identity / policy / key / time / attestation service | fail closed: authentication-dependent operations return `E_DEPENDENCY_UNAVAILABLE`; readiness false. Mesh-identity (SPIFFE) data-plane calls continue while only the *key* service is lost because they do not need it. |
| Audit sink | fail closed for audited operations (mutations, denials, control actions). |
| Telemetry | fail-safe degraded: data plane continues, route mutation paused. |
| Full partition | The incumbent mesh keeps enforcing the last policy it received; INV-58 never pushes a default-open policy. |

## Precedence

When requirements conflict, the higher rule wins:
1. Security and isolation (fail closed, tenant scope, no secret disclosure).
2. Residency/data-boundary constraints.
3. Correctness invariants (single retry owner, attempt budget).
4. SLOs (latency/availability).
5. Cost and convenience.

Validation enforces rule 1 structurally: a configuration that makes a security dependency anything but `fail_closed` is rejected, whatever the SLO or cost rationale.

## Failover

INV-58 is per-site (no global singleton). Failover is a controller moving to another instance: the new controller SHALL present a higher fencing token; the stale one is refused (`E_STALE_FENCE`). State moves only through sealed snapshots restored into declared tenants, never across a residency boundary: restore skips undeclared tenants.

## Configuration

Immutable artifact = this package. Mutable configuration = `PK_MESH_CONFIG/1` composed as defaults ← base ← environment ← site overlays; mutable state = route registries, fencing, controls, evidence, audit.
