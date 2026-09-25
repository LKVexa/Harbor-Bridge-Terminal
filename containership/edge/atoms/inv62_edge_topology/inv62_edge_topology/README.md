# INV-62 - Edge topology

**Version:** 4.3.0 (see `CHANGELOG.md`) · **Group:** 01_Source_Inventory ·
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0 ·
**Checklist:** 100 requirements in `CHECKLIST.json`, 94 missing components tracked in `conformance/mc_status.json`

Edge topology models the estate from cloud through regions and sites to devices, tracks live-link latency and
health, resolves the nearest reachable capable node under security/residency/availability policy, detects site
partitions against a designated cloud node, and grants fenced site-local coordinator leases when disconnected.

## Production status

**Not production-ready. Exit gate: NO_GO** (`evidence/exit_gate.json`). The engineering is in place and
tested. What still blocks the gate:

* owners and approvers are unbound;
* the ADR, thresholds and 8 waivers are unapproved;
* there is no licence;
* the release key is ephemeral;
* `pk_core` and a wasmCloud runtime are unavailable.

See `AUDIT_REPORT.md`.

## Layout

| Path | Content |
|---|---|
| `topology.py` | validated graph engine (stdlib, no `pk_core`) |
| `production/` | service boundary, auth, policy, election, health, config, persistence, audit, telemetry, resilience, client, adapters, bootstrap |
| `schemas/` | generated JSON Schemas and the error registry |
| `fixtures/` | reference conformance corpus |
| `docs/` | architecture, ADR, spec, NFR, semantics, interfaces, security, threat model, failure catalog, performance, observability, runbooks, governance |
| `conformance/` | requirements, generated RTM, MC status |
| `tools/` | `ci.py`, `bench.py`, `rtm.py`, `export_schemas.py`, `gen_fixtures.py`, `release.py`, `exit_gate.py` |
| `examples/` | config, overlays, seed topology used by the bootstrap runbook |
| `contract.py`, `component.py` | `pk_core` contract and conformance adapter (external) |

## Interfaces

`PK_TOPO_GRAPH/1`, `PK_TOPO_NEAREST/1` and `PK_TOPO_PARTITION/1` are the three wire protocols. Each has a
typed schema, and every call is authenticated and authorised. See `docs/INTERFACES.md`.

## Testing

From the folder containing `inv62_edge_topology`:

```text
python inv62_edge_topology/tools/ci.py                 # all lanes -> evidence/ci_report.json
python inv62_edge_topology/tests/run_suite.py          # all unit suites (skips fail the run)
python -O inv62_edge_topology/tests/run_suite.py       # optimised mode
python inv62_edge_topology/tools/bench.py --quick --gate
```

The conformance adapter additionally requires the external `pk_core` package; without it
`tests/test_component.py` exits 2, and the CI `pk-core` lane reports NOT_RUN, so the overall result is
INCOMPLETE rather than PASS.

## Day-0 / day-1 / day-2

See `docs/RUNBOOKS.md`. The bootstrap command there is executed by `tests/test_bootstrap.py`.
