"""Per-item execution status for the INV-71 v4.2.0 production remediation checklist.

This is the remediation pass's own claim about every checklist line, written as
data so the evidence builder can check it (every cited path must exist, every
cited test must exist and pass) and the gate can consume it.

Status vocabulary (never DONE - DONE needs independent review and the real
production path, and neither exists):

  I  IMPLEMENTED_UNREVIEWED  built and tested at reference scope; awaits independent review
  P  PARTIAL                 some of the line is done; the note says what is not
  O  OPEN                    doable at reference scope, not done in this pass
  B  BLOCKED                 needs a human authority, real infrastructure, or an external artifact
"""
from __future__ import annotations

STATUS = {"I": "IMPLEMENTED_UNREVIEWED", "P": "PARTIAL", "O": "OPEN", "B": "BLOCKED"}

# Evidence cited per control (paths relative to the package root; tests are
# discovered separately from "[Cxxx]" tags in test docstrings).
E = {
    "C009": ["docs/OWNERSHIP.md", "governance/raci.json", "control/auth.py", "docs/generated/AUTHZ.md"],
    "C010": ["docs/ADR-0001-heavy-agent-sandbox.md", "governance/approvals/README.md"],
    "C011": ["governance/requirements.json", "docs/generated/REQUIREMENTS.md", "docs/generated/OPERATIONS.md"],
    "C012": ["control/qualify.py", "docs/generated/PROFILES.md", "docs/generated/COMPATIBILITY.md"],
    "C013": ["docs/ARCHITECTURE.md", "governance/perf_thresholds.json"],
    "C014": ["control/errors.py", "docs/generated/ERROR_CODES.md", "docs/ARCHITECTURE.md"],
    "C015": ["control/lifecycle.py", "docs/generated/LIFECYCLE.md"],
    "C016": ["control/compat.py", "docs/generated/COMPATIBILITY.md", "schemas/PK_HEAVYBOX_EGRESS_v2.schema.json"],
    "C017": ["control/config.py", "control/resilience.py", "control/runtime_plan.py", "docs/generated/CONFIGURATION.md"],
    "C018": ["docs/ARCHITECTURE.md", "control/resilience.py", "control/qualify.py"],
    "C019": ["control/config.py", "docs/ARCHITECTURE.md"],
    "C020": ["tools/build_evidence.py", "governance/checklist_status.py", "evidence/traceability.json"],
    "C021": ["docs/ARCHITECTURE.md", "control/runtime_plan.py"],
    "C022": ["schemas/PK_HEAVYBOX_SESSION_v2.schema.json", "schemas/PK_HEAVYBOX_ERROR_v1.schema.json", "schemas/PK_HEAVYBOX_STATUS_v1.schema.json", "control/config.py", "fixtures/MANIFEST.json"],
    "C023": ["docs/SECURITY_DESIGN.md", "control/auth.py"],
    "C024": ["control/auth.py", "docs/generated/AUTHZ.md"],
    "C025": ["control/resilience.py", "docs/generated/OPERATIONS.md", "docs/ARCHITECTURE.md"],
    "C026": ["control/errors.py", "docs/generated/ERROR_CODES.md", "schemas/PK_HEAVYBOX_ERROR_v1.schema.json"],
    "C027": ["control/compat.py", "docs/ARCHITECTURE.md"],
    "C028": ["control/config.py", "control/auth.py", "control/resilience.py", "tools/fuzz.py"],
    "C029": ["tools/make_fixtures.py", "fixtures/MANIFEST.json", "fixtures/valid/adjacent_harness.json"],
    "C030": ["tools/make_fixtures.py", "fixtures/valid/adjacent_harness.json"],
    "C031": ["artifacts/approved-manifest.json", "control/artifacts.py", "control/qualify.py"],
    "C032": ["control/artifacts.py", "control/runtime_plan.py", "docs/ARCHITECTURE.md"],
    "C033": ["control/config.py", "docs/generated/CONFIGURATION.md", "schemas/PK_HEAVYBOX_CONFIG_v1.schema.json"],
    "C034": ["control/config.py"],
    "C035": ["control/config.py", "docs/generated/CONFIGURATION.md"],
    "C036": ["control/config.py", "control/audit_log.py"],
    "C037": ["control/config.py"],
    "C038": ["control/config.py", "docs/OPERATIONS.md"],
    "C039": ["docs/SECURITY_DESIGN.md", "control/audit_log.py", "control/errors.py"],
    "C040": ["control/qualify.py", "docs/OPERATIONS.md", "control/artifacts.py"],
    "C042": ["docs/SECURITY_DESIGN.md", "control/runtime_plan.py", "control/auth.py"],
    "C043": ["control/runtime_plan.py", "control/config.py", "docs/SECURITY_DESIGN.md"],
    "C044": ["docs/SECURITY_DESIGN.md", "control/artifacts.py", "control/auth.py"],
    "C045": ["control/artifacts.py", "evidence/sbom.cdx.json", "evidence/provenance.json"],
    "C046": ["control/runtime_plan.py", "docs/SECURITY_DESIGN.md"],
    "C047": ["docs/SECURITY_DESIGN.md"],
    "C048": ["control/resilience.py", "docs/SECURITY_DESIGN.md", "docs/generated/OPERATIONS.md"],
    "C049": ["control/audit_log.py"],
    "C050": ["tools/fuzz.py", "docs/THREAT_MODEL.md"],
    "C051": ["governance/failure_matrix.json", "docs/generated/FAILURE_MATRIX.md"],
    "C052": ["control/lifecycle.py", "control/controller.py", "control/resilience.py"],
    "C053": ["control/resilience.py", "control/errors.py"],
    "C054": ["control/resilience.py"],
    "C055": ["control/lifecycle.py", "docs/ARCHITECTURE.md"],
    "C056": ["control/resilience.py", "control/controller.py", "docs/ARCHITECTURE.md"],
    "C057": ["control/controller.py", "control/runtime_plan.py", "docs/generated/LIFECYCLE.md"],
    "C058": ["control/lifecycle.py", "control/resilience.py", "control/config.py"],
    "C059": ["control/controller.py", "control/lifecycle.py", "control/auth.py"],
    "C060": ["tests/test_control_faults.py", "governance/failure_matrix.json"],
    "C061": ["tools/bench.py", "evidence/performance/bench.json"],
    "C062": ["governance/perf_thresholds.json", "tools/bench.py"],
    "C063": ["tools/bench.py"],
    "C064": ["docs/PRODUCTION_BOUNDARY.md"],
    "C065": ["tools/bench.py", "docs/PRODUCTION_BOUNDARY.md"],
    "C066": ["control/egress.py", "docs/PRODUCTION_BOUNDARY.md"],
    "C067": ["control/telemetry.py", "control/egress.py", "control/audit_log.py", "control/resilience.py", "control/controller.py"],
    "C068": ["docs/PRODUCTION_BOUNDARY.md"],
    "C069": ["control/resilience.py", "control/telemetry.py"],
    "C070": ["tools/bench.py", "governance/perf_thresholds.json"],
    "C071": ["control/controller.py", "schemas/PK_HEAVYBOX_STATUS_v1.schema.json"],
    "C072": ["control/telemetry.py", "docs/generated/METRICS.md"],
    "C073": ["control/audit_log.py", "control/telemetry.py"],
    "C074": ["control/telemetry.py"],
    "C075": ["control/telemetry.py", "docs/OBSERVABILITY_AND_TESTING.md"],
    "C076": ["control/telemetry.py", "control/controller.py"],
    "C077": ["control/telemetry.py"],
    "C078": ["control/controller.py", "docs/OBSERVABILITY_AND_TESTING.md"],
    "C079": ["docs/OBSERVABILITY_AND_TESTING.md"],
    "C080": ["governance/alerts.yaml", "docs/OBSERVABILITY_AND_TESTING.md"],
    "C082": ["fixtures/MANIFEST.json", "schemas/PK_HEAVYBOX_ERROR_v1.schema.json"],
    "C083": ["fixtures/valid/adjacent_harness.json"],
    "C084": ["control/compat.py", "docs/generated/COMPATIBILITY.md"],
    "C085": ["tools/fuzz.py", "evidence/security/fuzz.json"],
    "C086": ["tests/test_control_lifecycle.py"],
    "C087": ["docs/THREAT_MODEL.md"],
    "C088": ["tools/bench.py"],
    "C089": ["tests/test_control_faults.py", "docs/OPERATIONS.md"],
    "C090": ["tools/build_evidence.py", "tools/production_gate.py", "evidence/release-manifest.json"],
    "C091": ["docs/OPERATIONS.md", "docs/ARCHITECTURE.md"],
    "C092": ["docs/OPERATIONS.md", "control/config.py"],
    "C093": ["control/compat.py", "docs/generated/COMPATIBILITY.md"],
    "C094": ["docs/OPERATIONS.md"],
    "C095": ["docs/OPERATIONS.md"],
    "C096": ["docs/OPERATIONS.md"],
    "C097": ["docs/OPERATIONS.md", "governance/alerts.yaml"],
    "C098": ["governance/review_schedule.json", "docs/OPERATIONS.md"],
    "C099": ["governance/waivers.json", "tools/production_gate.py"],
    "C100": ["tools/production_gate.py", "evidence/gate-result.json"],
    "INV71-X001": ["deps/pk_core.lock.json", "tools/pk_core_probe.py", "evidence/pk_core_probe.json"],
    "INV71-X002": ["docs/PRODUCTION_BOUNDARY.md"],
    "INV71-X003": ["control/runtime_plan.py", "docs/PRODUCTION_BOUNDARY.md"],
    "INV71-X004": ["pyproject.toml", ".github/workflows/ci.yml", "evidence/sbom.cdx.json", "evidence/provenance.json"],
    "INV71-X005": ["LICENSE_STATUS.md", "THIRD-PARTY-NOTICES.md", "evidence/license-inventory.json"],
    "INV71-X006": ["docs/SECURITY_DESIGN.md", "control/runtime_plan.py"],
    "INV71-X007": ["control/egress.py", "docs/SECURITY_DESIGN.md"],
}

# IMP items per control, in order: "S:note".  Notes are required for P/O/B.
IMP = {
    "C009": ["P:role template and RACI published; every role is UNASSIGNED", "I:RACI table + two-person/self-approval enforcement in control/auth.py", "B:needs paging system, people and vendor contacts", "I:authority-boundary table", "B:paging drill needs a paging system and named on-call"],
    "C010": ["B:approvals from platform/security/SRE/network/release owners; no owner exists", "I:alternatives table with rejection rationale", "I:frozen boundary section", "P:PROPOSED targets only; no measurement exists", "I:supersession rules + governance test guarding Accepted status"],
    "C011": ["I:23 SHALL/SHALL NOT requirements", "I:stable IDs with pre/post/acceptance", "I:security_invariant flag on 8 requirements", "I:per-operation deadlines and resource fields", "P:mapped to reference tests; production tests do not exist"],
    "C012": ["I:four profiles", "P:kernel/KVM/cgroup/memory/time checked; DNS, entropy, certificate and image-cache prerequisites not", "P:offline grace and telemetry buffer per profile; image pre-positioning and local policy cache not implemented", "I:unsupported combinations declared and refused", "I:qualify() emits PK_HEAVYBOX_NODE_QUALIFICATION/1"],
    "C013": ["I:SLO/SLI table", "I:p50/p95/p99 + hard timeouts per warm/cold/teardown/policy (PROPOSED)", "I:determinism of precedence/merge/policy; tested", "I:zero-budget invariants separated", "I:measurement windows, exclusions, clock source"],
    "C014": ["I:Outcome enum", "I:partial-effect/compensation table", "I:classified codes incl. snapshot/artifact/policy/capacity/guest/teardown/audit", "I:retry class + operator action per code", "I:READY and VERIFIED postconditions enforced in code"],
    "C015": ["I:14 states", "I:transition table with initiator/guard/timeout/event", "I:crash_recovery per transition (reference semantics)", "P:QUARANTINED distinct; CLOSED needs a typed TeardownProof for the sid, which is in-process and unsigned", "I:3000 random walks + stale-controller tests"],
    "C016": ["I:per-surface versions", "I:N/N-1 window", "P:unknown optional surfaces ignored; v2 schemas are closed (additionalProperties false) - reserved-field policy not defined", "I:deprecation table", "P:v2->v1 reduction fixture only; no old/new client-server runs"],
    "C017": ["I:per-session ceilings for vCPU/mem/pids/fds/disk/inodes/IOPS/net/conns/wall-clock", "P:tenant quotas + node capacity; snapshot/image cache and control-plane rate not modeled", "I:weighted fair share + 10% reserve", "P:rendered as cgroup v2/jailer/rate limiters; never enforced on a host", "P:rejection metrics + fairness test at reference scope"],
    "C018": ["I:offline behavior table", "P:bounded grace implemented; signed local policy/artifact cache not", "P:profile offline grace; edge offline-create rules only documented", "P:fencing + reconcile; buffered audit upload not implemented", "P:partition and flapping tests; clock drift and reconnect storms not"],
    "C019": ["I:precedence order", "I:non-overridable constraints", "I:stable PREC.* reason codes", "P:review requirement documented, not enforced", "I:table-driven precedence tests incl. missing input"],
    "C020": ["I:evidence/traceability.json", "I:test tags -> controls; orphan tests flagged", "I:sha256 per evidence file + release tree digest", "I:governance test fails on a control with no evidence", "B:signing needs a managed key"],
    "C021": ["I:15-boundary inventory", "I:protocol/direction/trust/identity/class/timeout/size/owner", "I:host paths/sockets/netns/cgroups listed = Plan.owned", "I:mermaid DFD", "P:plan hygiene test; no architecture review body"],
    "C022": ["P:session/egress/teardown/error/status/config schemas; policy distribution and exec/attach not", "I:canonical_bytes", "P:required/length/enum constraints; redaction class not in schemas", "P:config validator; no generated client types", "I:golden valid/invalid fixtures"],
    "C023": ["I:authentication matrix", "B:mTLS/SPIFFE needs a PKI", "P:lifetime/replay/revocation/skew in reference; bootstrap roots not", "P:artifact identity via manifest; node identity absent", "I:expired/revoked/audience/tenant/forged/replay/skew/anonymous tests"],
    "C024": ["I:capability model", "I:default deny, no wildcard", "P:principal/tenant/site/action bound; resource attributes absent and policy_version carried but not checked against the live policy", "I:host capabilities node-helper only", "I:reason codes + role-confusion/tenant-substitution tests"],
    "C025": ["I:per-operation deadlines", "P:cancellation documented; not implemented", "I:idempotency keys + window + mismatch rejection", "I:retry classes + full-jitter backoff", "P:429 + reserve + breaker; no queue-length limit"],
    "C026": ["I:namespaced registry", "I:retry/http/grpc/action/message per code", "I:correlation/operation/session/config fields", "I:INTERNAL.UNCLASSIFIED with privileged type only", "I:registry contract + exception mapping tests"],
    "C027": ["P:API/feature negotiation; snapshot/image via skew check", "I:required-feature refusal", "I:upgrade order + max skew", "P:downgrade documented only", "B:mixed-version matrix needs released versions"],
    "C028": ["P:token/config/path/sid/allowlist limits; response/event sizes only via schemas", "P:admission concurrency; no per-principal outstanding-op limit", "I:size checks before decode/parse", "P:reserve and fair share; no soft-limit throttling", "P:N-1/N/N+1 and fuzz; no concurrent-tenant load test"],
    "C029": ["I:fixture bundle", "I:golden canonical bytes + invalid fixtures", "I:fake INV-69/24/26/GAP-09 harness", "P:transitions/events/audit hashes; metric expectations not", "P:version+digest published; no second implementation to run it"],
    "C030": ["P:fake adjacent layers only", "P:reference serialization, not a real transport", "P:reference failure cases", "B:needs Linux/KVM hosts", "P:reference evidence captured"],
    "C031": ["B:no Firecracker/kernel/rootfs bytes; manifest UNPINNED", "P:qualify probe records CPU model/microcode; nothing pinned", "P:manifest schema + verifier; entries UNPINNED", "I:floating tags rejected; update policy in OPERATIONS", "P:verifier + gate reject; node-start check exists only as reference"],
    "C032": ["I:artifact classes digest-addressed", "P:per-session overlay in plan; not executed", "P:read-only root drive; runtime immutability unproven", "P:paths listed; mount flags/permissions partial", "P:reconcile on fixtures only"],
    "C033": ["I:typed schema", "I:secure defaults", "I:LOCKED + privileged flag + ranges", "I:deterministic, no env defaults", "I:baseline + generated docs + unknown fields rejected"],
    "C034": ["P:syntax/semantic/cross-field/signature; environment-capability join not", "P:ranges/devices; manifest digest not cross-checked against store", "I:prepare-then-commit, previous kept", "I:fail closed; CONFIG vs DEPENDENCY codes", "I:malformed/oversized/conflicting/stale/unsigned/escalating tests"],
    "C035": ["I:five layers", "I:per-layer allowlist + lower-only", "P:whole config signed; overlays not signed individually", "O:offline overlay cache not implemented", "I:merge tests"],
    "C036": ["I:Provenance record", "P:controller passes the config digest on every audit event it writes; audit_log does not enforce it", "P:activation history in memory, not durable", "P:status exposes digest, not full provenance", "B:incident reconstruction exercise needs an incident process"],
    "C037": ["P:Participant protocol; no real firewall/cgroup participant", "I:prepare/commit/abort generation switch", "I:monotonic generations", "P:previous kept; mixed-node quarantine not implemented", "P:participant rejection tested; process death/disk-full not"],
    "C038": ["P:triggers documented, not automated", "P:previous generations retained; re-verification on rollback partial", "P:rollback with reason/cohort; two-person authz not wired into ConfigStore", "P:documented", "B:drills need an environment"],
    "C039": ["B:needs a secret provider", "P:separation designed", "P:redaction in audit and error records; traces/crash dumps not", "P:documented", "P:argv/config scan test; runtime inspection blocked"],
    "C040": ["P:qualification + runbook; bootstrap not automated", "P:documented", "P:manifest verifier exists", "I:qualification report", "B:needs a clean production-equivalent host"],
    "C042": ["I:privilege inventory", "P:designed; per-session uid in plan", "P:designed; not deployed", "I:separate operator roles", "B:needs a host"],
    "C043": ["P:chroot and no mounts in plan; not executed", "P:nftables default-drop rendered", "P:no devices (locked)", "P:default seccomp retained; no custom profile", "P:argv/env scan"],
    "C044": ["B:needs PKI", "B:needs attestation hardware/service", "P:manifest signer check", "P:procedures documented", "P:reference credential rejections; duplicate node identity not"],
    "C045": ["P:SBOM for this package only", "P:HMAC reference signature + digest", "P:provenance without VCS commit or builder identity", "I:digest revocation", "P:tamper/wrong-signer/replay/unapproved/revoked tested; expired trust root not"],
    "C046": ["B:needs a real microVM", "P:SMT off; placement policy documented", "P:per-session overlay/netns in plan", "P:no vsock/console in plan", "B:residue tests need KVM"],
    "C047": ["I:path enumeration", "P:policy stated, not implemented", "P:designed", "P:key lifecycle documented", "B:needs KMS/PKI"],
    "C048": ["I:classification", "I:bounded grace", "I:hard deny for new trust decisions", "P:clock-loss policy documented; monotonic sequence", "P:outage + recovery tested; revocation during outage not"],
    "C049": ["I:audit schema (REQUIRED fields)", "P:chain + MAC + anchored checkpoints; MAC is not an asymmetric node signature", "P:refuse-not-drop spool; no authenticated transport", "I:actor/tenant/node/op/versions/reason/clock/correlation + redaction", "I:deletion/insertion/mutation/reorder/dup/MAC/truncation detection"],
    "C050": ["B:needs jailer/KVM", "P:parsers fuzzed; vsock/image metadata n/a", "I:token/capability/audit/epoch replay tests", "B:needs Firecracker/kernel", "P:admission exhaustion at reference; fork/memory/IO floods blocked"],
    "C051": ["I:16-row matrix", "I:detection/blast/ambiguity/retry/recovery/risk", "I:correlation column", "I:scenario per row (2 BLOCKED)", "P:test enforces scenarios; no review board"],
    "C052": ["P:status + dependencies; per-component probes absent", "I:monotonic deadlines + overdue + watchdog", "B:thresholds need measured distributions", "I:security vs degraded aggregation", "P:stall tests only"],
    "C053": ["I:classification", "I:backoff/jitter/attempts/elapsed/deadline", "P:create idempotency; persistence across controller restart not", "I:denials never retried", "P:duplicates + flapping; timeout-after-commit/late success not"],
    "C054": ["P:vCPU/mem/sessions; fds/KVM slots/net/cache/IOPS not", "I:reserve slice", "I:tenant-aware shedding", "I:breaker with bounded half-open", "P:reference fairness test; no load test"],
    "C055": ["P:documented", "P:residency in precedence; placement not implemented", "I:fencing leases", "I:restart from clean base only", "P:controller partition at reference; region failover blocked"],
    "C056": ["I:critical vs noncritical", "I:only locally verifiable operations", "I:examples", "P:DEGRADED + list; start time/duration cap not exposed", "P:entry tested; exit/backlog flush not"],
    "C057": ["P:documented", "I:durable audit before acknowledgement (defect fixed + tested)", "P:reconcile against supplied inventory", "P:documented", "P:create-phase faults; not every commit point"],
    "C058": ["I:epochs", "I:operation dedupe", "P:duplicate node identity not handled", "I:stale generation rejected", "I:partition + 64-way concurrency tests"],
    "C059": ["P:global/tenant/node disable + freeze; egress revoke via policy generation only", "I:freeze vs terminate", "I:authz + reason + incident + audit", "P:reserve slice; local node command path not", "B:drills need an environment"],
    "C060": ["P:in-process injection only", "I:tied to failure matrix", "I:no leak after injected faults", "B:needs load/rollout environment", "P:seeds recorded; reference evidence"],
    "C061": ["P:reference harness with fingerprint", "B:needs Firecracker host", "B:needs host metrics", "B:needs qualified node", "B:needs edge hardware"],
    "C062": ["P:PROPOSED targets", "P:PROPOSED ceilings", "P:warm/cold split", "P:regression rule text", "I:encoded in bench gate"],
    "C063": ["P:burst and teardown storm only", "P:latency/rejections at reference", "B:needs real multi-tenant load", "B:needs real resources", "P:gate vs thresholds; no approved baseline"],
    "C064": ["B:needs VMM processes", "B:needs measurement", "B:needs victim/aggressor runs", "B:billing semantics need an owner", "B:needs measured overhead"],
    "C065": ["P:tracemalloc profiling of the control layer", "B:needs guest/host data path", "B:needs images", "B:needs production concurrency", "P:two memory findings fixed with before/after"],
    "C066": ["P:verified resolver cache with bounded TTL", "O:batching policy not written", "B:needs measurement", "B:needs scheduler", "B:needs measurement"],
    "C067": ["I:bounds on explain/decisions/audit spool/idempotency/replay/leases", "I:audit refuses, others evict", "O:fan-out limits not implemented", "P:admission high-water only", "I:churn convergence test"],
    "C068": ["B:needs edge hardware", "B:needs edge hardware", "B:needs measurements", "B:needs measurements", "B:needs edge hardware"],
    "C069": ["B:needs measurements", "P:headroom metric defined", "I:reserve policy", "B:needs scale tests", "P:admission consumes capacity"],
    "C070": ["P:bench gate; no approved baseline", "P:absolute limits; regression % documented only", "P:fingerprint recorded, not enforced", "P:waiver register exists", "P:rollback criteria documented"],
    "C071": ["P:status has versions/config digest; artifact digests and authn on endpoint absent", "P:dependency states listed", "I:privileged-only detail", "I:live/ready/degraded/quarantined", "I:schema + fixture"],
    "C072": ["I:metrics registry + exposition", "B:host/VMM metrics need a host", "I:bounded vocabularies", "I:catalog", "B:exporter load test needs deployment"],
    "C073": ["I:structured audit fields", "I:event taxonomy", "I:redaction", "P:bounded spool + loss signal; clock quality is a placeholder", "P:correlation ids; controller->node->Firecracker chain absent"],
    "C074": ["P:traceparent library; not wired across processes", "O:spans not created", "I:untrusted headers ignored", "P:force_sample for errors/security", "O:not tested across processes"],
    "C075": ["P:scoped explain view", "P:tenant scoping only", "I:bounded", "P:name-based redaction", "P:cross-tenant explain test"],
    "C076": ["P:create/egress/authz decisions; place/retry/shed/rollback not all", "I:inputs by digest", "I:registry codes only", "P:field exists, rarely populated", "P:branch coverage partial"],
    "C077": ["P:explain view API", "P:reason code + digests", "I:tenant-scoped", "I:point-in-time records", "B:operator exercise needs operators"],
    "C078": ["I:release on create and records", "P:config/base digests; node image/kernel/microcode not", "B:needs a CMDB", "P:records retained in audit", "B:needs production data"],
    "C079": ["I:retention table", "I:sampling rules", "I:classification/residency", "P:deletion/legal hold stated", "B:needs retention jobs"],
    "C080": ["P:dashboard spec only", "I:zero-budget alert rules", "I:symptom/cause rules", "P:runbook links; owners UNASSIGNED", "B:needs monitoring stack"],
    "C082": ["I:contract tests", "I:semantic tests", "B:needs released version pairs", "I:golden bytes", "P:fixture digest check; no migration-note enforcement"],
    "C083": ["B:needs real layers", "P:reference lifecycle cases", "P:reconcile on inventories", "B:needs tiers", "P:reference evidence"],
    "C084": ["P:matrix rows all untested", "I:status vocabulary", "B:needs hardware", "I:no cross-hardware claims", "I:deployable() blocks"],
    "C085": ["P:6 targets", "P:property walks; not coverage-guided", "I:seed corpus", "P:time limits; no sanitizers (pure Python)", "P:documented + CI step"],
    "C086": ["I:duplicate create/teardown, admission churn", "P:random walks; no race detector", "P:stress at reference scale", "I:invariants asserted", "I:regressions kept"],
    "C087": ["I:threat -> test table", "P:reference scope", "B:needs supported versions", "B:needs independent reviewers", "I:links in traceability"],
    "C088": ["P:reference suites", "P:churn convergence", "P:burst/storm", "B:needs cluster", "P:automated comparison vs thresholds"],
    "C089": ["P:partition/DNS/trust/audit at reference", "P:stale epochs/duplicates", "B:needs environment", "I:degraded-never-bypasses tests", "B:needs drills"],
    "C090": ["P:evidence schema; unsigned", "P:digests; signatures blocked", "I:all 100 controls encoded", "I:offline reproducible verifier", "P:archived with release; promotion rejected"],
    "C091": ["I:SLI/SLO table", "I:burn-rate/support policy", "P:rollout pause documented", "I:end-to-end vs local", "B:needs production telemetry"],
    "C092": ["I:cohorts", "I:gates", "P:triggers documented; not automated", "P:documented", "B:drills"],
    "C093": ["P:matrix untested", "I:min/max/skew/EOL", "O:not generated from evidence yet", "I:check_skew/deployable", "P:versioned in repo"],
    "C094": ["I:PROPOSED SLA", "P:sources listed; no subscription", "P:documented", "I:lifetime/EOL", "B:needs fleet"],
    "C095": ["I:state classification", "P:documented", "I:reconstruct from clean artifacts", "P:documented", "B:needs drills"],
    "C096": ["P:Day-0 steps; production commands TBD", "P:Day-1", "P:Day-2", "P:prereqs/expected/abort partly", "B:game days"],
    "C097": ["I:severities", "P:paging targets UNASSIGNED", "I:containment playbooks", "I:re-entry criteria", "B:exercises"],
    "C098": ["I:schedule", "P:reviewers UNASSIGNED", "P:drift concept (config digest); report not automated", "P:documented", "P:documented"],
    "C099": ["I:register", "I:required fields", "I:gate enforces expiry/owner/permanence", "I:links schema", "P:review cadence stated"],
    "C100": ["I:gate covers all areas", "I:EVIDENCED-or-waived rule", "B:approvals need owners", "I:fail-closed verifier", "P:archived, unsigned"],
    "INV71-X001": ["P:lock fields declared; UNPINNED", "I:optional external integration", "I:digest-verifying resolver", "I:NOT_RUN/FAILED semantics", "P:CI calls the probe; pk_core list/run/gate/verify not run", "I:probe result in evidence", "P:absent/unpinned/mismatch tested; corrupt evidence/partial gate not", "P:owner UNASSIGNED"],
    "INV71-X002": ["I:declared unavailable after search", "I:nothing recovered; nothing fabricated", "B:nothing to diff without the file", "B:nothing to supersede without the file", "I:provenance note", "I:inventory test", "B:nothing recovered to preserve"],
    "INV71-X003": ["P:plan rendered; no runtime", "P:jailer/seccomp/cgroup/no-mount plan", "B:needs image build pipeline", "P:per-session overlay path", "P:netns/TAP/nft + DNS binding", "P:reconcile model", "P:verified multi-phase teardown at reference", "P:orphan detection", "B:needs real hosts"],
    "INV71-X004": ["I:pyproject + zero-dependency lock", "B:images", "P:package SBOM; no vulnerability scan", "B:managed signing keys", "P:CI written, not executed", "B:branch protection needs a hosting org", "P:gate re-verifies digests offline", "P:manifest tamper tests"],
    "INV71-X005": ["B:owner/legal decision", "B:follows the decision", "I:notices", "P:inventory in evidence; gate fails on missing LICENSE", "I:LICENSE_STATUS separates package vs images", "P:presence check in gate", "I:license inventory in evidence"],
    "INV71-X006": ["I:residue threat model", "P:swap off rendered; core dump policy documented", "B:kernel validation needs a host", "P:designed", "P:fresh overlay per session in plan", "P:KSM off specified", "B:residue tests need KVM", "P:documented; no acceptance"],
    "INV71-X007": ["I:host-based + IP binding, external enforcement", "I:trusted resolver + bound tuple", "I:TTL clamp + re-check", "P:IDNA/dots/zones/literals/v4-mapped/NAT64/metadata; redirects/CONNECT/SNI not", "I:capability closes TOCTOU", "I:decision log fields", "P:malicious DNS/TTL/rebinding/stale; split-horizon/dual-stack/redirect not", "I:fail closed"],
}

GLOBAL = ["P:specs versioned; owners UNASSIGNED", "B:no production path", "P:reference only", "P:reference authn/authz/audit", "P:reference cases", "P:reference layer only", "P:runbooks unexercised", "P:digests; artifacts UNPINNED; unsigned", "P:no independent review", "B:second audit needs the production path"]
FINAL = ["B:controls not EVIDENCED; no waivers", "B:no real microVM boundary", "B:artifacts UNPINNED/unsigned", "B:no PKI/KMS/WORM", "B:no game days", "B:not measured", "B:no releases", "B:no host", "B:unsigned bundle", "B:no named owners"]

FAULT_CONTROLS = {"C014", "C015", "C018", "C025", "C030", "C037", "C048", "C049", "C051", "C052", "C053", "C054",
                  "C055", "C056", "C057", "C058", "C059", "C060", "C089", "INV71-X001", "INV71-X007"}


GROUPS = [("ARCH", 9, 10), ("REQ", 11, 20), ("IFACE", 21, 30), ("IMPL", 31, 40), ("SEC", 42, 50),
          ("RES", 51, 60), ("PERF", 61, 70), ("OBS", 71, 80), ("TEST", 82, 90), ("OPS", 91, 100)]


def group_of(control: str) -> str:
    n = int(control[1:])
    return next(g for g, lo, hi in GROUPS if lo <= n <= hi)


REQ_CONTROLS = {"C011", "C012", "C013", "C014", "C015", "C016", "C017", "C018", "C019"}  # have HB-REQ entries

DES = {
    "ARCH": [("P", "path+version recorded; owner/reviewers/approval date UNASSIGNED"), ("I", "scope/out-of-scope stated"),
             ("P", "assumptions/residual risks documented; few are automated preflight checks"),
             ("P", "doc-drift and ADR-status tests; no architecture review body exists")],
    "REQ": [("REQ?", ""), ("I", "outcome model + stable error registry"),
            ("P", "requirement IDs in traceability and tests; not referenced from implementation code or telemetry"),
            ("P", "determinism tested in-process only; not across local/remote placement or profiles")],
    "IFACE": [("I", "boundary inventory with trust/authn/authz/timeout/idempotency/limits/compat"),
              ("P", "versioned schemas for session/egress/teardown/error/status/config; validation is in-process, not at a transport"),
              ("P", "valid/invalid fixtures; mixed-version only v2->v1 egress"),
              ("B", "no real transports or adapters exist")],
    "IMPL": [("P", "declarative config; artifact pins UNPINNED"), ("I", "fail-closed validation + two-phase generation switch"),
             ("I", "previous generation retained; signature re-verified on rollback"),
             ("P", "config digest in status/audit; artifact digests not in runtime status")],
    "SEC": [("P", "threat-model rows map prevention to tests; detection/containment/recovery partly"),
            ("P", "default deny implemented in the reference; host-side enforcement only rendered"),
            ("I", "audit records carry principal/versions/reason/correlation, redacted"),
            ("I", "adversarial negative tests; every defect found has a regression test")],
    "RES": [("I", "failure matrix rows"), ("I", "bounded retry, idempotency, fencing; recovery never skips checks"),
            ("P", "lifecycle state visible; no recovery progress signal"), ("B", "fault injection under load needs an environment")],
    "PERF": [("P", "reference layer only; production workload undefined"), ("P", "p50/p95/p99/max for the reference layer only"),
             ("P", "fairness under contention at reference scope"), ("P", "PROPOSED thresholds in an automated gate; verdict INCOMPLETE")],
    "OBS": [("I", "metric catalog, reason codes, bounded labels, redaction"), ("P", "correlation ids in audit/explain; no node/runtime lineage"),
            ("P", "bounded in-memory telemetry; audit refuses when full; exporters absent"), ("B", "no monitoring stack for dashboards")],
    "TEST": [("I", "stable test ids tagged to controls/requirements/threats"), ("B", "no production-equivalent hardware"),
             ("P", "positive/negative/boundary/fault/concurrency at reference; leak checks on supplied inventories"),
             ("I", "digest-addressed evidence consumed by the gate")],
    "OPS": [("P", "owners/approvers UNASSIGNED"), ("P", "procedures partly executable; production commands TBD"),
            ("B", "drills/game days need an environment and people"), ("P", "waiver expiry enforced by the gate; drill evidence expiry not")],
}


def rule_status(control: str, kind: str, n: int, has_tests: bool) -> tuple[str, str]:
    """Status for DES/VER/GATE lines, which are identical across controls."""
    all_blocked = all(x.startswith("B:") for x in IMP.get(control, ["B:"]))
    if kind == "DES":
        # DES lines differ by dimension (10 groups of 4); see DES below.
        g = group_of(control)
        code, note = DES[g][n - 1]
        if code == "REQ?":  # C011-C020 line 1: I only where the control has its own SHALL requirement
            code = "I" if control in REQ_CONTROLS else "P"
            note = "SHALL + acceptance in governance/requirements.json" if code == "I" else "no control-specific SHALL yet"
        if all_blocked and code == "I":
            code, note = "P", note + "; implementation lines for this control are all BLOCKED"
        return (code, note)
    if kind == "VER":
        if n == 1:
            if all_blocked or not has_tests:
                return ("B", "no executable scope for this control here")
            return ("I", "positive/negative/boundary tests tagged to this control")
        if n == 2:
            return ("I", "fault/timeout/restart tests") if control in FAULT_CONTROLS else ("P", "fault coverage limited to reference scope")
        if n == 3:
            return ("P", "evidence has source tree digest, env fingerprint, config digest, timestamps; artifact digests UNPINNED; no VCS revision")
        if n == 4:
            return ("P", "no independent review performed; waiver register empty")
        if n == 5:
            return ("I", "AUDIT_AFTER.json regenerated from traceability, never from prose")
    if kind == "GATE":
        return {1: ("B", "no production path exists"),
                2: ("I", "linked in evidence/traceability.json by sha256"),
                3: ("B", "no operational owner exists"),
                4: ("P", "gate rejects absent/failing evidence and unsigned/unpinned inputs; no per-control staleness or revocation check; signatures checked for presence only")}[n]
    if kind == "XVER":
        return {1: ("I", "regression tests"), 2: ("P", "owner UNASSIGNED"), 3: ("P", "reference evidence"),
                4: ("I", "linked in traceability"), 5: ("B", "needs production-equivalent verification")}[n]
    raise KeyError(kind)
