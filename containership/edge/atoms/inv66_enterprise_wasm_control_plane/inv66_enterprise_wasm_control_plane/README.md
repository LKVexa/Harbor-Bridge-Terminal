# INV-66 - Enterprise Wasm control plane

**Version:** 4.3.0 (see `CHANGELOG.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`, rendered in `MASTER.md` (derived, informative. The upstream series archive is not bundled.)
**Production status:** **NOT production-certified.** The exit gate is `NO_GO` (`release/exit_gate.json`); `docs/COVERAGE.md` has the reasons.

The enterprise Wasm control plane sits above many lattices and many teams. It adds three things a
single lattice lacks: who may deploy where, which registries and signers are acceptable, and a record of
every change. Guardrails are enforced at admission, so a manifest that pulls from an unapproved registry
never reaches a deployment manager.

## What 4.3.0 adds

4.2.0 was an in-memory decision engine that trusted a caller-supplied user string and a manifest
`signer` string. 4.3.0 adds a production layer under `production/`:

| Concern | Module | Notes |
|---|---|---|
| Authentication | `identity.py` | EdDSA JWT from trusted issuers (iss/aud/kid/exp/nbf/lifetime/jti, replay cache) or mTLS SPIFFE peers |
| Authorisation | `rbac.py` | org → tenant → lattice scopes, capabilities, groups, workload principals, deny-overrides, delegation without escalation |
| Provenance | `provenance.py` | digest pinning, Ed25519 signatures bound to digest+name, signer scope/revocation/expiry, attestations |
| Policy | `policy_engine.py` | local rules with fixed precedence, plus GAP-13 (OPA API) that is version-pinned and fails closed |
| Source of truth | `journal.py` | fsync'd, hash-chained, Ed25519-anchored journal; crash recovery; compaction with legal holds; export |
| Configuration | `config.py` | one digested `PK_ECP_CONFIG/1` generation: stage → N approvals → CAS activate → rollback |
| Resilience | `resilience.py`, `quota.py` | deadlines, retry + jitter, breaker, load shedding, per-tenant quotas, idempotency |
| HA | `replication.py` | single-writer lease with fencing epochs over shared storage |
| Delivery | `adapters.py` | INV-63 `PK_ECP_DELIVER/1` (idempotent on decision id), GitOps ingestion |
| Operations | `quarantine.py`, `siem.py`, `telemetry.py`, `http_api.py`, `server.py`, `cli.py` | freeze/quarantine, SIEM export, metrics/logs/traces, HTTPS API, backup/restore/anchor CLI |

`control_plane.py` (the 4.2.0 engine) is kept only as the `pk_core` behavioural fixture (`docs/TECH_DEBT.md` DEP-01).

## Owns / does not own

Owns: organisation and lattice RBAC · manifest admission guardrails · approved registries and signers · change audit trail · cross-lattice inventory.
Does not own: lattice runtime · reconciliation · signing keys · identity provider · billing.

## Interfaces

`PK_ECP_ADMIT/1`, `PK_ECP_RBAC/1`, `PK_ECP_AUDIT/1` (query) + `/2` (records), `PK_ECP_CONFIG/1`,
`PK_ECP_HEALTH/1`, `PK_ECP_INVENTORY/1`, `PK_ECP_ERROR/1`, `PK_ECP_DELIVER/1`. See `docs/INTERFACES.md` and `schemas/`.

## Service-level objectives

- **guardrails:** zero unadmitted manifests forwarded (no error budget)
- **audit integrity:** the audit chain verifies end to end (no error budget)
- **admission latency:** p99 under 50 ms (1 % may exceed). Measured values are in `docs/CAPACITY.md`.

## Running it

```
pip install -c constraints.txt cryptography            # runtime dependency
python tools/ci.py                                      # every lane; writes release/ci_report.json
python tools/bench.py --soak-seconds 60                 # benchmark -> release/bench.json
python tools/release.py build && python tools/release.py gate
python -m inv66_enterprise_wasm_control_plane.production.cli demo --seconds 30   # local HTTP demo
```

`tools/ci.py` runs from any directory. The test suites run from this folder with
`python -m unittest discover -s tests -t .`. `pk_core` conformance (`tests/test_component.py`) still
needs `pk_core` (set `PK_CORE_PATH`). Without it the `pk-core-gate` lane reports **NOT_RUN**, which is never PASS.

## Day-0 / day-1 / day-2

See `docs/runbooks/` (RB-DAY0, RB-DAY1, RB-DAY2, RB-BACKUP, RB-INCIDENT).

## Governance

Owners are UNASSIGNED (`governance/owners.json`). No license is selected (`LICENSE-STATUS.md`). Waivers
are in `release/waivers.json`. The checklist execution ledger is `release/mc_status.json`, and
`governance/…CHECKLIST.executed.md` is the annotated checklist.
