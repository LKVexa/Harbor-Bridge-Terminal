# INV-28 architecture (MC-090)

## Data flow

```
 workload owner ──PK_TOOLCHAIN_SELECTION_REQUEST/1──►  Selector.select(request, now)
                                                         │   ▲ policy (PK_TOOLCHAIN_POLICY/1, versioned, digest)
 register operator ──Registry.register/update/...──►  Registry ──signed snapshot──► FileStore (rev-NNNNNN.json)
                                                         │   ▲ GAP-15 certificates (PK_RUNTIME_CERT/1, key purpose gap15)
                                                         │   ▲ advisory feed (PK_ADVISORY_FEED/1, key purpose advisory)
                                                         │   ▲ rollout state (RolloutController ⇄ GAP-08 port)
                                                         ▼
                       SelectionResult + PK_TOOLCHAIN_TICKET/1   |  RefusalError(PK_TOOLCHAIN_REFUSAL/1)
                                                         │
                                  AuditLedger (hash chain) · Metrics · StructuredLogger · TraceContext
                                                         ▼
                               INV-27 ── Inv27Adapter.verify(ticket, artifact bytes) ── build/boot
```

## Modules

| Module | Responsibility | MC |
|---|---|---|
| `model.py` | `ToolchainRecord` (PK_TOOLCHAIN/2) and its parts. Validation, canonical form, digest | 009-021, 096 |
| `policy.py` | Versioned `SelectionPolicy`, `EnvironmentRule` with a production floor, `Waiver` | 022, 038, 094 |
| `registry.py` | Lifecycle, authz, CAS, signed and chained snapshots, `FileStore`, rollback, emergency disable | 027-030, 067, 069, 070 |
| `selection.py` | Request/result/refusal types, evaluation of every constraint, ranking, bounds, deadline, cache | 012, 019, 023-026, 078-080, 099, 100 |
| `certification.py` | GAP-15 certificate ingestion and exact-match lookup | 042, 097 |
| `advisories.py` | Signed advisory feed, staleness, open-advisory query | 037 |
| `binding.py` | Selection ticket plus the INV-27 verification | 041, 098 |
| `rollout.py` | Canary/staged rollout, auto-halt, rollback, GAP-08 announcements | 043, 068 |
| `observability.py` | Metrics, logs, traces, audit ledger, telemetry policy | 058-062, 065 |
| `service.py` / `explain.py` | Health, readiness, status, explain, lineage, review scheduling | 056, 057, 063, 064, 074 |
| `trust.py` | Per-purpose HMAC key ring | 030, 036 |
| `schema_check.py` + `schemas/` | Machine-readable interface schemas and their checker | 004, 005, 040 |
| `component.py` | pk_core conformance component (exercised findings) and the deprecated v1 API | 002, 055 |
| `fixtures.py` | Deterministic synthetic world for tests, examples and benchmarks | 092 |
| `cli.py` | Operator CLI: validate, select, explain, status | 063 |

## Trust boundaries
See `docs/THREAT_MODEL.md`. In short: request validation happens at the boundary. Every external document is authenticated by a key *purpose*. Registry writes are authorised per capability and serialised by CAS. INV-27 trusts only a verified ticket plus the bytes it holds.

## Lifecycle
`candidate → active ⇄ deprecated → eol → retired → (removed)`. The side states `quarantined` and `disabled` can be entered from `active` or `deprecated`. `disabled` requires the `emergency` capability. Only `active` is selectable in production. `deprecated` is selectable where policy allows it.

## Determinism
The decision id is the digest of the request, registry digest, policy digest, certificate snapshot, advisory snapshot, rollout state and `now`. Ranking order is maturity, then certified, then name, then newest version.

## Dependencies
Runtime uses the Python standard library only. pk_core is used only by `component.py`, `contract.py` and `tools/pk_gate.py` (vendored, provenance pinned).
