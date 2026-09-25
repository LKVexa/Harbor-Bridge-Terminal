"""Single source of truth for the 50 GAP-11 components: disposition, implementation
location, design-record fields, invariants, data, modes, rollout, blockers.

Every generated document (docs/DESIGN_RECORDS.md, REQUIREMENTS.json, DATA_INVENTORY.md,
OPERATING_MODES.md, ROLLOUT.md) is rendered from this file, and the checklist runner
reads the same file, so documents and status cannot drift apart.

Dispositions
  IMPLEMENTED   code + tests in gap11_control/, exercised in this environment
  SIMULATED     adapter/protocol implemented and tested against deterministic fakes;
                the real integration (hardware, PKI, KMS, adjacent GAP service) is BLOCKED
  DOCUMENTED    a governance artifact exists; its approval is BLOCKED on a human
  BLOCKED       cannot be produced here at all (named blocker)
"""
from __future__ import annotations

OWNER = "UNASSIGNED"          # GAP11-P2-46: no accountable owner has been named by the programme

B_HW = "BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/FPGA/NPU) in the build environment"
B_PKI = "BLK-PKI: no mTLS PKI / SPIFFE issuer / GAP-06 attestation service available"
B_KMS = "BLK-KMS: no KMS/HSM available; local SecretProvider is a stand-in"
B_HUMAN = "BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned)"
B_ENV = "BLK-ENV: requires a provisioned multi-node deployment and real observation period"
B_ADJ = "BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate"
B_SIGN = "BLK-SIGN: release signing keys and custody policy do not exist"
B_MASTER = "BLK-MASTER: the source-series MASTER.md is absent from every supplied artifact"

STATE = dict(template="state", modes={"startup": "recover store from snapshot+WAL; refuse mutations until leader", "steady": "all ops",
             "degraded": "store read-only / not leader: reads only, mutations refused with typed code",
             "recovery": "reconcile() before serving; SCRUBBING->QUARANTINED", "maintenance": "freeze(): reads only",
             "shutdown": "step_down(); in-flight commit either fsynced or discarded"})
HW = dict(template="hardware", modes={"startup": "collect inventory; unknown vendor -> refused", "steady": "periodic collect + diff",
          "degraded": "provider outage => devices UNKNOWN, never removed", "recovery": "reappearing device -> QUARANTINED",
          "maintenance": "drain before partition reconfigure", "shutdown": "no privileged op left without evidence record"})
SEC = dict(template="security", modes={"startup": "keyring loaded from secret refs; missing key -> not ready", "steady": "verify every call",
           "degraded": "identity/policy/KMS outage -> privileged ops fail closed", "recovery": "live key rotation, no restart",
           "maintenance": "emergency revoke via Keyring.retire", "shutdown": "nonce cache discarded (window bounded)"})
IFACE = dict(template="interface", modes={"startup": "bind loopback only (plaintext)", "steady": "bounded in-flight",
             "degraded": "OVERLOADED / NOT_LEADER typed retryable errors", "recovery": "clients retry with same request_id",
             "maintenance": "MAINTENANCE_MODE for mutations", "shutdown": "server.shutdown(); no half-applied mutation"})
SCHED = dict(template="scheduler", modes={"startup": "pure functions; no state", "steady": "deterministic decisions",
             "degraded": "missing thermal/health input -> device inadmissible", "recovery": "n/a (stateless)",
             "maintenance": "drained devices excluded", "shutdown": "n/a"})
VERIF = dict(template="verification", modes={"startup": "hermetic temp dirs", "steady": "tools/run_checklist.py",
             "degraded": "missing lane reported NOT RUN, never PASS", "recovery": "rerun is idempotent",
             "maintenance": "n/a", "shutdown": "evidence archived under evidence/"})
TEL = dict(template="telemetry", modes={"startup": "keyring must have an active audit key", "steady": "bounded buffers",
           "degraded": "sink failure counted as dropped, control path unaffected", "recovery": "ledger verified on open",
           "maintenance": "n/a", "shutdown": "ledger fsynced per append"})
CFG = dict(template="config", modes={"startup": "built-in secure defaults", "steady": "validated layered config",
           "degraded": "activation hook failure -> previous config kept", "recovery": "rollback()",
           "maintenance": "freeze()", "shutdown": "n/a"})
REL = dict(template="release", modes={"startup": "n/a", "steady": "ci.sh", "degraded": "missing signer -> release refused",
           "recovery": "rebuild from source revision", "maintenance": "n/a", "shutdown": "n/a"})
GOV = dict(template="governance", modes={"startup": "n/a", "steady": "reviewed on cadence", "degraded": "expired exception -> gate fails",
           "recovery": "n/a", "maintenance": "n/a", "shutdown": "n/a"})


def C(cid, disp, modules, tests, purpose, non_goals, trust, deps, inputs, outputs, data, invariants, telemetry, rollout,
      blockers=(), base=None):
    return {"id": cid, "disposition": disp, "modules": modules, "tests": tests, "purpose": purpose, "non_goals": non_goals,
            "trust_boundary": trust, "dependencies": deps, "inputs": inputs, "outputs": outputs, "data": data,
            "invariants": invariants, "telemetry": telemetry, "rollout": rollout, "blockers": list(blockers),
            "owner": OWNER, **(base or {})}


D_LEASE = [("lease/<id>", "store WAL", "integrity: sha256 per record; confidentiality: tenant id is sensitive", "until snapshot; usage/ kept for accounting", "schema field in record; WAL line format v1")]
D_DEV = [("dev/<id>", "inventory adapter -> store", "integrity sha256; security_tenant sensitive", "life of device", "additive fields only")]

COMPONENTS = [
    C("GAP11-P0-01", "IMPLEMENTED", ["gap11_control/store.py"], ["test_state.StoreTests"],
      "Durable, crash-consistent, CAS-only persistence of leases, device security state, idempotency keys and leadership.",
      "Replication/quorum (single-writer WAL; see BLK-ENV); schema-less queries.", "Process-local file owned by the controller account.",
      ["filesystem with fsync"], ["commit(ops, pre, prov, fence)"], ["revision, get/scan"], D_LEASE + D_DEV,
      ["INV-STORE-1 a commit is visible iff its WAL line is complete and checksummed", "INV-STORE-2 every write is CAS on explicit revisions",
       "INV-STORE-3 corruption anywhere but a torn tail refuses to open"], ["STORE_CORRUPT", "STORE_UNAVAILABLE", "STALE_REVISION"],
      "WAL format v1; readers skip records <= snapshot revision; a v2 format must be read-compatible for one release.", [B_ENV + " (quorum/replica restore paths)"], STATE),
    C("GAP11-P0-02", "IMPLEMENTED", ["gap11_control/store.py", "gap11_control/election.py"], ["test_state.FencingElectionTests", "test_verification.SplitBrainTests"],
      "Storage-side fencing: every controller mutation carries the leader epoch; the store rejects lower tokens.",
      "Fencing of external side-effects the store does not mediate (vendor calls must re-check).", "Store is the fence authority.",
      ["LeaderElector epoch"], ["fence=(resource, token)"], ["STALE_FENCE refusals"], [("__fence__/controller", "store", "integrity", "forever", "monotonic int")],
      ["INV-FENCE-1 token for a resource never decreases", "INV-FENCE-2 a write with a lower token is refused atomically"], ["STALE_FENCE"],
      "Enable by default; there is no unfenced mode.", [], STATE),
    C("GAP11-P0-03", "IMPLEMENTED", ["gap11_control/election.py"], ["test_state.FencingElectionTests"],
      "Lease-based leader election on the durable store; epoch = fencing token; safety margin before local expiry.",
      "Consensus across stores (single store); leader for other GAP subsystems.", "Controllers trust only the store record.",
      ["store", "monotonic clock"], ["try_acquire/renew/step_down"], ["epoch, is_leader"], [("ctl/leader", "store", "integrity", "overwritten", "fields additive")],
      ["INV-LEAD-1 at most one controller believes it leads outside its safety margin", "INV-LEAD-2 epochs strictly increase across holders"],
      ["NOT_LEADER", "leader_change"], "Mixed-version controllers must share the ctl/leader format.", [B_ENV + " (multi-node failover observation)"], STATE),
    C("GAP11-P0-04", "IMPLEMENTED", ["gap11_control/controller.py"], ["test_state.TTLAndReconcileTests"],
      "Lease TTL on the monotonic clock, heartbeats, and deterministic orphan reconciliation that is destructive only on unambiguous evidence.",
      "Deciding workload liveness (supplied by the lifecycle system).", "Liveness input is trusted as reported by the lifecycle hook.",
      ["liveness oracle"], ["heartbeat, reconcile"], ["report {reclaimed, renewed, suspect, quarantined}"], D_LEASE,
      ["INV-TTL-1 unknown liveness never reclaims before grace", "INV-TTL-2 reclaim leaves the device DIRTY"], ["AMBIGUOUS_EVIDENCE", "LEASE_EXPIRED"],
      "lease_ttl_s / lease_grace_s are config; shortening TTL is a risky change requiring canary.", [], STATE),
    C("GAP11-P0-05", "IMPLEMENTED", ["gap11_control/controller.py", "gap11_control/service.py"], ["test_state.IdempotencyTests"],
      "Durable request-id dedup committed in the same transaction as the mutation; conflicting replays refused.",
      "Global dedup across tenants (keys are tenant-scoped at the boundary).", "request_id is client-chosen, namespaced by authenticated tenant.",
      ["request_id + payload"], ["prior result or new mutation"], ["DUPLICATE_REQUEST / IDEMPOTENCY_CONFLICT"], [("idem/<tenant>:<rid>", "store", "integrity", "idempotency_retention_s", "payload digest sha256")],
      ["INV-IDEM-1 same id + same payload -> same result, no second effect", "INV-IDEM-2 same id + different payload -> refused"],
      ["IDEMPOTENCY_CONFLICT", "DUPLICATE_REQUEST"], "Retention is config; lowering it below client retry horizons is unsafe.", [], STATE),
    C("GAP11-P0-06", "SIMULATED", ["gap11_control/hardware.py"], ["test_hardware.InventoryTests"],
      "Vendor-neutral canonical device model; normalisation; stable identity; diffing; bounded retries; evidence.",
      "Driver installation; firmware update.", "Vendor SDK runs in a privileged node agent; the controller consumes typed records only.",
      ["vendor providers (simulated)"], ["collect()"], ["canonical records + PK_INVENTORY_EVIDENCE/1"], D_DEV,
      ["INV-INV-1 identity keyed by stable_id, never PCI address", "INV-INV-2 provider outage never implies removal"], ["DEADLINE_EXCEEDED", "SCHEMA_INVALID"],
      "New vendor = new normalize() branch behind a feature gate.", [B_HW], HW),
    C("GAP11-P0-07", "SIMULATED", ["gap11_control/hardware.py"], ["test_hardware.PartitionTopologyTests"],
      "Alternative partition layouts per device model, mutually exclusive; reconfigure only when drained; residual-capacity scoring.",
      "Executing MIG/SR-IOV commands on real devices.", "Reconfigure is a privileged node-agent operation.",
      ["profiles", "lease count"], ["reconfigure(profile)"], ["declared partitions"], D_DEV,
      ["INV-PART-1 a profile never oversubscribes memory", "INV-PART-2 no reconfigure with active leases"], ["ILLEGAL_TRANSITION", "CONFIG_INVALID"],
      "Profiles are data; adding one is additive.", [B_HW], HW),
    C("GAP11-P0-08", "SIMULATED", ["gap11_control/hardware.py", "gap11_control/controller.py"], ["test_hardware.ScrubTests"],
      "reset -> zeroize -> independent verify with deadline and bounded retry; any doubt quarantines.",
      "Proving zeroization of vendor-internal state the SDK does not expose.", "Scrub backend runs privileged on the node.",
      ["device record"], ["PK_SCRUB_EVIDENCE/1"], ["CLEAN or QUARANTINED"], D_DEV,
      ["INV-SCRUB-1 a device crosses tenants only after a verified scrub", "INV-SCRUB-2 timeout/partial/unknown -> QUARANTINED"],
      ["SCRUB_FAILED", "SCRUB_TIMEOUT"], "No mode disables scrub (dangerous_skip_scrub is forbidden by schema).", [B_HW], HW),
    C("GAP11-P0-09", "SIMULATED", ["gap11_control/security.py"], ["test_security.AttestationTests"],
      "Bind device stable_id, capability digest, driver/firmware and node identity to a signed, fresh quote.",
      "Hardware root-of-trust measurement (GAP-06).", "Quote signer = node attestation key (simulated keyring).",
      ["inventory record", "quote"], ["verify()"], ["attested / ATTESTATION_INVALID"], [("attestation quotes", "GAP-06", "integrity", "max_age_s", "claims additive")],
      ["INV-ATT-1 capability used for placement equals the attested digest"], ["ATTESTATION_INVALID"], "Firmware allowlist is config.", [B_PKI, B_ADJ], SEC),
    C("GAP11-P0-10", "SIMULATED", ["gap11_control/security.py", "gap11_control/service.py"], ["test_security.AuthnTests"],
      "Workload-identity credential verification: MAC, audience, expiry, skew, nonce replay window, live key rotation.",
      "mTLS termination (needs PKI).", "Only verified claims (sub, ten, knd, scp) reach authorization.",
      ["credential"], ["Principal"], ["UNAUTHENTICATED / REPLAY_DETECTED"], [("nonce cache", "memory", "integrity", "nonce_window_s", "n/a")],
      ["INV-AUTHN-1 no state change without a verified principal"], ["UNAUTHENTICATED", "REPLAY_DETECTED"], "Key rotation overlap then retire.", [B_PKI], SEC),
    C("GAP11-P0-11", "IMPLEMENTED", ["gap11_control/security.py", "gap11_control/service.py"], ["test_security.AuthzTests"],
      "Deny-by-default capability policy with operator-only scopes and tenant binding from the authenticated principal.",
      "Policy authoring UI.", "Policy rules are configuration under audit.", ["Principal", "action", "resource"], ["decide()"], ["allow/deny + reason"], [],
      ["INV-AUTHZ-1 tenant comes from the principal, never the body", "INV-AUTHZ-2 no rule -> deny"], ["POLICY_DENIED"], "Rules additive; removal is a breaking change.", [], SEC),
    C("GAP11-P0-12", "IMPLEMENTED", ["gap11_control/wire.py", "gap11_control/schemas/"], ["test_wire.SchemaTests"],
      "Versioned closed request schemas, open response schemas, one error envelope, limits before logic.",
      "Protobuf/WIT encodings (JSON only).", "Schema validation is the first gate after authentication.",
      ["bytes"], ["decode()"], ["typed dict or SCHEMA_INVALID/MESSAGE_TOO_LARGE"], [],
      ["INV-WIRE-1 no business logic on an unvalidated message"], ["SCHEMA_INVALID", "MESSAGE_TOO_LARGE"], "See docs/COMPATIBILITY.md.", [], IFACE),
    C("GAP11-P0-13", "IMPLEMENTED", ["gap11_control/service.py"], ["test_wire.TransportTests"],
      "Transport-independent request pipeline + loopback HTTP binding with in-flight bound, deadlines, size limits.",
      "Public network exposure without mTLS (refused).", "Loopback only in this build.", ["HTTP"], ["handle()"], ["JSON + status"], [],
      ["INV-SVC-1 bounded in-flight; excess -> OVERLOADED"], ["OVERLOADED", "DEADLINE_EXCEEDED"], "Feature-gated behind mTLS termination for non-loopback.", [B_PKI + " (non-loopback binding)"], IFACE),
    C("GAP11-P0-14", "IMPLEMENTED", ["gap11_control/scheduler.py"], ["test_scheduler"],
      "Quotas with secure default, bounded fair queue with aging (starvation bound 2*aging_s).", "Billing.", "Quota book is config.",
      ["tenant, active leases"], ["check(), FairQueue"], ["QUOTA_EXCEEDED / OVERLOADED"], [],
      ["INV-Q-1 no quota -> no access", "INV-Q-2 any queued request is served within 2*aging_s of reaching the head class"], ["QUOTA_EXCEEDED", "OVERLOADED"], "Caps are config.", [], SCHED),
    C("GAP11-P0-15", "IMPLEMENTED", ["gap11_control/controller.py"], ["test_state.LifecycleAndHotplugTests"],
      "Authoritative workload start/exit/crash/evict/restart hooks mapped to heartbeat/release/reclaim, idempotent by event id.",
      "Running workloads.", "Lifecycle events carry the tenant and are tenant-checked.", ["lifecycle events"], ["on_workload_event"], ["release/heartbeat results"], D_LEASE,
      ["INV-LC-1 a late event never resurrects or double-releases a lease"], ["ILLEGAL_TRANSITION", "LEASE_NOT_FOUND"], "Event schema additive.", [B_ADJ + " (real workload runtime)"], STATE),
    C("GAP11-P0-16", "IMPLEMENTED", ["gap11_control/tests/test_verification.py"], ["test_verification.SplitBrainTests"],
      "Multi-controller fault tests: partition, delayed messages, failover, replay, barrier collisions.", "Network-level chaos (needs a cluster).",
      "Tests run against one shared durable store.", ["store"], ["test results"], ["evidence/"], [],
      ["INV-SB-1 at most one lease per whole device under any interleaving"], ["STALE_FENCE"], "Runs in ci.sh.", [B_ENV + " (real network partitions)"], VERIF),
    C("GAP11-P1-17", "IMPLEMENTED", ["gap11_control/scheduler.py", "gap11_control/controller.py"], ["test_scheduler.TopologyGangTests"],
      "Fabric-domain gang candidates and all-or-nothing multi-device reservation in one transaction.", "NUMA/PCIe distance matrix from hardware.",
      "Topology comes from attested inventory.", ["topology"], ["allocate_gang"], ["PK_ACCELERATOR_GANG/1"], D_LEASE,
      ["INV-GANG-1 no partial gang is ever persisted"], ["CAPACITY_EXHAUSTED"], "feature_gates.gang_allocation default off.", [B_HW + " (real topology)"], SCHED),
    C("GAP11-P1-18", "IMPLEMENTED", ["gap11_control/scheduler.py", "gap11_control/hardware.py"], ["test_scheduler.FragmentationTests"],
      "Fragmentation metric and smallest-sufficient-slice placement preferring partially used devices.", "Live migration/defragmentation.",
      "n/a", ["devices, leases"], ["fragmentation(), place_partition()"], ["unusable_gb ratio"], [], ["INV-FRAG-1 slice placement never lands on a whole-device lease"],
      [], "Scoring change = canary.", [], SCHED),
    C("GAP11-P1-19", "SIMULATED", ["gap11_control/hardware.py"], ["test_hardware.ThermalHealthTests"],
      "GAP-10 adapter: stale/missing/hot readings make a device inadmissible.", "Setting power caps.", "GAP-10 readings trusted if fresh.",
      ["readings"], ["admissible()"], ["thermal_ok flag"], [], ["INV-THERM-1 missing or stale reading => not admissible"], ["THERMAL_UNAVAILABLE"], "Thresholds are config.", [B_ADJ], HW),
    C("GAP11-P1-20", "SIMULATED", ["gap11_control/hardware.py"], ["test_hardware.ThermalHealthTests"],
      "RAS classification (uncorrectable -> failed, reset storms, correctable thresholds) driving quarantine.", "Vendor-specific Xid catalogues.",
      "RAS signals from node agent.", ["RAS signals"], ["observe()"], ["ok/degraded/failed"], [], ["INV-RAS-1 failed health => QUARANTINED, excluded"], ["HARDWARE_FAULT"],
      "Signal catalogue additive.", [B_HW], HW),
    C("GAP11-P1-21", "IMPLEMENTED", ["gap11_control/controller.py", "gap11_control/hardware.py"], ["test_state.LifecycleAndHotplugTests"],
      "Device disappearance marks leases SUSPECT; reappearance quarantines; capability change under lease drains.", "Physical replacement workflow.",
      "Inventory diff trusted only for vendors whose provider answered.", ["inventory diff"], ["mark_missing, upsert_device"], ["state changes"], D_DEV,
      ["INV-HP-1 a returning device is never directly placeable"], ["DEVICE_MISSING", "AMBIGUOUS_EVIDENCE"], "n/a", [], STATE),
    C("GAP11-P1-22", "IMPLEMENTED", ["gap11_control/scheduler.py"], ["test_scheduler.PreemptionTests"],
      "Victim selection policy (strictly lower priority, min runtime, non-preemptible, budget).", "Checkpoint/eviction execution.",
      "n/a", ["leases"], ["choose_victims()"], ["victims"], [], ["INV-PRE-1 never preempt equal or higher priority"], [], "feature_gates.preemption default off.", [B_ADJ + " (eviction handoff)"], SCHED),
    C("GAP11-P1-23", "IMPLEMENTED", ["gap11_control/scheduler.py"], ["test_scheduler.ConstraintTests"],
      "Hard constraints in fixed precedence, soft scoring after, per-device rejection reasons.", "Cost model data.", "n/a",
      ["request, devices"], ["decide()"], ["Decision"], [], ["INV-CON-1 scoring never overrides a hard constraint"], ["CONSTRAINT_UNSATISFIED"], "Precedence change = ADR.", [], SCHED),
    C("GAP11-P1-24", "IMPLEMENTED", ["gap11_control/observability.py"], ["test_observability.AuditLedgerTests"],
      "Hash-chained, HMAC-signed, redacted audit ledger with external head witness.", "WORM storage.", "Audit key is separate from authn keys in production.",
      ["events"], ["append/verify/head"], ["audit.jsonl"], [("audit.jsonl", "controller", "integrity HMAC; redacted", "policy: 400 days (PROPOSED)", "entry format v1")],
      ["INV-AUD-1 any edit/reorder/delete fails verify; truncation fails against witness"], ["STORE_CORRUPT"], "n/a", [B_KMS], TEL),
    C("GAP11-P1-25", "IMPLEMENTED", ["gap11_control/observability.py"], ["test_observability.MetricsLogsTraceTests"],
      "Prometheus exposition with fixed label budget; latency histograms; refusal classes.", "Metrics backend.", "No tenant/lease/device ids in labels.",
      ["events"], ["expose()"], ["text/plain"], [], ["INV-MET-1 label values come from closed sets"], [], "n/a", [B_ENV + " (live scrape + retention)"], TEL),
    C("GAP11-P1-26", "IMPLEMENTED", ["gap11_control/observability.py"], ["test_observability.MetricsLogsTraceTests"],
      "Structured UTC JSON logs with redaction and debug sampling; W3C trace continuation.", "Trace backend.", "n/a",
      ["fields"], ["log()"], ["JSON lines"], [], ["INV-LOG-1 secrets never reach a sink"], [], "n/a", [B_ENV], TEL),
    C("GAP11-P1-27", "IMPLEMENTED", ["gap11_control/observability.py"], ["test_observability.HealthAlertTests"],
      "Health/readiness: version, config digest, role, epoch, store revision, dependencies, reconcile lag; redacted explain.", "UI.", "n/a",
      ["component state"], ["health_report()"], ["PK_HEALTH/1"], [], ["INV-HEALTH-1 not leader or store read-only => not ready"], [], "n/a", [], TEL),
    C("GAP11-P1-28", "DOCUMENTED", ["gap11_control/observability.py", "docs/DASHBOARDS.md"], ["test_observability.HealthAlertTests"],
      "Alert rules with severity, class, expression, dedupe and runbook; dashboard specification.", "Rendering dashboards.", "n/a",
      ["refusal-class counts"], ["evaluate_alerts()"], ["fired alerts"], [], ["INV-ALERT-1 every rule names a runbook"], [], "n/a", [B_ENV + " (deployed dashboards/alert routing)"], TEL),
    C("GAP11-P1-29", "IMPLEMENTED", ["gap11_control/config.py"], ["test_observability.ConfigTests"],
      "Typed config schema, layered precedence with provenance, validate-then-atomic-activate, last-known-good rollback.", "Remote config service.",
      "Config writes are privileged and audited.", ["layers"], ["apply/rollback"], ["effective config + digest"], [("config layers", "operator", "integrity digest", "last-known-good kept", "schema keys additive")],
      ["INV-CFG-1 an invalid candidate is never partially active"], ["CONFIG_INVALID"], "Keys additive; removal = major.", [], CFG),
    C("GAP11-P1-30", "SIMULATED", ["gap11_control/security.py"], ["test_security.SecretsTests"],
      "Secret references only; pluggable backend; fail closed on outage; keyring rotation/retire.", "Running a KMS.", "KMS is the root of secret trust.",
      ["secretref://"], ["resolve()"], ["bytes"], [("keys", "KMS", "confidentiality", "rotation policy (PROPOSED 90d)", "kid versioning")],
      ["INV-SEC-1 a secret value never appears in config, logs or audit"], ["DEPENDENCY_UNAVAILABLE"], "n/a", [B_KMS], SEC),
    C("GAP11-P1-31", "IMPLEMENTED", ["gap11_control/controller.py"], ["test_observability.UsageAccountingTests"],
      "Durable per-lease usage records committed with the allocation/release transaction.", "Chargeback pricing.", "n/a",
      ["leases"], ["usage_records()"], ["usage/<lease>"], [("usage/<lease>", "store", "integrity", "PROPOSED 400 days", "additive")],
      ["INV-USE-1 every lease has exactly one usage record, closed on release/reclaim"], [], "n/a", [], TEL),
    C("GAP11-P1-32", "IMPLEMENTED", ["gap11_control/controller.py"], ["test_observability.ConfigTests"],
      "Operator drain, freeze (maintenance), quarantine, health override — all fenced, provenance-recorded and audited.", "Unquarantine without scrub (does not exist by design).",
      "Operator scopes are operator-only in policy.", ["operator requests"], ["set_draining/freeze/quarantine"], ["state changes"], D_DEV,
      ["INV-OP-1 the only exit from QUARANTINED is a verified scrub"], ["MAINTENANCE_MODE"], "n/a", [], CFG),
    C("GAP11-P2-33", "IMPLEMENTED", ["gap11_control/tests/fixtures/"], ["test_wire.SchemaTests"], "Golden request/response/error fixtures.", "Binary encodings.", "n/a",
      [], [], ["fixtures/*.json"], [], ["INV-FIX-1 every fixture decodes to its expected outcome"], [], "n/a", [], VERIF),
    C("GAP11-P2-34", "BLOCKED", [], [], "Adjacent-layer integration tests against GAP-02/06/09/10 and the workload runtime.", "n/a", "n/a", [], [], [], [], [], [], "n/a", [B_ADJ], VERIF),
    C("GAP11-P2-35", "IMPLEMENTED", ["gap11_control/tests/test_wire.py", "gap11_control/tests/test_scheduler.py"], ["test_wire.SchemaTests", "test_scheduler.AdversarialTests"],
      "Seeded mutation fuzzing of decoders and seeded property tests over allocator sequences.", "Coverage-guided fuzzing (no atheris/hypothesis in the stdlib-only build).", "n/a",
      [], [], [], [], ["INV-FUZZ-1 decoder raises only typed ControlError"], [], "n/a", [], VERIF),
    C("GAP11-P2-36", "IMPLEMENTED", ["gap11_control/tests/test_verification.py"], ["test_verification.SplitBrainTests"], "Barrier-synchronised collision and soak tests.", "Long-duration soak (hours).", "n/a",
      [], [], [], [], ["INV-CONC-1 invariants hold under every tested interleaving"], [], "n/a", [B_ENV + " (multi-hour soak)"], VERIF),
    C("GAP11-P2-37", "IMPLEMENTED", ["gap11_control/tests/test_security.py"], ["test_security"], "Adversarial suite: forged, replayed, expired, cross-tenant, confused deputy, escalation, tampered quotes/audit.",
      "Side-channel testing (hardware).", "n/a", [], [], [], [], ["INV-ADV-1 every adversarial case is refused with a typed code"], [], "n/a", [B_HW + " (side channels)"], VERIF),
    C("GAP11-P2-38", "IMPLEMENTED", ["gap11_control/tests/test_verification.py"], ["test_verification.FaultMatrixTests"], "Fault matrix: crash at every write point, dependency outages, ENOSPC, corruption.",
      "Node loss / real network partitions.", "n/a", [], [], [], [], ["INV-FAULT-1 retry after restart converges to exactly one effect"], [], "n/a", [B_ENV], VERIF),
    C("GAP11-P2-39", "IMPLEMENTED", ["gap11_control/tests/test_verification.py"], ["test_verification.BenchmarkTests"], "Control-path latency benchmark with PROPOSED thresholds.",
      "Fleet-scale load testing.", "n/a", [], [], ["evidence/benchmark.json"], [], [], [], "Thresholds unapproved (owner decision).", [B_ENV, B_HUMAN + " (threshold approval)"], VERIF),
    C("GAP11-P2-40", "DOCUMENTED", ["docs/COMPATIBILITY.md"], [], "Compatibility matrix.", "n/a", "n/a", [], [], [], [], [], [], "n/a", [B_HW + " (driver/firmware rows untested)"], REL),
    C("GAP11-P2-41", "IMPLEMENTED", ["pyproject.toml"], [], "Package metadata; zero runtime dependencies (stdlib only); pk_core range declared optional.", "Publishing to an index.", "n/a",
      [], [], [], [], [], [], "n/a", [], REL),
    C("GAP11-P2-42", "IMPLEMENTED", ["ci.sh", "tools/run_checklist.py"], [], "CI gate: compile, unit, contract, fuzz, benchmark, manifest verification; exit non-zero on any failure.",
      "Hosted CI runner.", "n/a", [], [], [], [], [], [], "n/a", [B_SIGN + " (provenance stage)"], REL),
    C("GAP11-P2-43", "DOCUMENTED", ["release/SBOM.cdx.json", "MANIFEST.sha256"], [], "SBOM + checksums; signing refused without keys.", "n/a", "n/a",
      [], [], [], [], [], [], "n/a", [B_SIGN], REL),
    C("GAP11-P2-44", "DOCUMENTED", ["docs/THREAT_MODEL.md"], [], "Threat model.", "n/a", "n/a", [], [], [], [], [], [], "n/a", [B_HUMAN], GOV),
    C("GAP11-P2-45", "DOCUMENTED", ["docs/ADR-001-control-plane.md"], [], "ADR (status PROPOSED).", "n/a", "n/a", [], [], [], [], [], [], "n/a", [B_HUMAN], GOV),
    C("GAP11-P2-46", "BLOCKED", ["docs/OWNERSHIP.md"], [], "Accountable owner and escalation path.", "n/a", "n/a", [], [], [], [], [], [], "n/a", [B_HUMAN], GOV),
    C("GAP11-P2-47", "DOCUMENTED", ["docs/RUNBOOKS.md"], [], "Runbooks (unexercised).", "n/a", "n/a", [], [], [], [], [], [], "n/a", [B_ENV, B_HUMAN], GOV),
    C("GAP11-P2-48", "DOCUMENTED", ["docs/EXCEPTIONS.json"], [], "Exception/waiver register (all entries PROPOSED, owner UNASSIGNED).", "n/a", "n/a", [], [], [], [], [], [], "n/a", [B_HUMAN], GOV),
    C("GAP11-P2-49", "BLOCKED", ["docs/MASTER_MD_DISPOSITION.md"], [], "MASTER.md disposition.", "n/a", "n/a", [], [], [], [], [], [], "n/a", [B_MASTER, B_HUMAN], GOV),
    C("GAP11-P2-50", "IMPLEMENTED", ["tools/run_checklist.py", "evidence/EXIT_BUNDLE.json"], [], "Machine-readable production-exit bundle generated from executed evidence; verdict computed, never asserted.",
      "Approving the bundle.", "n/a", [], [], ["EXIT_BUNDLE.json"], [], ["INV-EXIT-1 any open P0 item or unapproved exception => NO_GO"], [], "n/a", [B_HUMAN], GOV),
]

if len(COMPONENTS) != 50 or len({c["id"] for c in COMPONENTS}) != 50:
    raise RuntimeError("registry must hold exactly 50 unique components")
