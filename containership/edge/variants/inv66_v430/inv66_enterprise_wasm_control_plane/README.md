# INV-66 - Enterprise Wasm control plane

**Version:** 4.3.0 (see `CHANGELOG.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master requirement source:** [`MASTER.md`](../MASTER.md) — generated, digest-pinned mirror of `CHECKLIST.json` (upstream series text not bundled; waiver W-005)
**Licence:** all rights reserved, selection pending ([`LICENSE`](../LICENSE), waiver W-008)

The enterprise Wasm control plane sits above many lattices and many teams. It adds what a single lattice lacks: who may deploy where, which registries and signers are acceptable, and a record of every change. Guardrails are enforced at admission, so a manifest that pulls from an unapproved registry never reaches a deployment manager.

## Responsibility

Own multi-lattice governance: organisation and lattice RBAC, admission guardrails on manifests, approved registries and signers, and an append-only change audit.

## Owns

- Organisation and lattice RBAC
- Manifest admission guardrails
- Approved registries and signers
- Change audit trail
- Cross-lattice inventory

## Explicitly does not own

- Lattice runtime
- Reconciliation
- Signing keys
- Identity provider
- Billing

## Non-goals

- Running lattices
- Holding signing keys
- Issuing identity

## Interfaces

- `admit` - PK_ECP_ADMIT/1 - manifest admission decision
- `audit` - PK_ECP_AUDIT/1 - append-only change record
- `rbac` - PK_ECP_RBAC/1 - role bindings per lattice

## Service-level objectives

- **guardrails** - zero unadmitted manifests forwarded (error budget: no budget)
- **audit integrity** - audit chain verifies end to end (error budget: no budget)
- **admission latency** - p99 under 50ms (error budget: 1% may exceed)

## Running it

Install (Python ≥ 3.11) and run the production service:

```
pip install -c constraints.txt .
inv66 validate-config examples/config.prod.example.json
inv66 serve --config /etc/inv66/config.json --store /var/lib/inv66/store --node-id $(hostname) \
      --org acme --deploy-url https://inv63.internal/deliver --tls-cert … --tls-key … --tls-client-ca …
```

Verification (no network, no `pk_core` needed):

```
python -m unittest discover -s inv66_enterprise_wasm_control_plane/tests -v
python -O -m unittest discover -s inv66_enterprise_wasm_control_plane/tests
python tools/bench.py --n 3000 --fsync --gate --baseline perf/baseline.json
python tools/repo_checks.py && python tools/gen_evidence.py && python tools/exit_gate.py
```

Full 100-item Post-Kubernetes conformance additionally requires `pk_core`:

```
python inv66_enterprise_wasm_control_plane/tests/test_component.py   # set PK_CORE_PATH if pk_core is elsewhere
python -m pk_core list
python -m pk_core run INV-66 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-66 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-66`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-66`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.

## Where things are

| Need | Look at |
|---|---|
| Architecture, topology, degraded modes, capacity | [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md), [`docs/ADR-0001-control-plane-architecture.md`](../docs/ADR-0001-control-plane-architecture.md) |
| APIs, schemas, error codes, compatibility | [`docs/API.md`](../docs/API.md), `schemas/`, `errors.py` |
| Security | [`docs/THREAT_MODEL.md`](../docs/THREAT_MODEL.md) |
| Operating it (day 0/1/2, backup/restore, incidents) | [`docs/OPERATIONS.md`](../docs/OPERATIONS.md) |
| Requirement → code → test → evidence | [`docs/REQUIREMENTS.md`](../docs/REQUIREMENTS.md), `governance/RTM.json` |
| Checklist execution record (1,420 items) | [`governance/CHECKLIST_STATUS.md`](../governance/CHECKLIST_STATUS.md) |
| Waivers, evidence, exit gate | `governance/WAIVERS.json`, `governance/ACCEPTANCE_EVIDENCE.json`, `governance/PRODUCTION_EXIT_GATE.json` |

## Audit status

See `AUDIT_REPORT.md` (v4.3.0 section) for the remediation record. The production exit gate currently returns **NO_GO**: named owners/approvals, `pk_core` conformance, real-dependency E2E, multi-node HA and hosted CI remain open and are tracked as waivers W-001…W-015. `MISSING_COMPONENTS.md` keeps the v4.2.0 gap inventory with a v4.3.0 residual summary.
