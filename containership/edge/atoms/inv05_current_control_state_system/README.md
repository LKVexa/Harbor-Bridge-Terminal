# INV-05 — Current control-state system

**Version:** 4.3.0 (see `CHANGELOG.md`) · **Group:** 01_Source_Inventory · **Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklists:** 100 requirements in `CHECKLIST.json` (traced in `traceability/TRACE_MATRIX.md`); 52 missing-component items / 2 346 sub-items (status in `traceability/CHECKLIST_STATUS.md`).
**Framework dependency:** `pk_core` is needed only for the 100-item framework gate and is not bundled (EX-003).
**Master prompts:** `MASTER.md` is not present in this archive; ADR-007 proposes formally removing it (EX-002).

The control-state system is the consistent key/value state every controller reads and writes. Each committed transaction gets a new global revision; writes are compare-and-swap transactions with success/failure branches; consumers read at a revision and watch from a revision; compaction explicitly refuses any read or watch that needs discarded history, so a controller relists instead of silently missing changes.

> **What 4.3.0 is, and is not.** It is a working single-member service: an MVCC engine, a durable encrypted WAL with crash recovery, an mTLS HTTP/NDJSON transport, authn/authz, namespaces, leases with fencing, backups, audit, metrics/logs/traces and CI tooling, all tested. It is **not** a replicated, consensus-backed cluster. Multi-member HA stays blocked until an owner-approved backend is pinned (ADR-002, EX-001). `tools/release_gate.py` reports this and blocks promotion until the open owner decisions are made.

## Package map

| Area | Modules |
|---|---|
| Engine | `store.py` (MVCC, txn, predicates, ranges, deletes, leases, compaction), `limits.py`, `errors.py` |
| Durability | `wal.py` (WAL, snapshots, recovery, AES-GCM, keyring), `backup.py` (backup/restore, compaction controller) |
| Watches | `watch.py` (live + catch-up delivery, progress, resume, backpressure, drain) |
| Protocol | `schema.py` (versioned JSON schemas, negotiation), `server.py` (mTLS HTTP + NDJSON), `client.py` (retries, list-then-watch `Mirror`) |
| Security | `security.py` (SPIFFE mTLS, tokens, deny-by-default policy, secrets, TLS policy), `audit.py` (HMAC hash chain) |
| Operations | `service.py` (pipeline, controls, health), `observability.py`, `config.py`, `bootstrap.py`, `serve.py`, `backend.py`, `replication.py` |
| Verification | `linearizability.py`, `bench.py`, `conformance/`, `tools/`, `tools_check.py`, `tests/` |
| Docs / deploy | `docs/` (architecture, requirements, interfaces, ADRs, threat model, DR, runbooks), `deploy/`, `observability/` |
| Legacy | `state.py`, `component.py`, `contract.py` (4.2.0 reference model + pk_core component, API unchanged) |

## Quick start

```text
# tests (from the directory that contains the package)
python -m unittest discover -s inv05_current_control_state_system/tests
python -O -m unittest discover -s inv05_current_control_state_system/tests

# full acceptance gate -> evidence/gate_report.json (+ tests, conformance, SBOM, provenance, bench, restore drill)
python inv05_current_control_state_system/tools/ci_gate.py

# promotion decision for a topology
python inv05_current_control_state_system/tools/release_gate.py --topology single-member

# conformance vectors, benchmark, restore drill
python -m inv05_current_control_state_system.conformance.runner
python -m inv05_current_control_state_system.bench --durable tmp --ops 20000
python inv05_current_control_state_system/tools/restore_drill.py
```

To run the service, follow `docs/operations/RUNBOOK_DAY0.md` (`bootstrap`, then `serve`, with the config overlays in `deploy/config/`).

## With the external framework

```text
python -m pk_core run INV-05 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-05 --out conformance/PK_GATE_RESULTS.json
```

The two framework tests in `tests/test_component.py` are the only skips the CI gate allows; it reports them against EX-003.

## Where to look first

`AUDIT_REPORT.md` (what changed and what was verified) · `traceability/CHECKLIST_STATUS.md` (all 2 346 checklist items) · `docs/EXCEPTIONS.json` (every open gap, with owner and expiry) · `MISSING_COMPONENTS.md` (component-level status).
