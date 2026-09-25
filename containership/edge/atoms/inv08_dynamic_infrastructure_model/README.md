# INV-08 - Dynamic infrastructure model

**Version:** 4.2.0  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

INV-08 models elastic infrastructure as leased capacity rather than permanently
owned nodes. The package-local executable model grows and shrinks a node pool
between hard bounds, renews leases for busy nodes, reclaims only idle nodes, and
accounts node-hours.

Version 4.2.0 is a hardened reference/scaffold, **not a standalone production
certification**. The wider checklist requires external `pk_core` conformance,
provider/control-plane integration, security controls, distributed-state
semantics, telemetry, operational evidence, and release governance. Those gaps
are explicitly tracked in `MISSING_COMPONENTS.md`.

## Responsibility

Own elastic-capacity policy: lease-based node membership, demand-driven scaling
within bounds, safe reclamation of idle nodes, and pool cost accounting.

## Owns

- Leased node membership model
- Demand-driven scale-out and scale-in policy
- Hard pool bounds
- Safe reclamation of idle nodes
- Busy-node lease renewal
- Node-hour accounting
- Dependency-free deterministic pool state transitions

## Explicitly does not own

- Provider provisioning APIs
- Workload scheduling
- Image building
- Billing systems
- Networking
- The distributed lease store or consensus layer
- Identity, attestation, policy, or key-management services

## Interfaces declared by the contract

- `PK_DYN_LEASE/1` - node lease and expiry
- `PK_DYN_SCALE/1` - scaling decision
- `PK_DYN_COST/1` - node-hours per pool

These protocol names are contract declarations only. Wire schemas, transport
bindings, authentication, authorization, retry, idempotency, and compatibility
fixtures remain missing and are listed in `MISSING_COMPONENTS.md`.

## 4.2.0 hardening highlights

- Moved safety-critical pool logic to dependency-free `model.py`.
- Made package metadata and the pool importable even when `pk_core` is absent.
- Added validation for NaN/Inf, boolean-as-integer inputs, malformed restored
  node state, invalid bounds, and time regression.
- Made each `tick()` transactional so a rejected decision cannot partially
  mutate the pool.
- Added collision-safe node ID allocation after restored state.
- Added explicit `elapsed_hours` accounting and richer scaling decision output.
- Split standalone unit tests from optional `pk_core` integration tests.
- Added strict/standalone preflight so missing `pk_core` cannot be mistaken for
  full conformance.
- Removed the prior README claim that `MASTER.md` was bundled when it was not.
- Replaced the blanket production-readiness implication with an explicit gap
  inventory and audit report.

## Local verification

From the directory containing this package:

```text
python inv08_dynamic_infrastructure_model/tests/test_component.py
python inv08_dynamic_infrastructure_model/preflight.py --allow-missing-pk-core
```

For the full conformance path, make `pk_core` importable (for example by setting
`PK_CORE_PATH`) and run:

```text
python inv08_dynamic_infrastructure_model/preflight.py
python -m pk_core list
python -m pk_core run INV-08 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-08 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

## Service-level objectives declared by the contract

- **bounded** - pool never exceeds its configured maximum
- **safe reclaim** - zero busy nodes reclaimed
- **responsiveness** - scaling decision within one tick of demand change

These are declared objectives; production measurement, alerting, error-budget
policy, and release regression gates are not implemented in this ZIP.

## Operating model

- **Day 0:** validate package integrity, resolve `pk_core`, load site-specific
  configuration, initialize the authoritative lease store, then bootstrap the
  first controller instance.
- **Day 1:** execute conformance and integration gates before staged rollout.
- **Day 2:** continuously reconcile desired/observed infrastructure, preserve
  audit evidence, monitor saturation/lease health, and exercise rollback and
  emergency-disable controls.

The concrete distributed lease store, reconciliation controller, provider
adapters, observability stack, and operational automation are future components,
not silently implied by this reference model.
