"""Build CERTIFICATION_MANIFEST.json: one entry per checklist item (all 1,831), with status and evidence.

Statuses
  implemented          code in this package, verified by a dedicated or indirect test (see AUDIT_REPORT sampling)
  implemented-fixture  GAP-14's side implemented and tested against signed fixtures; needs the live counterpart
  documented           satisfied by a normative document in docs/ (no code required by the item)
  partial              some of the item is met; the note says exactly what is missing
  open                 not implemented in v4.3.0
  external             cannot be closed inside this package (people, live estate, other OS/runtimes, signing, exercises)
  not-applicable       item does not apply to this component; note says why

The classification below was made item by item against the checklist text; it is the
reviewable source for the manifest.  Regenerate after changing it:
    python gap14_data_gravity_manager/tools/build_manifest.py
"""
from __future__ import annotations

import collections
import json
import pathlib
import re

PKG = pathlib.Path(__file__).resolve().parents[1]
CHECKLIST = PKG / "docs" / "GAP14_v4.2.0_Missing_Components_Engineering_Checklist.md"
CODES = {"I": "implemented", "F": "implemented-fixture", "D": "documented", "P": "partial", "O": "open",
         "X": "external", "N": "not-applicable"}

T_SEC = "tests/test_p0_security_adapters.py"
T_EVD = "tests/test_p0_evidence_config_gate.py"
T_OPS = "tests/test_p1_operability.py"
T_FUZ = "tests/test_property_fuzz.py"
T_FLT = "tests/test_fault_injection.py"
T_P2 = "tests/test_p2_capabilities.py"
T_PKG = "tests/test_packaging.py"

# Primary evidence per component (code, tests, schemas, docs).
EVIDENCE = {
    "P0-01": ["compat.py", T_EVD + "::GateIntegrityTest", "__main__.py (handshake, gate)"],
    "P0-02": ["adapters.py::PolicyAdapter", "schemas/PK_POLICY_REQUEST-1.schema.json", "schemas/PK_POLICY_VERDICT-1.schema.json", T_SEC + "::PolicyAdapterTest", T_FLT],
    "P0-03": ["adapters.py::TopologyAdapter", "planner.py::plan.route", "schemas/PK_TOPOLOGY_SNAPSHOT-1.schema.json", T_SEC + "::TopologyAdapterTest", T_FLT],
    "P0-04": ["adapters.py::ReplicationAdapter", "schemas/PK_CONVERGENCE_PROOF-1.schema.json", T_SEC + "::ReplicationAdapterTest", T_FLT],
    "P0-05": ["adapters.py::PlacementAdapter", "schemas/PK_PLACEMENT_SNAPSHOT-1.schema.json", T_SEC + "::PlacementAdapterTest"],
    "P0-06": ["adapters.py::DataPlaneHandoff", "schemas/PK_DATA_MOVE_HANDOFF-1.schema.json", "schemas/PK_DATA_MOVE_ACK-1.schema.json", T_EVD + "::EstateIntegrationTest"],
    "P0-07": ["identity.py", "service.py::decide", "schemas/PK_CAPABILITY_TOKEN-1.schema.json", T_SEC + "::AuthTest"],
    "P0-08": ["identity.py::WorkloadIdentity", "service.py::DecisionRequest", T_SEC + "::TenantIdentityTest"],
    "P0-09": ["service.py::_decide (provenance)", "schemas/PK_DECISION_PROVENANCE-1.schema.json", T_EVD + "::ProvenanceTest"],
    "P0-10": ["audit.py", "__main__.py verify-audit", "schemas/PK_AUDIT_RECORD-1.schema.json", T_EVD + "::AuditTest"],
    "P0-11": ["config.py", "schemas/PK_GAP14_CONFIG-1.schema.json", T_EVD + "::ConfigTest", "docs/OPERATIONS.md#1"],
    "P0-12": ["tests/fixtures/estate.py", T_EVD + "::EstateIntegrationTest", T_FLT, "evidence/test_report.json"],
    "P1-13": ["resilience.py::Deadline/CancellationToken/AdmissionController", T_OPS + "::DeadlineCancellationTest"],
    "P1-14": ["resilience.py::call_with_resilience/CircuitBreaker/RetryPolicy", T_OPS + "::RetryBreakerTest"],
    "P1-15": ["resilience.py::FreshnessPolicy", "trust.py::check_fresh", T_OPS + "::FreshnessStaleTest"],
    "P1-16": ["resilience.py::StaleDataPolicy", "service.py (provenance.quality)", T_OPS + "::FreshnessStaleTest"],
    "P1-17": ["service.py::health/drain", "schemas/PK_HEALTH-1.schema.json", T_OPS + "::HealthTest"],
    "P1-18": ["observability.py::Registry/standard_metrics", T_OPS + "::MetricsLoggingTest", "docs/OPERATIONS.md#3"],
    "P1-19": ["observability.py::StructuredLogger/TraceContext", T_OPS + "::MetricsLoggingTest"],
    "P1-20": ["service.py::explain", "schemas/PK_GRAVITY_EXPLAIN-1.schema.json", T_OPS + "::ExplainTest"],
    "P1-21": ["resilience.py::AdmissionController", T_OPS + "::AdmissionTest"],
    "P1-22": [T_FUZ],
    "P1-23": ["tools/bench.py", "evidence/bench_v4.3.0.json", "evidence/bench_v4.3.0_threads*.json"],
    "P1-24": [T_FLT],
    "P1-25": ["docs/COMPATIBILITY.md", "compat.py", T_PKG],
    "P1-26": ["docs/SUPPLY_CHAIN.md", "tools/release_evidence.py", "evidence/SBOM.cdx.json", "MANIFEST.sha256"],
    "P1-27": ["pyproject.toml", "__main__.py", T_PKG],
    "P2-28": ["planner.py (move-data-partial)", T_P2 + "::PartialMovementTest"],
    "P2-29": ["planner.py (WorkloadProfile.runs, warm-up, cache reuse)", T_P2 + "::AmortisationTest"],
    "P2-30": ["planner.py (replicate)", T_P2 + "::ReplicationOptionTest"],
    "P2-31": ["planner.py::optimize_dag", "service.py::plan_dag", T_P2 + "::DagTest"],
    "P2-32": ["planner.py::SiteEconomics", T_P2 + "::CarbonThermalTransferStorageTest"],
    "P2-33": ["planner.py::Route.transfer_hours", T_P2 + "::CarbonThermalTransferStorageTest"],
    "P2-34": ["planner.py (storage/IOPS, min charge, rounding)", T_P2 + "::CarbonThermalTransferStorageTest"],
    "P2-35": ["adapters.py::PlacementSnapshot.compatible", T_P2 + "::CompatQuotaTest", T_SEC + "::PlacementAdapterTest"],
    "P2-36": ["adapters.py::PlacementSnapshot.data_quota_ok", T_P2 + "::CompatQuotaTest"],
    "P2-37": ["modeling.py::CalibrationTracker/PageHinkley", "service.py::record_outcome", T_P2 + "::CalibrationTest"],
    "P2-38": ["service.py (shadow/canary)", "modeling.py::CanaryRouter", T_P2 + "::ShadowCanaryTest"],
    "P2-39": ["service.py::simulate", "schemas/PK_GRAVITY_SIMULATION-1.schema.json", T_P2 + "::SimulationTest"],
    "P2-40": ["docs/RUNBOOKS.md"],
}

# Component-specific items (A05-A10, B04-B06, D01-D03, E01-E04, G01-G03).  "ID:S[:note]" separated by " | ".
SPECIFIC = {
 "P0-01": "A05:P:range + API surface pinned; certified digest is None until release engineering records it (handshake reports UNPINNED) | A06:I | A07:I | A08:P:pyproject pins build backend; no lock for pk_core because the certified build is not available here | A09:I:only PKCORE_PIN.required_api is consumed | A10:I | B04:I | B05:I | B06:I | D01:P:version/digest/capabilities recorded in handshake + gate result; not emitted as a metric during a gate run | D02:I | D03:P:duration recorded in handshake; metric declared, not emitted by CLI | E01:X:requires the real pk_core at min/max/pinned versions | E02:I | E03:I | E04:X:clean Windows/CI environment not available | G01:X:needs certified runtime | G02:X:needs recorded digest | G03:I",
 "P0-02": "A05:I | A06:I | A07:I | A08:I:request_hash binding | A09:I | A10:I:obligations of touched sites attached to decision and PLN-06 handoff | B04:I | B05:I | B06:I | D01:I:gap14_dependency_latency_seconds{dependency=GAP-13} | D02:P:outcomes counted by refusal code; allow/deny per rule code not metered | D03:P:version/issuer/age in provenance, not span attributes | E01:F | E02:I | E03:I | E04:I | G01:F:against fixtures; live GAP-13 pending | G02:I | G03:I",
 "P0-03": "A05:I | A06:I | A07:I:NaN/inf/negative/zero multipliers rejected (TopologyDomainTest) | A08:I:version + body_digest in provenance | A09:I:one immutable snapshot per decision | A10:I | B04:I | B05:P:topology and cost arrive in one signed snapshot, so mixing cannot occur by construction; no dedicated test | B06:I | D01:P:age/version in provenance; no age gauge | D02:I | D03:O:no multiplier/effective-cost distribution metric | E01:I | E02:I | E03:I | E04:P:single snapshot per decision by construction; no explicit refresh-race test | G01:I | G02:I | G03:I",
 "P0-04": "A05:P:dataset, version, conflicts, watermark; no replica-set/epoch/member-set/consistency-mode fields | A06:P:dataset_version bound; content generation not bound into the request | A07:P:issuer, TTL, signature, version rollback enforced; replica-set mismatch not modelled | A08:O:binary converged state only | A09:P:proof ref + digest in provenance and handoff; PLN-06 re-validation is PLN-06's side | A10:O | B04:P:60 s TTL bounds staleness; no invalidation on topology/replica-set change | B05:I:caller boolean not used on the service path | B06:P:version rollback detected; split-brain not modelled | D01:P | D02:P:generic dependency latency/outcome only | D03:I | E01:I | E02:I | E03:O | E04:P:version watermark only | G01:I | G02:I | G03:I",
 "P0-05": "A05:P:architecture, runtime, cpu, gpu; no memory/accelerator model/locality | A06:P:no maintenance state or reservations | A07:P:snapshot version/freshness bound; not bound to a workload revision | A08:I:COMPUTE_UNAVAILABLE vs COMPUTE_INCOMPATIBLE | A09:P:hard constraints only; preferred constraints not modelled | A10:I | B04:I | B05:X:needs SCH-01 reservations | B06:I | D01:I | D02:P:in provenance only | D03:O | E01:I | E02:X:execution precondition is SCH-01/PLN-06 side | E03:P:no preferred constraints to test | E04:F | G01:I | G02:I | G03:P:snapshot revision recorded; workload-spec identity not",
 "P0-06": "A05:P:decision id, handoff id, from/to, size, obligations, provenance digest, not_after; no dataset generation | A06:P:ack carries handoff_id/accepted/status; no executor identity/plan revision | A07:P:in-process idempotency + deterministic handoff id; persistence across restarts relies on PLN-06 dedupe | A08:P:expiry precondition only | A09:O:execution state machine is PLN-06's | A10:O | B04:I | B05:I | B06:X:PLN-06 integrity verification | D01:P | D02:O | D03:O | E01:I | E02:I | E03:X | E04:P:tampered envelope rejected; completion attestation not modelled | G01:F | G02:I | G03:X",
 "P0-07": "A05:I:estate capability token; transport mTLS is the deployment's | A06:I:authenticated before body parse | A07:P:scopes enforced for recommend/explain/simulate/handoff; config activation does not yet check gravity:admin | A08:I | A09:I:aud, iss, exp, lifetime cap, alg allowlist, kid; request replay guard | A10:P:scopes separate; service vs human principals not distinguished | B04:I | B05:I | B06:I | D01:I | D02:I | D03:O | E01:I | E02:P:revocation tested; rotation overlap not | E03:P:decide/handoff/explain/simulate tested; plan_dag/record_outcome authorization not separately tested | E04:P:request fuzzed; token structure fuzz not | G01:I | G02:I | G03:I",
 "P0-08": "A05:I | A06:P:dataset version via convergence proof; no workload revision | A07:I | A08:I | A09:D:docs/COMPATIBILITY.md | A10:I | B04:I | B05:I | B06:I:single ident() normaliser (NFC-only) | D01:O | D02:I | D03:I:keyed-hash identifiers in logs | E01:I | E02:P:covered by fuzz values; no dedicated case/whitespace test | E03:P:strict rejection of unknown/legacy fields; no legacy fixture | E04:I | G01:I | G02:I | G03:I",
 "P0-09": "A05:I | A06:I | A07:I | A08:P:issued_at and age recorded; separate observation timestamp not | A09:I | A10:I | B04:P:refs + body digests recorded; bodies not retained, reconstruction needs producer archives | B05:I | B06:I | D01:P | D02:O | D03:I | E01:P:planner deterministic; bundle replay tool not provided | E02:I | E03:P:canonical JSON deterministic; cross-platform run not done | E04:I | G01:I | G02:P | G03:I",
 "P0-10": "A05:I | A06:I | A07:I | A08:P:retention stated in DESIGN §6; legal hold/partitioning/export not specified | A09:I:synchronous, fail-closed, no buffer | A10:I | B04:I | B05:I | B06:I | D01:P:result counter only | D02:P:CLI result; no metric | D03:I | E01:I | E02:I | E03:P:historical records verify with retained keys; revoked keys also invalidate history (documented) | E04:I:synchronous fsync means nothing is pending | G01:I | G02:I | G03:P",
 "P0-11": "A05:I | A06:I | A07:I | A08:I | A09:P:history in memory; last-known-good not persisted | A10:P:strict schema admits no secret fields; secret-store references not implemented | B04:I | B05:P:rollback limited to revisions verified in-process | B06:I | D01:I:gap14_build_info | D02:I | D03:P | E01:I | E02:I | E03:I | E04:P | G01:I | G02:I | G03:I",
 "P0-12": "A05:F | A06:P:scenarios are tests, not a manifest file | A07:I | A08:P:decision id correlated through audit and handoff; not sent to policy/topology | A09:I | A10:I:evidence/test_report.json | B04:I | B05:I | B06:I:skips reported with reasons | D01:I | D02:O | D03:P | E01:F | E02:F | E03:I | E04:P:config reload during decisions tested sequentially only | G01:X:live estate | G02:I | G03:P",
 "P1-13": "A05:I | A06:P:deadline checked between stages and passed to transports; in-flight transport cancellation depends on the client | A07:I | A08:P:G14_OVERLOADED; no Retry-After | A09:I | A10:I:health() bypasses admission | B04:P:bounded if transport honours timeout | B05:P | B06:I | D01:I | D02:I | D03:O | E01:I | E02:P:pre-dispatch cancellation tested | E03:I | E04:P | G01:P:enforced via transport timeout parameter | G02:I | G03:I",
 "P1-14": "A05:I | A06:I | A07:I | A08:I | A09:O:no Retry-After handling | A10:I | B04:I | B05:I | B06:I | D01:P | D02:O | D03:O | E01:I | E02:I | E03:P | E04:I | G01:I | G02:I | G03:I",
 "P1-15": "A05:I | A06:P:issued_at recorded; receipt time = decision issued_at | A07:I | A08:I | A09:P:checked at fetch within a short deadline | A10:P:handoff not_after only | B04:I | B05:I | B06:P | D01:P | D02:I | D03:O | E01:I | E02:I | E03:P | E04:I | G01:I | G02:I | G03:I",
 "P1-16": "A05:I | A06:I | A07:I | A08:I | A09:I:no cache exists | A10:I | B04:I | B05:I | B06:I | D01:I | D02:I | D03:N:no cache | E01:I | E02:I | E03:I | E04:I | G01:I | G02:I | G03:I",
 "P1-17": "A05:I | A06:I | A07:I | A08:I | A09:I | A10:I:drain() | B04:I | B05:I | B06:I | D01:I | D02:O | D03:O | E01:I | E02:I:service cannot start without an active config | E03:I | E04:I | G01:P:degraded not a distinct state | G02:I | G03:P:no secrets; endpoint exposure is the deployment's",
 "P1-18": "A05:P:no per-handoff counter | A06:I | A07:P:cost histogram only; no size distribution | A08:I | A09:I | A10:I | B04:I | B05:I | B06:I | D01:O | D02:I | D03:P:bench includes instrumentation | E01:I | E02:P | E03:P | E04:I | G01:P:metrics exist and are tested; dashboards are sketches | G02:I | G03:I",
 "P1-19": "A05:I | A06:P:ingress parsed, recorded; not propagated to dependency requests | A07:I | A08:I | A09:I | A10:O | B04:I | B05:P | B06:I | D01:O | D02:O | D03:I | E01:I | E02:P | E03:I | E04:O | G01:I | G02:I | G03:I",
 "P1-20": "A05:I | A06:I | A07:I:recorded envelope, never recomputed | A08:I | A09:P:no role-based redaction | A10:I | B04:I | B05:I | B06:I | D01:I | D02:P | D03:O | E01:P | E02:I | E03:P | E04:O | G01:I | G02:I | G03:P",
 "P1-21": "A05:P:size checked on parsed object; raw-byte/nesting limit belongs to the transport layer | A06:I | A07:I:global + per-tenant | A08:I | A09:I | A10:O | B04:P | B05:I | B06:I | D01:I | D02:O | D03:P | E01:P | E02:I | E03:P | E04:P | G01:I | G02:P | G03:P:bounded caches; soak memory in evidence",
 "P1-22": "A05:P:seeded stdlib generators, no Hypothesis/shrinking | A06:P | A07:I | A08:I:NaN, ±inf, negatives, subnormal, max finite, -0.0, precision tie, 2**63 | A09:I | A10:P:seeded and reproducible; no minimized-example store | B04:I | B05:I | B06:I | D01:P | D02:O | D03:O | E01:P | E02:O | E03:P:GAP14_FUZZ_ITERS knob; nightly job not scheduled | E04:O | G01:P | G02:I | G03:I",
 "P1-23": "A05:P | A06:I:engine_only vs service in bench output | A07:P:latency/throughput/memory; CPU/GC not | A08:I:warm-up | A09:P:40 s soak, not multi-hour | A10:P | B04:P | B05:P | B06:O | D01:I | D02:P | D03:O | E01:I | E02:X:needs live dependencies | E03:X | E04:P | G01:P:met in-process single worker (p99 ~1.2 ms); not with 8 threads/process; live pending | G02:P | G03:O",
 "P1-24": "A05:P:timeout/outage/tamper/stale/rollback; DNS/reset are transport-level | A06:I | A07:I | A08:I | A09:I | A10:I | B04:I | B05:I | B06:I | D01:O | D02:P | D03:P | E01:I | E02:I | E03:P | E04:I | G01:I | G02:I | G03:I",
 "P1-25": "A05:D | A06:D | A07:D | A08:O:matrix is hand-written markdown | A09:P | A10:D:docs/RUNBOOKS.md deprecation | B04:P | B05:I | B06:D | D01:O | D02:O | D03:O | E01:X:3.12/3.13 not available | E02:P | E03:X | E04:I | G01:D | G02:P | G03:I",
 "P1-26": "A05:P:no third-party deps; build backend pinned without hash | A06:I | A07:X:estate registry/signing | A08:P:release_evidence.json; no builder attestation | A09:X | A10:D | B04:I | B05:P:MANIFEST.sha256 | B06:X | D01:O | D02:P | D03:O | E01:X | E02:I | E03:X | E04:P | G01:P:signature missing | G02:X:CI | G03:X",
 "P1-27": "A05:I | A06:P:runtime/optional only | A07:I | A08:I | A09:X:wheel/sdist build not run here | A10:X | B04:I | B05:I | B06:P | D01:P | D02:P | D03:D | E01:X | E02:X | E03:P | E04:I | G01:I | G02:I | G03:P",
 "P2-28": "A05:P:shard name/size/needed/converged; no lineage/generation | A06:P | A07:P:legality at dataset level; per-record policy not modelled | A08:I | A09:P:handoff kind + shard list | A10:P | B04:P | B05:I | B06:P | D01:O | D02:I | D03:O | E01:P | E02:O | E03:X | E04:I | G01:P | G02:P | G03:P",
 "P2-29": "A05:P:runs only; no confidence/horizon | A06:I | A07:P:reuse fraction | A08:I | A09:I | A10:P:default runs=1 | B04:P | B05:P | B06:O | D01:O | D02:O | D03:O | E01:I | E02:P | E03:O | E04:P | G01:I | G02:I | G03:P",
 "P2-30": "A05:I | A06:P:seed, storage, sync; deletion lifecycle not | A07:P:hold verdict at destination; retention not separately authorised | A08:P | A09:O | A10:I | B04:I | B05:O | B06:P | D01:I | D02:P | D03:O | E01:P | E02:O | E03:O | E04:O | G01:P | G02:P | G03:O",
 "P2-31": "A05:P | A06:I | A07:I | A08:P:transfer cost only | A09:I | A10:P:assignment + total; no per-edge breakdown | B04:I | B05:I | B06:I | D01:O | D02:P | D03:O | E01:I | E02:I | E03:I | E04:I | G01:I | G02:I | G03:P",
 "P2-32": "A05:P:units in field names | A06:P:signed config revision; no feed freshness | A07:I | A08:I | A09:D:transfer energy explicitly excluded (planner docstring) | A10:I | B04:P | B05:P | B06:I | D01:P:estimates are in the signed breakdown; no metric | D02:I | D03:O | E01:P | E02:I | E03:I | E04:O | G01:P | G02:I | G03:I",
 "P2-33": "A05:P:bandwidth, congestion | A06:I | A07:O | A08:O | A09:O | A10:I | B04:I | B05:I | B06:I | D01:P | D02:P | D03:P | E01:P | E02:P | E03:O | E04:P:missing bandwidth defaults to 1 Gb/s (time estimate only) | G01:I | G02:O | G03:P",
 "P2-34": "A05:P | A06:P:min charge, rounding; no currency/effective date | A07:I | A08:O | A09:O | A10:I | B04:I | B05:I | B06:O | D01:I | D02:P | D03:P | E01:I | E02:P | E03:O | E04:O | G01:P | G02:I | G03:I",
 "P2-35": "A05:P | A06:P | A07:O | A08:O | A09:I | A10:I | B04:I | B05:P | B06:O | D01:I | D02:P | D03:O | E01:I | E02:O | E03:O | E04:I | G01:I | G02:O | G03:I",
 "P2-36": "A05:P:storage quota only | A06:O | A07:O | A08:O | A09:P | A10:O | B04:I | B05:X | B06:O | D01:I | D02:O | D03:O | E01:I | E02:O | E03:O | E04:O | G01:I | G02:O | G03:O",
 "P2-37": "A05:P:joined by decision id in memory | A06:P:MAPE and bias | A07:P:Page-Hinkley; minimum sample size not | A08:I | A09:I | A10:D:RB-06 | B04:I | B05:P | B06:I:no auto-tuning | D01:P | D02:I | D03:O | E01:I | E02:O | E03:P | E04:P | G01:P | G02:D | G03:I",
 "P2-38": "A05:I | A06:I | A07:P | A08:I | A09:P:shadow runs synchronously in-process | A10:D:RB-06 | B04:I | B05:P | B06:P:same verified inputs by construction; no dedicated test | D01:I | D02:O | D03:O | E01:I | E02:P:shadow errors captured; no dedicated test | E03:I | E04:P | G01:I | G02:I | G03:D",
 "P2-39": "A05:I | A06:P:explicit inputs; no base snapshot references | A07:P:same validators | A08:O:single scenario per call | A09:I | A10:I | B04:I | B05:I | B06:I | D01:I | D02:O | D03:O | E01:I | E02:P | E03:P | E04:O | G01:I | G02:I | G03:P",
 "P2-40": "A05:D | A06:D | A07:P:containment = stop routing; compute-only safe mode not implemented | A08:D | A09:P | A10:D | B04:D | B05:D | B06:D | D01:O | D02:O | D03:O | E01:X | E02:X | E03:X | E04:X | G01:P:roles named by function; people unassigned | G02:X | G03:D",
}

NO_TRUST_BOUNDARY = {"P1-22", "P1-23", "P1-24", "P1-25", "P1-27", "P2-40"}
NO_VERSIONED_IFACE = {"P1-13", "P1-14", "P1-15", "P1-16", "P1-22", "P1-23", "P1-24", "P1-26", "P1-27", "P2-29",
                      "P2-32", "P2-33", "P2-34", "P2-35", "P2-36", "P2-37", "P2-38", "P2-40"}


GENERIC_EVIDENCE = {
    "A02": ["docs/DESIGN.md"], "A03": ["docs/DESIGN.md#7", "docs/COMPATIBILITY.md"], "A04": ["docs/DESIGN.md#3"],
    "B01": ["errors.py", T_OPS + "::ReasonCodeRegistryTest"], "B02": ["errors.py", "docs/OPERATIONS.md#4"],
    "B03": [T_FLT], "C01": ["docs/DESIGN.md#5"], "C02": ["trust.py::KeyRing", "identity.py", T_SEC],
    "C03": ["trust.py", T_FUZ], "C04": ["trust.py::KeyRing", "docs/DESIGN.md#4"], "C05": ["docs/DESIGN.md#6"],
    "D04": ["observability.py::TraceContext", T_EVD + "::ProvenanceTest::test_trace_context_propagated"],
    "D05": ["observability.py", T_OPS + "::MetricsLoggingTest"], "D06": ["service.py (provenance)", "tools/release_evidence.py"],
    "E05": [T_SEC + "::SchemaVersionTest", T_FUZ], "E06": [T_FUZ], "E07": [T_OPS + "::AdmissionTest::test_concurrent_decisions_are_consistent"],
    "E08": [T_FLT], "F01": ["docs/OPERATIONS.md#1"], "F02": ["docs/OPERATIONS.md#2"], "F03": ["docs/OPERATIONS.md#4"],
    "F04": ["docs/OPERATIONS.md#5", T_EVD + "::ConfigTest"], "F05": ["CERTIFICATION_MANIFEST.json"],
}


def generic(comp: str, sec: str) -> tuple[str, str]:
    if sec == "A01":
        return "X", "owners unassigned (OWNERS.md); people cannot be assigned by the build"
    if sec in ("A02", "A03", "A04"):
        return "D", "docs/DESIGN.md §2/§3/§7 and §8 component note"
    if sec in ("B01", "B02"):
        return "I", "errors.py registry (category + disposition); docs/OPERATIONS.md §4"
    if sec == "B03":
        return "I", "tests/test_fault_injection.py (no default/ambient fallback under any single or pairwise fault)"
    if sec == "C01":
        return "D", "docs/DESIGN.md §5"
    if sec == "C02":
        return ("N", "no new trust boundary") if comp in NO_TRUST_BOUNDARY else ("I", "trust.py KeyRing issuer-scoped verification; identity.py")
    if sec == "C03":
        return "I", "trust.py ident/number/exact_fields; tests/test_property_fuzz.py"
    if sec == "C04":
        return ("N", "no decision-affecting data introduced") if comp in NO_TRUST_BOUNDARY else (
            "F", "HMAC-SHA256 + issuer + revision + timestamp; asymmetric signatures pending (DESIGN R-1)")
    if sec == "C05":
        return "D", "docs/DESIGN.md §6"
    if sec == "D04":
        return "P", "trace/span ids in logs, provenance, refusal audit; not propagated into dependency requests"
    if sec == "D05":
        return "I", "observability.py series caps; test_signals_emitted_without_high_cardinality_labels"
    if sec == "D06":
        return "I", "signed provenance envelope + tools/release_evidence.py"
    if sec == "E05":
        return ("N", "no versioned interface") if comp in NO_VERSIONED_IFACE else (
            "I", "current schema accepted, unknown schema tag / fields rejected (only one version exists)")
    if sec == "E06":
        return ("N", "runbooks") if comp == "P2-40" else ("I", "tests/test_property_fuzz.py; strict validators")
    if sec == "E07":
        return ("I", "test_concurrent_decisions_are_consistent") if comp in ("P1-21", "P0-10", "P1-13") else (
            "P", "one multi-threaded decision test; no component-specific race test")
    if sec == "E08":
        return ("N", "runbooks") if comp == "P2-40" else ("I", "component negative tests listed in evidence")
    if sec in ("F01", "F02", "F03"):
        return "D", "docs/OPERATIONS.md §1/§2/§4"
    if sec == "F04":
        return "D", "docs/OPERATIONS.md §5; audit chain verifies across rollback (test_rollback_then_forward_needs_newer_than_highest)"
    if sec == "F05":
        return "P", "CERTIFICATION_MANIFEST.json links schemas, tests, docs and digests; dashboards/alert rules are sketches only"
    if sec == "G04":
        return "X", "fixtures and artifacts are source-controlled; independent reviewer run required"
    if sec == "G05":
        return "X", "requires security review sign-off by an assigned reviewer"
    raise KeyError(sec)


def main() -> None:
    text = CHECKLIST.read_text(encoding="utf-8")
    items = re.findall(r"- \[ \] `(G14-(P\d-\d\d)-([A-G]\d\d))` (.*)", text)
    program = re.findall(r"^- \[ \] (?!`)(.*)$", text, flags=re.M)
    spec = {c: {p.split(":")[0].strip(): p.split(":", 2)[1:] for p in s.split(" | ")} for c, s in SPECIFIC.items()}
    entries, counts = [], collections.Counter()
    per_comp = collections.defaultdict(collections.Counter)
    for full, comp, sec, req in items:
        if sec in spec.get(comp, {}):
            parts = spec[comp][sec]
            code, note = parts[0], (parts[1] if len(parts) > 1 else "")
        else:
            code, note = generic(comp, sec)
        status = CODES[code]
        counts[status] += 1
        per_comp[comp][status] += 1
        entries.append({"id": full, "component": comp, "section": sec[0], "requirement": req.replace("**", "").strip(),
                        "status": status,
                        "evidence": (EVIDENCE[comp] if sec in spec.get(comp, {}) else GENERIC_EVIDENCE.get(sec, [])) if code in "IFPD" else [],
                        "note": note})
    assert len(entries) == 1800, len(entries)
    prog_codes = [  # 10 global DoD, 5 P0 closure, 4 P1 closure, 4 P2 closure, 8 final-bundle items (checklist order)
        ("X", "owners unassigned"), ("P", "schemas versioned and validated; cross-version compatibility tests limited"),
        ("D", "DESIGN §5"), ("I", "resilience.py + adapters"), ("I", "errors.py"), ("I", "observability.py"),
        ("P", "unit/contract/property/fuzz/fault present; live integration missing"), ("P", "no signature / VCS revision"),
        ("P", "documented; human exercises not run"), ("I", "this manifest"),
        ("X", "P0 G-gates open"), ("X", "certified pk_core"), ("X", "live estate"),
        ("F", "service path: 100% of decisions carry identity/provenance/audit (fixtures)"),
        ("F", "handoff requires production, signed, unexpired envelope; verdicts/convergence/placement enforced (fixtures)"),
        ("I", "fault matrix"), ("P", "implemented; not deployed"), ("P", "in-process only"), ("X", "CI enforcement"),
        ("P", "hard-constraint precedence property-tested; objective documented"), ("P", "drift + shadow/canary; calibration data needed"),
        ("I", "simulation non-executable by construction"), ("X", "exercises not run"),
        ("X", "no VCS here"), ("P", "version + matrix; matrix partial"), ("P", "SBOM + hashes; no signature/vuln report"),
        ("P", "config schema/revision; signed config evidence from authority needed"), ("I", "evidence/test_report.json"),
        ("P", "metric contract documented; alert rules as sketches"), ("X", "exercises not run"), ("X", "signed decision pending")]
    assert len(prog_codes) == len(program), (len(prog_codes), len(program))
    prog = [{"id": f"PROGRAM-{i + 1:02d}", "requirement": r.strip(), "status": CODES[c], "note": n}
            for i, (r, (c, n)) in enumerate(zip(program, prog_codes))]
    for p in prog:
        counts[p["status"]] += 1
    total = len(entries) + len(prog)
    manifest = {
        "schema": "PK_GAP14_CERTIFICATION_MANIFEST/1", "version": "4.3.0", "checklist": CHECKLIST.name,
        "items_total": total, "component_items": len(entries), "program_items": len(prog),
        "status_counts": dict(sorted(counts.items())),
        "certification_decision": {"verdict": "NO-GO",
                                   "reason": "P0 gates G01-G05 need live estate runs, certified pk_core, signed artifacts, named owners and security review",
                                   "signed_by": None},
        "per_component": {c: dict(sorted(v.items())) for c, v in sorted(per_comp.items())},
        "items": entries, "program": prog}
    (PKG / "CERTIFICATION_MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(total, dict(sorted(counts.items())))


if __name__ == "__main__":
    main()
