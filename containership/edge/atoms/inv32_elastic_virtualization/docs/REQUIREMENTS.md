# INV-32 Requirements (SHALL statements, v4.3.0)

Machine-readable form: `RTM.json` (rows `REQ-*`). Priority P0 unless stated.

## Functional — memory (C011, C012)
- **REQ-MEM-001** The controller SHALL adjust a running guest's memory only between its declared floor and ceiling, clamping requests above the ceiling.
- **REQ-MEM-002** It SHALL refuse any target below the working-set floor or provider-reported non-balloonable memory.
- **REQ-MEM-003** It SHALL align targets to the provider's memory block size without leaving the declared bounds.
- **REQ-MEM-004** It SHALL record the hypervisor-confirmed applied value, never the requested value, and report refused/partial reclaim.
## Functional — vCPU
- **REQ-CPU-001** vCPU targets SHALL lie in [max(1, min_boot_vcpus), vcpu_max].
- **REQ-CPU-002** A partially applied vCPU change SHALL be compensated to the original count or reported as unknown.
## Rollback / reconciliation
- **REQ-RBK-001** A revert SHALL be accepted only for an authenticated audit record of this host/guest, in the current ownership epoch, whose applied value equals current live state.
- **REQ-RBK-002** On start-up every incomplete journalled operation SHALL be reconciled against live state before writes; mutations SHALL never be replayed blindly.
## Invariants
- **REQ-INV-001** Σ guest memory SHALL NOT exceed usable host memory minus the reserve, including concurrently in-flight growth.
- **REQ-INV-002** No guest SHALL be below its floor as a result of any INV-32 action, including recovery.
## Applicability (C012)
- **REQ-CTX-001** Cloud/datacenter: supported with a consensus lease store (BLOCKED ADR-0003). Near-edge: supported single-node with `FileLeaseStore`. Far-edge/disconnected: supported in local-safe mode only while lease and state integrity are provable; otherwise FROZEN_WRITE. Excluded: cross-site guest control.
## Non-functional (C013)
- **REQ-NFR-LAT** Controller-owned decision p99 ≤ 2 ms; durable mutation p99 ≤ 50 ms on reference hardware (bench gate).
- **REQ-NFR-AVL** Read/health availability 99.9%; mutation availability is subordinate to safety (may freeze).
- **REQ-NFR-DUR** No acknowledged mutation SHALL lack a durable journal+audit record (fsync before response).
- **REQ-NFR-CON** Linearizable per guest (serialized, CAS on provider state version).
- **REQ-NFR-ISO** Tenant-scoped principals SHALL NOT read or mutate other tenants' guests nor learn their existence.
- **REQ-NFR-DET** Given identical inputs and seeds, decisions SHALL be identical (pure `_plan`).
- **REQ-NFR-REC** RPO ≤ anchor interval (default 300 s); RTO ≤ 15 min (RUNBOOKS).
## Outcomes and lifecycle (C014, C015)
- **REQ-OUT-001** Every response SHALL carry one outcome ∈ {success, partial_success, degraded_success, rejected, retryable_failure, terminal_failure, unknown_outcome, rolled_back} and, on failure, a stable code.
- **REQ-LCY-001** Operation lifecycle: prepared → provider_requested → provider_confirmed → state_committed → audit_committed; side exits failed / unknown → reconciled. No other transitions.
- **REQ-LCY-002** Guest lifecycle: mutations only in `running`.
## Capacity/quota/fairness (C017)
- **REQ-QTA-001** Tenant memory SHALL NOT exceed its hard cap; borrowing above guarantee SHALL NOT make another tenant's guarantee unsatisfiable.
- **REQ-QTA-002** Per-tenant rate and in-flight limits SHALL bound control-plane use; safety operations keep reserved capacity.
## Network (C018)
- **REQ-NET-001** Loss of lease store → FROZEN_WRITE; loss of provider → circuit open, mutations rejected retryably; loss of telemetry → control continues (TELEMETRY_DOWN); loss of audit export → local durable audit continues, anchors queue.
## Precedence (C019)
- **REQ-PRC-001** Conflicts resolve: security/integrity > isolation/residency > state correctness > SLO/availability > cost/efficiency, unless governance approves otherwise via a waiver.
