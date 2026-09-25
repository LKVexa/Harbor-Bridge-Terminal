# GAP-04 — Disconnected-operation controller

**Version:** 4.3.0 · **Group:** 04_Gap_Subsystems · **Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Master source:** [MASTER.md](MASTER.md) · **Checklist status:** [GAP04_v4.3.0_Checklist_Status.md](GAP04_v4.3.0_Checklist_Status.md) · **Residual gaps:** [MISSING_COMPONENTS.md](MISSING_COMPONENTS.md)

GAP-04 provides bounded site autonomy while the control plane is unavailable. Version 4.3.0 turns the 4.2.0 reference state machine into a durable, cryptographically governed runtime that implements the P0 controls of the 56-component missing-components checklist, with P1 operational tooling and P2 governance artifacts.

> **Production status: NO_GO.** The formal exit gate (`runtime/gate.py`) refuses GO: owners/approvers are unassigned, adjacent layers were exercised only through reference adapters, there is no release CI, and no independent security review has taken place. See `docs/WAIVERS.md`.

## Layout
| Path | What |
|---|---|
| `controller.py` | Dependency-free tier/lease state machine (4.2.0 core + configurable tier schedule, lease capabilities, tier caps, snapshots) |
| `runtime/node.py` | `DisconnectedNode` — the production composition |
| `runtime/trust.py`, `canonical.py`, `crypto.py` | Signed leases/policies/trust bundles, canonical JSON, pinned crypto profile |
| `runtime/clock.py` | Trusted time with persisted anti-rollback high-water mark |
| `runtime/journal.py`, `storage.py` | Crash-consistent WAL, hash-chained + HMAC'd + AES-GCM frames, atomic files, keyring |
| `runtime/fencing.py` | Ownership lock and generation fencing |
| `runtime/adapters.py` | GAP-12 / GAP-13 / PLN-07 / GAP-01 / GAP-05 contracts + reference implementations |
| `runtime/authz.py`, `opsapi.py` | mTLS SPIFFE identity, deny-by-default authorization, health/metrics endpoint |
| `runtime/errors.py` | Machine-readable error model (`docs/ERROR_CODES.md`) |
| `runtime/config.py`, `rollout.py`, `backup.py`, `release.py`, `capacity.py`, `gate.py` | Config, staged rollout, backup/restore, SBOM/provenance/signing, sizing, GO gate |
| `schemas/` | 16 JSON Schemas for every wire/document contract |
| `docs/` | Threat model, ADRs, runbook, SLOs, incident, vulnerability/EOL, reviews, waivers, governance, configuration, capacity |
| `ops/` | Prometheus alert rules, Grafana dashboard |
| `evidence/` | Test results, perf baseline, checklist status (1,456 controls), RTM (100 checks), waivers, gate decision, release verification |
| `tests/` | Unit, crash (process kill), fault-injection, concurrency, fuzz, adversarial, contract, integration, governance suites; `perf/bench.py` |

## Quick start
```text
pip install -r requirements.lock          # cryptography==46.0.7 (hashes pending, W-004)
python gap04_disconnected_operation_controller/tools/run_all_tests.py
python -m gap04_disconnected_operation_controller.runtime.gate --archive <release.zip>
python gap04_disconnected_operation_controller/tests/perf/bench.py
```
The 4.2.0 dependency-free controller suite still runs with `python tests/test_controller.py` (and `-O`); the `pk_core` conformance suite (`tests/test_component.py`) requires `PK_CORE_PATH`.

## Interfaces
Emitted: `PK_AUTONOMY_LEASE/1`, `PK_DEGRADATION_TIER/1`, `PK_RECONCILIATION_RECORD/1` (reference controller) and `/2` (runtime), `PK_GAP04_HEALTH/1`, `PK_GAP04_ERROR/1`, `PK_GAP04_LOG/1`. Accepted: `PK_SIGNED_LEASE/1`, `PK_POLICY_BUNDLE/1`, `PK_TRUST_BUNDLE/1`, `PK_TIME_TOKEN/1`, `PK_HEARTBEAT/1`, `PK_CAPABILITY_GRANT/1`, quarantine command/release. Adjacent: `PK_SUPERVISOR_COMMAND/1`, `PK_REPLICATION_BATCH/1`. See `COMPATIBILITY_MATRIX.json`.
