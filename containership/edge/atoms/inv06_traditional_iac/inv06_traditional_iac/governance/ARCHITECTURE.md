# INV-06 Traditional IaC — Architecture (v4.3.0)

Status: **Draft for review** (MC-003 ADR approval pending). Covers baseline check CHK-007 for every implemented component.

## Component boundaries and data flow

```mermaid
flowchart LR
  subgraph Callers["Untrusted callers (operators, CI, INV-07)"]
    OP[Operator / pipeline]
  end
  subgraph Edge["Trust boundary 1: identity"]
    AUTHN[security.TokenAuthenticator]
    AUTHZ[security.Authorizer<br/>default-deny, tenant-scoped]
  end
  subgraph Control["INV-06 control plane (this package)"]
    ADM[resilience.AdmissionController<br/>+ FreezeController + DegradedMode]
    CFG[config.parse_hcl_subset → compile_config<br/>overlays global < env < site]
    GRAPH[graph.ResourceGraph]
    ENGINE[state.IacState<br/>plan / apply / drift / protect]
    POL[policy.PolicyGate → GAP-13]
    SIGN[security.Signer<br/>plan approval]
    EXEC[execution.execute_plan / TerraformRunner]
    OBS[observability: health, metrics,<br/>logs, traces, explain, lineage]
  end
  subgraph Persist["Trust boundary 2: storage"]
    LOCK[locking.FileLeaseLock<br/>+ FencedBackend]
    BE[durable.FileStateBackend<br/>revisions + WAL + HEAD]
    AUD[security.SignedAuditLog]
    PROV[config.ProvenanceLedger]
  end
  subgraph Ext["Trust boundary 3: providers (external)"]
    PRV[Provider adapters<br/>cloud / datacenter / edge]
    KMS[(Estate KMS / HSM)]
  end
  OP --> AUTHN --> AUTHZ --> ADM --> CFG --> GRAPH --> ENGINE
  ENGINE --> POL --> SIGN --> EXEC --> PRV
  EXEC -->|complete| LOCK --> BE
  EXEC -->|partial| ENGINE
  ENGINE --> AUD
  CFG --> PROV
  SIGN -.keys.-> KMS
  ENGINE --> OBS
```

## Control flow of one change

1. Authenticate caller → authorise `plan.create` for tenant.
2. Admission (bounded concurrency/queue); refuse if frozen or critical dependency down.
3. Parse + compile configuration (pinned subset, overlay precedence), build the resource graph (cycles/dangling refused).
4. `IacState.plan(desired)` against the HEAD serial loaded from the backend (digest-verified).
5. `PolicyGate.check(plan)` — fail closed, decision bound to plan digest and policy version.
6. A different principal with `plan.approve` signs the plan (separation of duties).
7. Applier acquires a lease (fencing token) → `execute_plan` drives the provider in graph order.
8. Only a complete provider run is applied to `IacState` and committed through `FencedBackend.commit` (CAS on serial + fencing). A partial run triggers drift reconciliation; nothing is committed.
9. Audit event (signed), provenance record, lineage record, metrics/logs/trace emitted.

## Failure domains

| Domain | Failure | Safe behaviour | Code |
|---|---|---|---|
| Process | crash mid-commit | WAL recovery rolls forward/back deterministically | `durable.recover` |
| Host disk | corrupt revision | refuse load, restore from backup | `durable.StateCorrupt`, `restore` |
| Concurrency | two writers | CAS + fencing; one wins | `StateConflict`, `FencingViolation` |
| Policy engine | down / malformed | fail closed | `PolicyUnavailable` |
| Identity/keys | down | per `OUTAGE_POLICY` | `outage_decision` |
| Provider | partial failure | stop, report, reconcile via drift | `execute_plan` |
| Overload | burst | shed with `Overloaded` | `AdmissionController` |
| Site | loss | residency-and-serial-aware failover | `FailoverController` |

## Not in this package (explicit exclusions)

Real cloud/datacenter provider adapters, Terraform binaries, estate KMS/HSM, distributed consensus lock services, WORM audit storage, CI runners, dashboards hosting. These are integration points, declared by protocol (`execution.Provider`, `security.KeyProvider`, `locking.LeaseBackend`, `policy.PolicyEngine`).
