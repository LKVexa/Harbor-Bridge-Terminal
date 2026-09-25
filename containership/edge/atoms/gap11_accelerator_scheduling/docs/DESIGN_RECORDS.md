# GAP-11 component design records (GAP11-*.11)
Generated from `tools/registry.py`. Owner fields read UNASSIGNED because no owner has been named (GAP11-P2-46).

## GAP11-P0-01 — Durable lease-state store  <a id="GAP11-P0-01"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Transactional persistence for allocations, releases, scrub state, quarantine state, and tenant security epochs across process/node restarts.  
- **Source controls:** C032, C037, C057, C095  
- **Purpose / scope:** Durable, crash-consistent, CAS-only persistence of leases, device security state, idempotency keys and leadership.  
- **Non-goals:** Replication/quorum (single-writer WAL; see BLK-ENV); schema-less queries.  
- **Trust boundary:** Process-local file owned by the controller account.  
- **Dependencies:** filesystem with fsync  
- **Inputs:** commit(ops, pre, prov, fence)  
- **Outputs:** revision, get/scan  
- **Implementation:** `gap11_control/store.py`  
- **Tests:** `test_state.StoreTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** state  
- **Blockers:** BLK-ENV: requires a provisioned multi-node deployment and real observation period (quorum/replica restore paths)

## GAP11-P0-02 — Distributed compare-and-swap / fencing layer  <a id="GAP11-P0-02"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Monotonic ownership epochs or fencing tokens preventing two controllers from allocating the same physical accelerator after failover or partition.  
- **Source controls:** C055, C058  
- **Purpose / scope:** Storage-side fencing: every controller mutation carries the leader epoch; the store rejects lower tokens.  
- **Non-goals:** Fencing of external side-effects the store does not mediate (vendor calls must re-check).  
- **Trust boundary:** Store is the fence authority.  
- **Dependencies:** LeaderElector epoch  
- **Inputs:** fence=(resource, token)  
- **Outputs:** STALE_FENCE refusals  
- **Implementation:** `gap11_control/store.py`, `gap11_control/election.py`  
- **Tests:** `test_state.FencingElectionTests`, `test_verification.SplitBrainTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** state  

## GAP11-P0-03 — HA controller ownership / leader election  <a id="GAP11-P0-03"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Explicit active-controller authority and failover behavior, integrated with fencing rather than best-effort locks.  
- **Source controls:** C051, C055, C058  
- **Purpose / scope:** Lease-based leader election on the durable store; epoch = fencing token; safety margin before local expiry.  
- **Non-goals:** Consensus across stores (single store); leader for other GAP subsystems.  
- **Trust boundary:** Controllers trust only the store record.  
- **Dependencies:** store, monotonic clock  
- **Inputs:** try_acquire/renew/step_down  
- **Outputs:** epoch, is_leader  
- **Implementation:** `gap11_control/election.py`  
- **Tests:** `test_state.FencingElectionTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** state  
- **Blockers:** BLK-ENV: requires a provisioned multi-node deployment and real observation period (multi-node failover observation)

## GAP11-P0-04 — Lease TTL, heartbeat, and orphan reconciliation  <a id="GAP11-P0-04"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Reclaim or quarantine resources after workload/controller death without prematurely releasing live workloads.  
- **Source controls:** C015, C025, C052, C057  
- **Purpose / scope:** Lease TTL on the monotonic clock, heartbeats, and deterministic orphan reconciliation that is destructive only on unambiguous evidence.  
- **Non-goals:** Deciding workload liveness (supplied by the lifecycle system).  
- **Trust boundary:** Liveness input is trusted as reported by the lifecycle hook.  
- **Dependencies:** liveness oracle  
- **Inputs:** heartbeat, reconcile  
- **Outputs:** report {reclaimed, renewed, suspect, quarantined}  
- **Implementation:** `gap11_control/controller.py`  
- **Tests:** `test_state.TTLAndReconcileTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** state  

## GAP11-P0-05 — Idempotency and replay-protection store  <a id="GAP11-P0-05"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Request IDs and durable deduplication for allocate/release/scrub calls.  
- **Source controls:** C025, C049, C058  
- **Purpose / scope:** Durable request-id dedup committed in the same transaction as the mutation; conflicting replays refused.  
- **Non-goals:** Global dedup across tenants (keys are tenant-scoped at the boundary).  
- **Trust boundary:** request_id is client-chosen, namespaced by authenticated tenant.  
- **Dependencies:** request_id + payload  
- **Inputs:** prior result or new mutation  
- **Outputs:** DUPLICATE_REQUEST / IDEMPOTENCY_CONFLICT  
- **Implementation:** `gap11_control/controller.py`, `gap11_control/service.py`  
- **Tests:** `test_state.IdempotencyTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** state  

## GAP11-P0-06 — Real hardware inventory adapter  <a id="GAP11-P0-06"></a>
- **Disposition:** SIMULATED  
- **Required capability (checklist):** Integration with GAP-02 and vendor APIs for device identity, memory, features, health, and hot-plug changes.  
- **Source controls:** C021, C030, C083  
- **Purpose / scope:** Vendor-neutral canonical device model; normalisation; stable identity; diffing; bounded retries; evidence.  
- **Non-goals:** Driver installation; firmware update.  
- **Trust boundary:** Vendor SDK runs in a privileged node agent; the controller consumes typed records only.  
- **Dependencies:** vendor providers (simulated)  
- **Inputs:** collect()  
- **Outputs:** canonical records + PK_INVENTORY_EVIDENCE/1  
- **Implementation:** `gap11_control/hardware.py`  
- **Tests:** `test_hardware.InventoryTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** hardware  
- **Blockers:** BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/FPGA/NPU) in the build environment

## GAP11-P0-07 — Partition topology/lifecycle adapter  <a id="GAP11-P0-07"></a>
- **Disposition:** SIMULATED  
- **Required capability (checklist):** Representation of mutually compatible partition profiles and creation/destruction/drain operations for MIG/SR-IOV/vendor slices.  
- **Source controls:** C011, C015, C021  
- **Purpose / scope:** Alternative partition layouts per device model, mutually exclusive; reconfigure only when drained; residual-capacity scoring.  
- **Non-goals:** Executing MIG/SR-IOV commands on real devices.  
- **Trust boundary:** Reconfigure is a privileged node-agent operation.  
- **Dependencies:** profiles, lease count  
- **Inputs:** reconfigure(profile)  
- **Outputs:** declared partitions  
- **Implementation:** `gap11_control/hardware.py`  
- **Tests:** `test_hardware.PartitionTopologyTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** hardware  
- **Blockers:** BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/FPGA/NPU) in the build environment

## GAP11-P0-08 — Vendor-specific scrub/reset executor  <a id="GAP11-P0-08"></a>
- **Disposition:** SIMULATED  
- **Required capability (checklist):** Actual VRAM/HBM/state zeroization or reset with timeout, retry policy, health verification, and evidence.  
- **Source controls:** C046, C048, C053, C059  
- **Purpose / scope:** reset -> zeroize -> independent verify with deadline and bounded retry; any doubt quarantines.  
- **Non-goals:** Proving zeroization of vendor-internal state the SDK does not expose.  
- **Trust boundary:** Scrub backend runs privileged on the node.  
- **Dependencies:** device record  
- **Inputs:** PK_SCRUB_EVIDENCE/1  
- **Outputs:** CLEAN or QUARANTINED  
- **Implementation:** `gap11_control/hardware.py`, `gap11_control/controller.py`  
- **Tests:** `test_hardware.ScrubTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** hardware  
- **Blockers:** BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/FPGA/NPU) in the build environment

## GAP11-P0-09 — Device attestation binding  <a id="GAP11-P0-09"></a>
- **Disposition:** SIMULATED  
- **Required capability (checklist):** Cryptographic binding between discovered accelerator identity/capabilities, node identity, driver/firmware state, and GAP-06 attestation evidence.  
- **Source controls:** C044, C045  
- **Purpose / scope:** Bind device stable_id, capability digest, driver/firmware and node identity to a signed, fresh quote.  
- **Non-goals:** Hardware root-of-trust measurement (GAP-06).  
- **Trust boundary:** Quote signer = node attestation key (simulated keyring).  
- **Dependencies:** inventory record, quote  
- **Inputs:** verify()  
- **Outputs:** attested / ATTESTATION_INVALID  
- **Implementation:** `gap11_control/security.py`  
- **Tests:** `test_security.AttestationTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** security  
- **Blockers:** BLK-PKI: no mTLS PKI / SPIFFE issuer / GAP-06 attestation service available; BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate

## GAP11-P0-10 — Authenticated service boundary  <a id="GAP11-P0-10"></a>
- **Disposition:** SIMULATED  
- **Required capability (checklist):** mTLS/workload identity or equivalent authentication for inventory, allocate, release, and scrub APIs.  
- **Source controls:** C023, C044, C047  
- **Purpose / scope:** Workload-identity credential verification: MAC, audience, expiry, skew, nonce replay window, live key rotation.  
- **Non-goals:** mTLS termination (needs PKI).  
- **Trust boundary:** Only verified claims (sub, ten, knd, scp) reach authorization.  
- **Dependencies:** credential  
- **Inputs:** Principal  
- **Outputs:** UNAUTHENTICATED / REPLAY_DETECTED  
- **Implementation:** `gap11_control/security.py`, `gap11_control/service.py`  
- **Tests:** `test_security.AuthnTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** security  
- **Blockers:** BLK-PKI: no mTLS PKI / SPIFFE issuer / GAP-06 attestation service available

## GAP11-P0-11 — Authorization/capability policy  <a id="GAP11-P0-11"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Tenant/workload permissions for device classes, partitions, administrative scrub, quarantine overrides, and sensitive inventory.  
- **Source controls:** C024, C042, C043  
- **Purpose / scope:** Deny-by-default capability policy with operator-only scopes and tenant binding from the authenticated principal.  
- **Non-goals:** Policy authoring UI.  
- **Trust boundary:** Policy rules are configuration under audit.  
- **Dependencies:** Principal, action, resource  
- **Inputs:** decide()  
- **Outputs:** allow/deny + reason  
- **Implementation:** `gap11_control/security.py`, `gap11_control/service.py`  
- **Tests:** `test_security.AuthzTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** security  

## GAP11-P0-12 — Versioned wire schemas  <a id="GAP11-P0-12"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Concrete JSON/Protobuf/WIT/RPC schema files for accelerator inventory, allocation, release, and scrub interfaces, including compatibility rules.  
- **Source controls:** C022, C026, C027, C082  
- **Purpose / scope:** Versioned closed request schemas, open response schemas, one error envelope, limits before logic.  
- **Non-goals:** Protobuf/WIT encodings (JSON only).  
- **Trust boundary:** Schema validation is the first gate after authentication.  
- **Dependencies:** bytes  
- **Inputs:** decode()  
- **Outputs:** typed dict or SCHEMA_INVALID/MESSAGE_TOO_LARGE  
- **Implementation:** `gap11_control/wire.py`, `gap11_control/schemas/`  
- **Tests:** `test_wire.SchemaTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** interface  

## GAP11-P0-13 — API transport/server  <a id="GAP11-P0-13"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Bounded request queues, deadlines, cancellation, backpressure, connection limits, and structured failure mapping.  
- **Source controls:** C025, C028, C054, C067  
- **Purpose / scope:** Transport-independent request pipeline + loopback HTTP binding with in-flight bound, deadlines, size limits.  
- **Non-goals:** Public network exposure without mTLS (refused).  
- **Trust boundary:** Loopback only in this build.  
- **Dependencies:** HTTP  
- **Inputs:** handle()  
- **Outputs:** JSON + status  
- **Implementation:** `gap11_control/service.py`  
- **Tests:** `test_wire.TransportTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** interface  
- **Blockers:** BLK-PKI: no mTLS PKI / SPIFFE issuer / GAP-06 attestation service available (non-loopback binding)

## GAP11-P0-14 — Admission quotas and fairness  <a id="GAP11-P0-14"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Per-tenant/project caps, reservation classes, starvation prevention, queue discipline, and capacity ceilings.  
- **Source controls:** C017, C054, C069  
- **Purpose / scope:** Quotas with secure default, bounded fair queue with aging (starvation bound 2*aging_s).  
- **Non-goals:** Billing.  
- **Trust boundary:** Quota book is config.  
- **Dependencies:** tenant, active leases  
- **Inputs:** check(), FairQueue  
- **Outputs:** QUOTA_EXCEEDED / OVERLOADED  
- **Implementation:** `gap11_control/scheduler.py`  
- **Tests:** `test_scheduler`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** scheduler  

## GAP11-P0-15 — Workload lifecycle integration  <a id="GAP11-P0-15"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Authoritative hooks for workload start, exit, crash, eviction, and restart so leases cannot leak or be released too early.  
- **Source controls:** C030, C057  
- **Purpose / scope:** Authoritative workload start/exit/crash/evict/restart hooks mapped to heartbeat/release/reclaim, idempotent by event id.  
- **Non-goals:** Running workloads.  
- **Trust boundary:** Lifecycle events carry the tenant and are tenant-checked.  
- **Dependencies:** lifecycle events  
- **Inputs:** on_workload_event  
- **Outputs:** release/heartbeat results  
- **Implementation:** `gap11_control/controller.py`  
- **Tests:** `test_state.LifecycleAndHotplugTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** state  
- **Blockers:** BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate (real workload runtime)

## GAP11-P0-16 — Split-brain and stale-controller tests  <a id="GAP11-P0-16"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Multi-controller fault tests proving fencing under delayed messages, network partitions, failover, and replay.  
- **Source controls:** C058, C060, C086, C089  
- **Purpose / scope:** Multi-controller fault tests: partition, delayed messages, failover, replay, barrier collisions.  
- **Non-goals:** Network-level chaos (needs a cluster).  
- **Trust boundary:** Tests run against one shared durable store.  
- **Dependencies:** store  
- **Inputs:** test results  
- **Outputs:** evidence/  
- **Implementation:** `gap11_control/tests/test_verification.py`  
- **Tests:** `test_verification.SplitBrainTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** verification  
- **Blockers:** BLK-ENV: requires a provisioned multi-node deployment and real observation period (real network partitions)

## GAP11-P1-17 — Multi-device topology scheduler  <a id="GAP11-P1-17"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** NUMA/PCIe/NVLink/fabric locality, gang allocation, atomic multi-device reservation, and rollback.  
- **Source controls:** C017, C065, C066  
- **Purpose / scope:** Fabric-domain gang candidates and all-or-nothing multi-device reservation in one transaction.  
- **Non-goals:** NUMA/PCIe distance matrix from hardware.  
- **Trust boundary:** Topology comes from attested inventory.  
- **Dependencies:** topology  
- **Inputs:** allocate_gang  
- **Outputs:** PK_ACCELERATOR_GANG/1  
- **Implementation:** `gap11_control/scheduler.py`, `gap11_control/controller.py`  
- **Tests:** `test_scheduler.TopologyGangTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** scheduler  
- **Blockers:** BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/FPGA/NPU) in the build environment (real topology)

## GAP11-P1-18 — Fragmentation-aware partition placement  <a id="GAP11-P1-18"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Profile compatibility and placement minimizing unusable residual accelerator capacity.  
- **Source controls:** —  
- **Purpose / scope:** Fragmentation metric and smallest-sufficient-slice placement preferring partially used devices.  
- **Non-goals:** Live migration/defragmentation.  
- **Trust boundary:** n/a  
- **Dependencies:** devices, leases  
- **Inputs:** fragmentation(), place_partition()  
- **Outputs:** unusable_gb ratio  
- **Implementation:** `gap11_control/scheduler.py`, `gap11_control/hardware.py`  
- **Tests:** `test_scheduler.FragmentationTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** scheduler  

## GAP11-P1-19 — Power/thermal admission adapter  <a id="GAP11-P1-19"></a>
- **Disposition:** SIMULATED  
- **Required capability (checklist):** Live constraint integration with GAP-10 so thermally unavailable devices cannot be leased.  
- **Source controls:** C019, C030, C068  
- **Purpose / scope:** GAP-10 adapter: stale/missing/hot readings make a device inadmissible.  
- **Non-goals:** Setting power caps.  
- **Trust boundary:** GAP-10 readings trusted if fresh.  
- **Dependencies:** readings  
- **Inputs:** admissible()  
- **Outputs:** thermal_ok flag  
- **Implementation:** `gap11_control/hardware.py`  
- **Tests:** `test_hardware.ThermalHealthTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** hardware  
- **Blockers:** BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate

## GAP11-P1-20 — Health/RAS integration  <a id="GAP11-P1-20"></a>
- **Disposition:** SIMULATED  
- **Required capability (checklist):** ECC, Xid/device faults, link degradation, reset storms, predictive failure, and automatic quarantine/drain.  
- **Source controls:** C051, C052, C059  
- **Purpose / scope:** RAS classification (uncorrectable -> failed, reset storms, correctable thresholds) driving quarantine.  
- **Non-goals:** Vendor-specific Xid catalogues.  
- **Trust boundary:** RAS signals from node agent.  
- **Dependencies:** RAS signals  
- **Inputs:** observe()  
- **Outputs:** ok/degraded/failed  
- **Implementation:** `gap11_control/hardware.py`  
- **Tests:** `test_hardware.ThermalHealthTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** hardware  
- **Blockers:** BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/FPGA/NPU) in the build environment

## GAP11-P1-21 — Hot-plug and inventory reconciliation loop  <a id="GAP11-P1-21"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Safely handle device disappearance, replacement, renumbering, and changed capabilities while leases exist.  
- **Source controls:** C051, C057  
- **Purpose / scope:** Device disappearance marks leases SUSPECT; reappearance quarantines; capability change under lease drains.  
- **Non-goals:** Physical replacement workflow.  
- **Trust boundary:** Inventory diff trusted only for vendors whose provider answered.  
- **Dependencies:** inventory diff  
- **Inputs:** mark_missing, upsert_device  
- **Outputs:** state changes  
- **Implementation:** `gap11_control/controller.py`, `gap11_control/hardware.py`  
- **Tests:** `test_state.LifecycleAndHotplugTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** state  

## GAP11-P1-22 — Preemption/reservation policy  <a id="GAP11-P1-22"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Priority classes or reserved accelerators, including safe preemption semantics where enabled.  
- **Source controls:** C017, C019  
- **Purpose / scope:** Victim selection policy (strictly lower priority, min runtime, non-preemptible, budget).  
- **Non-goals:** Checkpoint/eviction execution.  
- **Trust boundary:** n/a  
- **Dependencies:** leases  
- **Inputs:** choose_victims()  
- **Outputs:** victims  
- **Implementation:** `gap11_control/scheduler.py`  
- **Tests:** `test_scheduler.PreemptionTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** scheduler  
- **Blockers:** BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate (eviction handoff)

## GAP11-P1-23 — Constraint policy engine  <a id="GAP11-P1-23"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Precedence for security, residency, workload class, generation, feature, cost, power, and SLO constraints, with deterministic decision reasons.  
- **Source controls:** C019, C076, C077  
- **Purpose / scope:** Hard constraints in fixed precedence, soft scoring after, per-device rejection reasons.  
- **Non-goals:** Cost model data.  
- **Trust boundary:** n/a  
- **Dependencies:** request, devices  
- **Inputs:** decide()  
- **Outputs:** Decision  
- **Implementation:** `gap11_control/scheduler.py`  
- **Tests:** `test_scheduler.ConstraintTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** scheduler  

## GAP11-P1-24 — Tamper-evident audit ledger  <a id="GAP11-P1-24"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Signed/chained events for allocation, release, scrub, quarantine, policy decisions, overrides, and controller leadership changes.  
- **Source controls:** C049, C090  
- **Purpose / scope:** Hash-chained, HMAC-signed, redacted audit ledger with external head witness.  
- **Non-goals:** WORM storage.  
- **Trust boundary:** Audit key is separate from authn keys in production.  
- **Dependencies:** events  
- **Inputs:** append/verify/head  
- **Outputs:** audit.jsonl  
- **Implementation:** `gap11_control/observability.py`  
- **Tests:** `test_observability.AuditLedgerTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** telemetry  
- **Blockers:** BLK-KMS: no KMS/HSM available; local SecretProvider is a stand-in

## GAP11-P1-25 — Metrics exporter  <a id="GAP11-P1-25"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Allocation latency, refusal reason, active leases, saturation, scrub latency/failure, queue depth, fragmentation, and reconciliation state.  
- **Source controls:** C061-C070, C072  
- **Purpose / scope:** Prometheus exposition with fixed label budget; latency histograms; refusal classes.  
- **Non-goals:** Metrics backend.  
- **Trust boundary:** No tenant/lease/device ids in labels.  
- **Dependencies:** events  
- **Inputs:** expose()  
- **Outputs:** text/plain  
- **Implementation:** `gap11_control/observability.py`  
- **Tests:** `test_observability.MetricsLogsTraceTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** telemetry  
- **Blockers:** BLK-ENV: requires a provisioned multi-node deployment and real observation period (live scrape + retention)

## GAP11-P1-26 — Structured logs and trace propagation  <a id="GAP11-P1-26"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Stable operation/request/lease/device IDs, trace context, privacy controls, and correlation to release lineage.  
- **Source controls:** C073-C079  
- **Purpose / scope:** Structured UTC JSON logs with redaction and debug sampling; W3C trace continuation.  
- **Non-goals:** Trace backend.  
- **Trust boundary:** n/a  
- **Dependencies:** fields  
- **Inputs:** log()  
- **Outputs:** JSON lines  
- **Implementation:** `gap11_control/observability.py`  
- **Tests:** `test_observability.MetricsLogsTraceTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** telemetry  
- **Blockers:** BLK-ENV: requires a provisioned multi-node deployment and real observation period

## GAP11-P1-27 — Health/readiness/debug endpoints  <a id="GAP11-P1-27"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Version, configuration digest, dependency health, controller role, reconciliation lag, and safe explain output.  
- **Source controls:** C071, C077  
- **Purpose / scope:** Health/readiness: version, config digest, role, epoch, store revision, dependencies, reconcile lag; redacted explain.  
- **Non-goals:** UI.  
- **Trust boundary:** n/a  
- **Dependencies:** component state  
- **Inputs:** health_report()  
- **Outputs:** PK_HEALTH/1  
- **Implementation:** `gap11_control/observability.py`  
- **Tests:** `test_observability.HealthAlertTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** telemetry  

## GAP11-P1-28 — Dashboards and alerts  <a id="GAP11-P1-28"></a>
- **Disposition:** DOCUMENTED  
- **Required capability (checklist):** Separate capacity exhaustion, policy rejection, scrub failure, device health failure, attack indicators, and software defects.  
- **Source controls:** C080  
- **Purpose / scope:** Alert rules with severity, class, expression, dedupe and runbook; dashboard specification.  
- **Non-goals:** Rendering dashboards.  
- **Trust boundary:** n/a  
- **Dependencies:** refusal-class counts  
- **Inputs:** evaluate_alerts()  
- **Outputs:** fired alerts  
- **Implementation:** `gap11_control/observability.py`, `docs/DASHBOARDS.md`  
- **Tests:** `test_observability.HealthAlertTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** telemetry  
- **Blockers:** BLK-ENV: requires a provisioned multi-node deployment and real observation period (deployed dashboards/alert routing)

## GAP11-P1-29 — Declarative configuration schema  <a id="GAP11-P1-29"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Validation, secure defaults, site/environment overlays, provenance, atomic activation, and rollback.  
- **Source controls:** C033-C038  
- **Purpose / scope:** Typed config schema, layered precedence with provenance, validate-then-atomic-activate, last-known-good rollback.  
- **Non-goals:** Remote config service.  
- **Trust boundary:** Config writes are privileged and audited.  
- **Dependencies:** layers  
- **Inputs:** apply/rollback  
- **Outputs:** effective config + digest  
- **Implementation:** `gap11_control/config.py`  
- **Tests:** `test_observability.ConfigTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** config  

## GAP11-P1-30 — Secrets/KMS integration  <a id="GAP11-P1-30"></a>
- **Disposition:** SIMULATED  
- **Required capability (checklist):** Certificate/key retrieval, rotation, redaction, and fail-closed behavior when key or identity services are unavailable.  
- **Source controls:** C039, C047, C048  
- **Purpose / scope:** Secret references only; pluggable backend; fail closed on outage; keyring rotation/retire.  
- **Non-goals:** Running a KMS.  
- **Trust boundary:** KMS is the root of secret trust.  
- **Dependencies:** secretref://  
- **Inputs:** resolve()  
- **Outputs:** bytes  
- **Implementation:** `gap11_control/security.py`  
- **Tests:** `test_security.SecretsTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** security  
- **Blockers:** BLK-KMS: no KMS/HSM available; local SecretProvider is a stand-in

## GAP11-P1-31 — Usage accounting/export  <a id="GAP11-P1-31"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Durable device/partition occupancy records suitable for capacity analytics, chargeback/showback, and audit without trusting ephemeral process memory.  
- **Source controls:** —  
- **Purpose / scope:** Durable per-lease usage records committed with the allocation/release transaction.  
- **Non-goals:** Chargeback pricing.  
- **Trust boundary:** n/a  
- **Dependencies:** leases  
- **Inputs:** usage_records()  
- **Outputs:** usage/<lease>  
- **Implementation:** `gap11_control/controller.py`  
- **Tests:** `test_observability.UsageAccountingTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** telemetry  

## GAP11-P1-32 — Operator quarantine/drain controls  <a id="GAP11-P1-32"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Explicit freeze, drain, unquarantine, force-reconcile, and maintenance workflows with authorization and audit.  
- **Source controls:** C059, C092, C097  
- **Purpose / scope:** Operator drain, freeze (maintenance), quarantine, health override — all fenced, provenance-recorded and audited.  
- **Non-goals:** Unquarantine without scrub (does not exist by design).  
- **Trust boundary:** Operator scopes are operator-only in policy.  
- **Dependencies:** operator requests  
- **Inputs:** set_draining/freeze/quarantine  
- **Outputs:** state changes  
- **Implementation:** `gap11_control/controller.py`  
- **Tests:** `test_observability.ConfigTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** config  

## GAP11-P2-33 — Public schema fixtures and contract tests  <a id="GAP11-P2-33"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Golden requests/responses/error cases for every wire interface.  
- **Source controls:** C029, C082  
- **Purpose / scope:** Golden request/response/error fixtures.  
- **Non-goals:** Binary encodings.  
- **Trust boundary:** n/a  
- **Dependencies:** none  
- **Inputs:** n/a  
- **Outputs:** fixtures/*.json  
- **Implementation:** `gap11_control/tests/fixtures/`  
- **Tests:** `test_wire.SchemaTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** verification  

## GAP11-P2-34 — Adjacent-layer integration tests  <a id="GAP11-P2-34"></a>
- **Disposition:** BLOCKED  
- **Required capability (checklist):** GAP-02, GAP-06, GAP-09, GAP-10, workload placement, runtime, and workload lifecycle integration tests.  
- **Source controls:** C030, C083  
- **Purpose / scope:** Adjacent-layer integration tests against GAP-02/06/09/10 and the workload runtime.  
- **Non-goals:** n/a  
- **Trust boundary:** n/a  
- **Dependencies:** none  
- **Inputs:** n/a  
- **Outputs:** n/a  
- **Implementation:** none  
- **Tests:** none  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** verification  
- **Blockers:** BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate

## GAP11-P2-35 — Fuzzing/property tests  <a id="GAP11-P2-35"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Request parsing, schema handling, state-machine sequences, lease replay, and malformed inventory.  
- **Source controls:** C085  
- **Purpose / scope:** Seeded mutation fuzzing of decoders and seeded property tests over allocator sequences.  
- **Non-goals:** Coverage-guided fuzzing (no atheris/hypothesis in the stdlib-only build).  
- **Trust boundary:** n/a  
- **Dependencies:** none  
- **Inputs:** n/a  
- **Outputs:** n/a  
- **Implementation:** `gap11_control/tests/test_wire.py`, `gap11_control/tests/test_scheduler.py`  
- **Tests:** `test_wire.SchemaTests`, `test_scheduler.AdversarialTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** verification  

## GAP11-P2-36 — Broader concurrency tests  <a id="GAP11-P2-36"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Release-vs-scrub, allocate-vs-inventory-change, controller failover, multi-device transactions, and long-running race/soak tests.  
- **Source controls:** C086, C088  
- **Purpose / scope:** Barrier-synchronised collision and soak tests.  
- **Non-goals:** Long-duration soak (hours).  
- **Trust boundary:** n/a  
- **Dependencies:** none  
- **Inputs:** n/a  
- **Outputs:** n/a  
- **Implementation:** `gap11_control/tests/test_verification.py`  
- **Tests:** `test_verification.SplitBrainTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** verification  
- **Blockers:** BLK-ENV: requires a provisioned multi-node deployment and real observation period (multi-hour soak)

## GAP11-P2-37 — Security adversarial suite  <a id="GAP11-P2-37"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Spoofed identity, capability escalation, stale lease replay, denial of service, side-channel assumptions, audit tampering, and malicious device metadata.  
- **Source controls:** C041, C050, C087  
- **Purpose / scope:** Adversarial suite: forged, replayed, expired, cross-tenant, confused deputy, escalation, tampered quotes/audit.  
- **Non-goals:** Side-channel testing (hardware).  
- **Trust boundary:** n/a  
- **Dependencies:** none  
- **Inputs:** n/a  
- **Outputs:** n/a  
- **Implementation:** `gap11_control/tests/test_security.py`  
- **Tests:** `test_security`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** verification  
- **Blockers:** BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/FPGA/NPU) in the build environment (side channels)

## GAP11-P2-38 — Fault-injection/disaster tests  <a id="GAP11-P2-38"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Store loss, partial write, process kill, node loss, network partition, time skew, dependency outage, and reconnect.  
- **Source controls:** C060, C089  
- **Purpose / scope:** Fault matrix: crash at every write point, dependency outages, ENOSPC, corruption.  
- **Non-goals:** Node loss / real network partitions.  
- **Trust boundary:** n/a  
- **Dependencies:** none  
- **Inputs:** n/a  
- **Outputs:** n/a  
- **Implementation:** `gap11_control/tests/test_verification.py`  
- **Tests:** `test_verification.FaultMatrixTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** verification  
- **Blockers:** BLK-ENV: requires a provisioned multi-node deployment and real observation period

## GAP11-P2-39 — Performance/scale benchmarks  <a id="GAP11-P2-39"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** p50/p95/p99/worst-case latency, burst/overload, fleet size, queue depth, memory/CPU overhead, and regression gates.  
- **Source controls:** C061-C070, C088  
- **Purpose / scope:** Control-path latency benchmark with PROPOSED thresholds.  
- **Non-goals:** Fleet-scale load testing.  
- **Trust boundary:** n/a  
- **Dependencies:** none  
- **Inputs:** n/a  
- **Outputs:** evidence/benchmark.json  
- **Implementation:** `gap11_control/tests/test_verification.py`  
- **Tests:** `test_verification.BenchmarkTests`  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** verification  
- **Blockers:** BLK-ENV: requires a provisioned multi-node deployment and real observation period; BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned) (threshold approval)

## GAP11-P2-40 — Compatibility matrix  <a id="GAP11-P2-40"></a>
- **Disposition:** DOCUMENTED  
- **Required capability (checklist):** Supported Python/pk_core versions, API schema versions, architectures, drivers, firmware, hypervisors, accelerator families, and providers.  
- **Source controls:** C084, C093  
- **Purpose / scope:** Compatibility matrix.  
- **Non-goals:** n/a  
- **Trust boundary:** n/a  
- **Dependencies:** none  
- **Inputs:** n/a  
- **Outputs:** n/a  
- **Implementation:** `docs/COMPATIBILITY.md`  
- **Tests:** none  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** release  
- **Blockers:** BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/FPGA/NPU) in the build environment (driver/firmware rows untested)

## GAP11-P2-41 — Packaging metadata and dependency pinning  <a id="GAP11-P2-41"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** pyproject/build metadata, explicit pk_core compatibility range, reproducible wheel/sdist or repository packaging, and installation tests.  
- **Source controls:** C031, C040  
- **Purpose / scope:** Package metadata; zero runtime dependencies (stdlib only); pk_core range declared optional.  
- **Non-goals:** Publishing to an index.  
- **Trust boundary:** n/a  
- **Dependencies:** none  
- **Inputs:** n/a  
- **Outputs:** n/a  
- **Implementation:** `pyproject.toml`  
- **Tests:** none  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** release  

## GAP11-P2-42 — CI release gate  <a id="GAP11-P2-42"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Compile, unit, contract, integration, security, fuzz, benchmark, provenance, and artifact verification before release.  
- **Source controls:** C070, C090, C100  
- **Purpose / scope:** CI gate: compile, unit, contract, fuzz, benchmark, manifest verification; exit non-zero on any failure.  
- **Non-goals:** Hosted CI runner.  
- **Trust boundary:** n/a  
- **Dependencies:** none  
- **Inputs:** n/a  
- **Outputs:** n/a  
- **Implementation:** `ci.sh`, `tools/run_checklist.py`  
- **Tests:** none  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** release  
- **Blockers:** BLK-SIGN: release signing keys and custody policy do not exist (provenance stage)

## GAP11-P2-43 — SBOM, signing, and provenance  <a id="GAP11-P2-43"></a>
- **Disposition:** DOCUMENTED  
- **Required capability (checklist):** Signed release artifacts, dependency inventory, source/build attestations, and verification policy.  
- **Source controls:** C045, C094  
- **Purpose / scope:** SBOM + checksums; signing refused without keys.  
- **Non-goals:** n/a  
- **Trust boundary:** n/a  
- **Dependencies:** none  
- **Inputs:** n/a  
- **Outputs:** n/a  
- **Implementation:** `release/SBOM.cdx.json`, `MANIFEST.sha256`  
- **Tests:** none  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** release  
- **Blockers:** BLK-SIGN: release signing keys and custody policy do not exist

## GAP11-P2-44 — Threat model document  <a id="GAP11-P2-44"></a>
- **Disposition:** DOCUMENTED  
- **Required capability (checklist):** Attacker classes, trust boundaries, residual-data threat analysis, stale-controller threats, side-channel assumptions, and mitigations.  
- **Source controls:** C041, C050  
- **Purpose / scope:** Threat model.  
- **Non-goals:** n/a  
- **Trust boundary:** n/a  
- **Dependencies:** none  
- **Inputs:** n/a  
- **Outputs:** n/a  
- **Implementation:** `docs/THREAT_MODEL.md`  
- **Tests:** none  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** governance  
- **Blockers:** BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned)

## GAP11-P2-45 — Architecture Decision Record (ADR)  <a id="GAP11-P2-45"></a>
- **Disposition:** DOCUMENTED  
- **Required capability (checklist):** Approved technology/state-store/API/fencing choices and explicit tradeoffs.  
- **Source controls:** C010  
- **Purpose / scope:** ADR (status PROPOSED).  
- **Non-goals:** n/a  
- **Trust boundary:** n/a  
- **Dependencies:** none  
- **Inputs:** n/a  
- **Outputs:** n/a  
- **Implementation:** `docs/ADR-001-control-plane.md`  
- **Tests:** none  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** governance  
- **Blockers:** BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned)

## GAP11-P2-46 — Named accountable owner and escalation path  <a id="GAP11-P2-46"></a>
- **Disposition:** BLOCKED  
- **Required capability (checklist):** Owner, on-call/escalation route, incident severity policy, and support commitment.  
- **Source controls:** C009, C091, C097  
- **Purpose / scope:** Accountable owner and escalation path.  
- **Non-goals:** n/a  
- **Trust boundary:** n/a  
- **Dependencies:** none  
- **Inputs:** n/a  
- **Outputs:** n/a  
- **Implementation:** `docs/OWNERSHIP.md`  
- **Tests:** none  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** governance  
- **Blockers:** BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned)

## GAP11-P2-47 — Runbooks  <a id="GAP11-P2-47"></a>
- **Disposition:** DOCUMENTED  
- **Required capability (checklist):** Bootstrap, rollout, rollback, emergency disable, store recovery, orphan reconciliation, failed scrub, device replacement, and incident containment.  
- **Source controls:** C092, C095-C097  
- **Purpose / scope:** Runbooks (unexercised).  
- **Non-goals:** n/a  
- **Trust boundary:** n/a  
- **Dependencies:** none  
- **Inputs:** n/a  
- **Outputs:** n/a  
- **Implementation:** `docs/RUNBOOKS.md`  
- **Tests:** none  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** governance  
- **Blockers:** BLK-ENV: requires a provisioned multi-node deployment and real observation period; BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned)

## GAP11-P2-48 — Exception/waiver/deprecation register  <a id="GAP11-P2-48"></a>
- **Disposition:** DOCUMENTED  
- **Required capability (checklist):** Owners, expiry dates, rationale, migration plan, and review cadence.  
- **Source controls:** C098, C099  
- **Purpose / scope:** Exception/waiver register (all entries PROPOSED, owner UNASSIGNED).  
- **Non-goals:** n/a  
- **Trust boundary:** n/a  
- **Dependencies:** none  
- **Inputs:** n/a  
- **Outputs:** n/a  
- **Implementation:** `docs/EXCEPTIONS.json`  
- **Tests:** none  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** governance  
- **Blockers:** BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned)

## GAP11-P2-49 — Source-series MASTER.md artifact  <a id="GAP11-P2-49"></a>
- **Disposition:** BLOCKED  
- **Required capability (checklist):** Restore the authoritative master prompt/workflow source or remove all downstream assumptions that require it.  
- **Source controls:** —  
- **Purpose / scope:** MASTER.md disposition.  
- **Non-goals:** n/a  
- **Trust boundary:** n/a  
- **Dependencies:** none  
- **Inputs:** n/a  
- **Outputs:** n/a  
- **Implementation:** `docs/MASTER_MD_DISPOSITION.md`  
- **Tests:** none  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** governance  
- **Blockers:** BLK-MASTER: the source-series MASTER.md is absent from every supplied artifact; BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned)

## GAP11-P2-50 — Formal production-exit evidence bundle  <a id="GAP11-P2-50"></a>
- **Disposition:** IMPLEMENTED  
- **Required capability (checklist):** Machine-readable acceptance results covering architecture, security, resilience, performance, observability, rollback, ownership, and all unresolved exceptions.  
- **Source controls:** C090, C100  
- **Purpose / scope:** Machine-readable production-exit bundle generated from executed evidence; verdict computed, never asserted.  
- **Non-goals:** Approving the bundle.  
- **Trust boundary:** n/a  
- **Dependencies:** none  
- **Inputs:** n/a  
- **Outputs:** EXIT_BUNDLE.json  
- **Implementation:** `tools/run_checklist.py`, `evidence/EXIT_BUNDLE.json`  
- **Tests:** none  
- **Owner:** UNASSIGNED  
- **Lifecycle template:** governance  
- **Blockers:** BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned)
