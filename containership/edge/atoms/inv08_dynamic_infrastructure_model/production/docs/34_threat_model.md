# 34 - Formal threat model (INV-08 lease pool) - PK_DYN_THREAT/1

Status: DRAFT. Risk owner: UNASSIGNED. Approver: UNASSIGNED. Every residual risk is
`UNACCEPTED` until a named human owner signs it; code refuses `ACCEPTED` without an owner.

The authoritative, machine-readable model is `production/threat_model.py::MODEL`.
This document explains it; if they disagree, the module wins and this doc is a defect.

## Scope
`model.Pool` (lease table, `tick()` scaling decision) and the production overlay
around it: provider calls (PK_DYN_PROVIDER), node agents, release/policy intake,
audit log, keys, tenant state and telemetry.

## Assets, flows, trust boundaries
- Assets: pool state, policy bundle, artifacts, audit log, keys, tenant state, telemetry.
- Actors/processes: controller (trusted), node agent (untrusted once compromised),
  provider (external), tenant (external), operator/CI.
- Boundaries: B.tenant, B.node, B.provider, B.supply, B.operator.
- Flows: demand, heartbeat/attestation, provision, release, audit, telemetry, tenant state.

## STRIDE enumeration
14 threats (T01-T14) cover all six STRIDE categories; each names its target,
abuse-case family, mitigating symbols (verified importable by
`test_secobs.ThreatModelTests.test_every_mitigation_resolves`) and a residual level.

## Tenant and compromised-node abuse cases
`abuse_cases("tenant")`: T08 cross-tenant read, T09 leakage through telemetry,
T10 demand exhaustion, T11 cardinality explosion, T13 namespace escape.
`abuse_cases("compromised_node")`: T01 forged attestation, T12 KEK misuse.

## Supply-chain / replay / spoofing attack trees
Three AND/OR trees (`MODEL["attack_trees"]`); `tree_achievable(tree, unmitigated)`
evaluates whether a goal is reachable when a set of mitigations fail.

## Mitigation ownership and residual risk
`residual_risk_register()` lists every threat with level, `acceptance=UNACCEPTED`,
`owner=UNASSIGNED`. BLOCKED: a human risk owner and review meeting.

## Known gaps (not mitigated here)
Real hardware attestation, asymmetric release signing, OS/hypervisor isolation,
transport encryption and at-rest encryption are BLOCKED (see components 35-38).
