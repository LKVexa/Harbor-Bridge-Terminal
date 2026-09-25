# INV-58 - Existing service-mesh layer

**Version:** 4.3.0 (see `CHANGELOG.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` is referenced by the source inventory but is not present in this archive; this is tracked explicitly in `POST_AUDIT_MISSING_COMPONENTS.md` (MC-001, BLOCKED).
**Release state:** engineering gate PASS; production **NO_GO** until the human/external blockers in `release/ACCEPTANCE_RECORD.json` are closed.

The existing service-mesh layer is already doing mTLS, retries and routing for current workloads, and the new runtime has to coexist with it rather than duplicate it. The sharpest hazard is retry multiplication: three app retries through a mesh that also retries three times is nine attempts against a struggling service. This element owns the division of labour.

## Responsibility

Own coexistence with the incumbent mesh: which layer retries, total-attempt budgets, identity handoff from mesh certificates to runtime identities, and detection of traffic bypassing the mesh.

## Owns

- Retry ownership between app runtime and mesh
- Total-attempt budgets
- Mesh-to-runtime identity mapping
- Mesh-bypass detection
- Migration of policies off the mesh

## Explicitly does not own

- The mesh's data plane
- Certificate issuance
- Application retry code
- Routing policy content
- Network hardware

## Non-goals

- Running the mesh
- Issuing certificates
- Writing app retry code

## Interfaces

- `bypass` - PK_MESH_BYPASS/1 - a flow observed outside the mesh
- `identity` - PK_MESH_IDENTITY/1 - certificate SAN to runtime identity
- `reconcile` - PK_MESH_RECONCILE/1 - effective retry ownership per route

## Service-level objectives

- **bounded attempts** - no call exceeds its total-attempt budget (error budget: no budget)
- **no bypass** - every bypass flow flagged within one scrape (error budget: no budget)
- **handoff cost** - p99 identity mapping under 100us (error budget: 1% may exceed)

## Running it

```
python -B -m unittest discover -s inv58_existing_service_mesh_layer/tests       # full dependency-free suite
python -B -O inv58_existing_service_mesh_layer/tools/run_tests.py               # same under -O, JSON result
python -B inv58_existing_service_mesh_layer/tools/bootstrap.py --dev-keys       # empty-environment preflight
python -B inv58_existing_service_mesh_layer/tools/rtm.py --check                # traceability matrix (100 rows)
python -B inv58_existing_service_mesh_layer/tools/gen_fixtures.py --check       # golden fixtures drift check
python -B inv58_existing_service_mesh_layer/tools/bench.py run && python -B inv58_existing_service_mesh_layer/tools/bench.py gate
python -B inv58_existing_service_mesh_layer/tools/release_gate.py               # exit 0 GO / 3 NO_GO / 1 engineering fail
```

Framework conformance (needs the external, still-unpinned `pk_core`):

```
python -m pk_core run INV-58 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-58 --out conformance/PK_GATE_RESULTS.json
```

## Layout (v4.3.0)

| Path | Role |
|---|---|
| `mesh_logic.py` | pure retry reconciliation, strict SPIFFE mapping, bypass detector, COW route registry (4.2.0 invariants preserved) |
| `service.py` | `MeshLayerService` — the single boundary: authN → authZ → lifecycle/freeze/quarantine → admission → execute → journal/audit/metrics |
| `authz.py` | boundary matrix, SPIFFE + signed-token authentication, deny-by-default capability policy, break-glass |
| `config.py` | `PK_MESH_CONFIG/1`: secure defaults, overlays, validation, provenance, atomic activation, auto/operator rollback |
| `secret_refs.py` | `secretref://` references, explicit providers, redaction |
| `audit.py` | hash-chained, HMAC-sealed, bounded audit trail with optional append-only JSONL sink |
| `resilience.py` | retry safety + jittered backoff executor, circuit breaker, admission control, lifecycle FSM, fencing, freeze/quarantine |
| `telemetry.py` | metric catalogue with cardinality bounds, structured logs with pseudonymisation, W3C trace context |
| `integrity.py` | artifact manifest signature/digest/provenance/approved-version verification |
| `errors.py` | `PK_MESH_ERROR/1` envelope and stable codes |
| `schemas/` | 10 Draft 2020-12 schemas (3 data-plane + error, config, status, decision, audit, snapshot, artifact) |
| `fixtures/` | golden conformance fixtures |
| `docs/` | requirements, ADR-001 (PROPOSED), interfaces, threat model, failure taxonomy, performance, SLO, runbooks, incident, security policy, backup/restore, telemetry, reviews, residual risks |
| `governance/` | RTM, rtm_map, ownership (roles, no people), threat model JSON, waivers/debt/deprecations, BOM, compatibility matrix, checklist execution |
| `ops/` | dashboards and alerts |
| `tools/` | rtm, gen_fixtures, bench, bootstrap, run_tests, release_gate, checklist_status |
| `release/ACCEPTANCE_RECORD.json` | last gate run: digests, evidence, verdict, blockers |

The previous v4.2.0 audit remains in `AUDIT_REPORT.md` (with a v4.3.0 section appended) and `POST_AUDIT_MISSING_COMPONENTS.md`; `MISSING_COMPONENTS.json` keeps every original finding and adds a `closure_4_3_0` record to each.

## Day-0 / day-1 / day-2

See `docs/RUNBOOKS.md` (bootstrap, canary stages and promotion criteria, rollback, two-person emergency disable, day-2 checks). Rollback of configuration is `rollback_config`; restoring state is `restore` from a sealed snapshot; emergency disable is `arm_break_glass` by one operator then `break_glass` by another.
