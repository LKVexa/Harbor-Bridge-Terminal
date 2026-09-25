# INV-63 Boundaries

| Field | Value |
|---|---|
| Document ID | INV63-ARCH-BOUNDARIES |
| INV-63 C-IDs covered | C002, C003, C006, C021 |
| Status | DRAFT — pending approval |
| Owner | Service owner (role) — UNASSIGNED |
| Reviewers | Architecture reviewer (role), Security reviewer (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change. The machine-readable source is `docs/interfaces/BOUNDARIES.json`; `tests/test_contracts.py::SchemaTest::test_boundary_inventory_matches_code` checks it against code. |

## 1. Scope (C002)
Owns (`contract.py::build`): desired-state storage, reconciliation diff, spread across host labels, idempotent convergence, rolling updates bounded by max-unavailable.
Does not own: manifest format, running components, artifact signing, host provisioning, provider implementations.

## 2. Boundary inventory (C021) — view of `BOUNDARIES.json`

| ID | Name | Kind / dir | Contract | AuthN | AuthZ | Timeout | Limits | Owner (role) |
|---|---|---|---|---|---|---|---|---|
| B-01 | Deployment API | API / in | `PK_DEPLOY_REQUEST/1` | HMAC bearer (`TokenAuthority`): iss/aud/exp/nbf/jti | capability per op (`OP_CAPABILITY`), tenant-scoped | `request_timeout_ms` (5000 default, max 300000); `deadline_ms` only shortens | 64 KiB, depth 8, `max_inflight`, per-tenant bucket 50/s burst 100 | service-owner |
| B-02 | Desired state (v1) | body / in | `PK_DEPLOY_DESIRED/1` | via B-01 | `desired:write` | via B-01 | count<=1000, ids<=256 | service-owner; deprecated 2027-09-30, rejected when signing required |
| B-03 | Desired state (v2, signed) | body / in | `PK_DEPLOY_DESIRED/2` | B-01 + Ed25519 | `desired:write` | via B-01 | count<=1000, residency<=16 | service-owner |
| B-04 | Reconciliation plan | internal | `PK_DEPLOY_DIFF/1` | in-process | `reconcile:run` | caller deadline | <=2000 start/stop | service-owner |
| B-05 | Rollout request | body / in | `PK_DEPLOY_ROLLOUT/1` | B-01 + signature | `rollout:run` | via B-01 | `max_unavailable` 1..1000 | service-owner |
| B-06 | Structured error | response / out | `PK_DEPLOY_ERROR/1` | n/a | n/a | n/a | message<=512 | service-owner |
| B-07 | Audit/decision event | event / out | `PK_DEPLOY_EVENT/1` | exporter mTLS (deployment) | `audit:read` | async | reason<=1024 | sre |
| B-08 | Configuration | file / in | `PK_DEPLOY_CONFIG/1` | file ownership + activation author | `config:activate` | n/a | schema-bounded | config-admin |
| B-09 | Exit gate verdict | file / out | `PK_DEPLOY_GATE/1` | Ed25519 | release approver | n/a | n/a | release-approver |
| B-10 | Lattice adapter (INV-60/Wadm) | control-plane / out | OAM `core.oam.dev/v1beta1` over injected transport | NATS nkey/JWT via `secret_refs.lattice_creds` | lattice account scoped to manager | per-call deadline, retry, breaker | one call per action | service-owner |
| B-11 | State journal | file / internal | journal record (`store.py`) | FS ACL (0700 state dir) | epoch fencing | fsync | 256 MiB before compaction | service-owner |
| B-12 | Status/health | API / out | `INV63_STATUS/1` | deployment ingress | `explain:read` | n/a | n/a | sre |
| B-13 | Metrics | API / out | Prometheus text 0.0.4 | deployment ingress | scrape identity | n/a | <=2000 series/metric | sre |
| B-14 | Upstream INV-64 | API / in | `PK_DEPLOY_DESIRED/2` | node/peer principal | `desired:write` | via B-01 | via B-01 | INV-64 owner |
| B-15 | Enterprise control plane INV-66 | control-plane / in | `PK_DEPLOY_REQUEST/1` | controller principal | reconciler / sre-operator roles | via B-01 | via B-01 | INV-66 owner |

Not exposed: WIT, non-JSON RPC, device, hypervisor interfaces. Operations on B-01: `set_desired, reconcile, rollout, freeze, unfreeze, quarantine, release_quarantine, explain, rollback`.

Notes / gaps: B-07 exporter, B-12/B-13 HTTP ingress and B-12/B-13 ingress are deployment responsibilities — the package does not create an HTTP server or exporter. B-11 mode 0700 is set by `tools/bootstrap.py` (`os.chmod(sd, 0o700)`), not by `Journal`. `status()` is a Python method; no capability check is applied to it in code.

## 3. Trust boundaries

| TB | Between | Enforcement |
|---|---|---|
| TB-1 | Untrusted caller → service | `schema.parse_bytes` (size/depth/dup keys), `TokenAuthority.verify`, `Authorizer.check` |
| TB-2 | Tenant A ↔ tenant B | `security.namespace` (`tenant/component`), Authorizer tenant scoping (`INV63-E-TENANT-ISOLATION`), per-tenant quotas and token buckets |
| TB-3 | Artifact supply chain → desired state | `ArtifactVerifier.verify` (digest, trusted key id, Ed25519, approved version, revocation) |
| TB-4 | Service → lattice (Wadm/NATS) | injected transport; credentials by secret ref; lattice is **trusted to report truthfully** (A-17) |
| TB-5 | Service → disk | hash-chained journal, optional AES-256-GCM `Sealer`, epoch fencing |
| TB-6 | Operator → service | `emergency_disable(on, principal)` / `quarantine_host(host, on, principal)` require a `Principal` with tenant `"*"` and `control:freeze` / `control:quarantine` (`service._operator`, else `INV63-E-FORBIDDEN`). The principal object is trusted as passed (in-process call; no token verification) |

## 4. Tenant / environment / site / workload boundaries (C006)

| Boundary | Contract statement | Implementation |
|---|---|---|
| Tenant | state and traffic partitioned, never shared | `namespace()`, `Authorizer`, `tenant_quotas`, `Admission` per-tenant buckets; platform principals (`tenant="*"`) may not `desired:write`/`rollout:run` |
| Environment | limits/endpoints differ per env | `deploy/config/env/{dev,staging,prod}.json`; prod forces `SECURITY_CRITICAL` settings (`config.validate`) |
| Site | own instance per site; no global singleton | `deploy/config/site/*.json`; one `state_dir`/`epoch` per instance |
| Workload | budgets/quotas per workload | per-(tenant, component) lifecycle, `count<=1000`, controls on `tenant/component` or `tenant/*` |

## 5. Dependencies (C003)

| Direction | Element | Role | Interface |
|---|---|---|---|
| upstream | INV-64 Application model | supplies validated manifests | B-14 |
| downstream | INV-60 Wasm application fabric | starts/stops what INV-63 decides | B-10 |
| downstream | INV-66 Enterprise Wasm control plane | manages many managers | B-15 |
| peer | GAP-08 OTA lifecycle/rollback | rollback for failed rollouts | none in code (INV-63 has its own `_rollback`) — integration open |
| runtime | `cryptography` 46.0.7 | Ed25519, AES-GCM | `security.py` |
| runtime | Wadm (UNPINNED) | actuator | `adapter.WadmAdapter` (full `LatticeAdapter` over injected transport) |

Interoperation with live INV-60/INV-64/INV-66 has not been tested (evidence key `wadm-live` open).
