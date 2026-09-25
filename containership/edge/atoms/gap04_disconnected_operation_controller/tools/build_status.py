"""Build the requirements-traceability/status evidence for the GAP-04 missing-components checklist.

Inputs : the checklist markdown (path arg or tools/checklist_source.md), evidence/test_results.json,
         evidence/waivers.json.
Outputs: evidence/CHECKLIST_STATUS.json  (1 456 controls: status, evidence, reason, waivers)
         evidence/RTM.json                (original 100 GAP-04 checks -> modules/tests/status)
         GAP04_v4.3.0_Checklist_Status.md (the checklist with statuses, evidence and exit records filled)

Status legend follows the checklist: 'x' implemented AND evidence attached, '~' partial, '!' blocked,
'-' not applicable (needs approval), ' ' not started. Judgements are recorded here explicitly, per
component, so every status is reviewable in source control (C49-009, C49-017).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else PKG / "tools" / "checklist_source.md"

# ----------------------------------------------------------------------------- judgements
# Per component: statuses for items 001-005 and 006-020 (one char each), acceptance 021-026 use ACC
# unless overridden, implementation refs, tests, a gap note, and per-item notes.
T = "tests/"
C = {
 "01": ("xxxxx", "xxxxxxxxxx~x~~x", ["runtime/trust.py", "runtime/canonical.py", "runtime/crypto.py", "runtime/node.py:install_lease"],
        [T+"test_p0_lease_policy.py::LeaseEnvelope", T+"fixtures/golden_v1.json"],
        "Issuer-side custody/SLOs and FIPS evidence depend on the control-plane org.",
        {16: "health exposes lease id/watermark and verification-failure metrics by code; no explicit per-lease verification-status field",
         18: "issuer duties documented in THREAT_MODEL §7; key custody and signing-service SLOs belong to the control-plane owner (W-001/W-005)",
         19: "library/version pinned and recorded; FIPS mode not validated (W-005)"}),
 "02": ("xxx~!", "x~x~x~~~~x~xx~~", ["runtime/clock.py", "runtime/node.py:_now"], [T+"test_p0_durability.py::TrustedTime"],
        "Software HWM only; whole-disk rollback while partitioned is a documented residual risk (W-012).",
        {7: "HWM persisted in MAC'd journal frames; no TPM NV counter (W-012)", 9: "detected when a trusted anchor is below HWM; a full-disk restore is undetectable offline (R1)",
         11: "jumps beyond max_drift fail closed and are counted; small slews accepted without classification",
         12: "priority signed token > authenticated adapter > optional RTC; no multi-source quorum",
         13: "HWM frames are MAC'd with the node audit key; transplant together with keys.json is possible",
         14: "RTC reset, reboot, snapshot restore, rollback, jump tested; suspend/hibernate not; DST/timezone/leap irrelevant (integer UTC)",
         16: "rollback/jump rejections counted and logged; anchor transitions not individually audited",
         19: "documented in THREAT_MODEL §6; hardware requirements depend on W-012", 20: "reboot/rollback tests pass; whole-disk rollback residual (R1)"}),
 "03": ("x~x~!", "x~~~xxxxxx~~~~x", ["runtime/journal.py", "runtime/storage.py:atomic_write", "runtime/node.py:_recover"],
        [T+"test_p0_durability.py::JournalWAL", T+"test_crash_recovery.py"], "Qualified on one filesystem only; ENOSPC/fsync-error injection not real.",
        {7: "frames carry seq/gen/kind/prev/h/mac + decision bindings; no explicit per-frame schema version (file format PK_JOURNAL/1)",
         8: "tmp+fsync+rename+dir-fsync on POSIX; Windows equivalent present but unqualified (W-008)",
         9: "torn tail truncated, mid-file corruption fails closed; corrupt segments are not isolated/quarantined automatically",
         16: "10 named crash points + random SIGKILL; no real ENOSPC/fsync-failure/partial-sector injection",
         17: "torn tail, mid corruption, crash loops tested; missing/duplicated segments and old-snapshot rollback not",
         18: "utilization/bytes/seq exposed; oldest unreconciled age, segment count, corruption state not",
         19: "classification/retention in THREAT_MODEL §5; legal/forensic policy needs owner approval"}),
 "04": ("xxx~x", "~x~~~~xx~~x~~ ~", ["runtime/journal.py:verify_export", "runtime/node.py:reconnect"], [T+"test_p0_durability.py::JournalWAL"],
        "Hash chain + HMAC; no signed checkpoints, audit-key rotation, or site binding.",
        {6: "frame schema has seq/prev/h/gen/kind; actor/policy bindings live in decision bodies rather than a separate audit schema",
         8: "audit key in keys.json (0600), separate file, no TPM/HSM (W-005)", 9: "MAC'd anchor header on compaction; no periodic signed checkpoints",
         10: "deletion/insertion/modification/reorder detected; whole-frame tail truncation indistinguishable from crash (R3)",
         11: "generation bound per frame; site/device identity not bound into chain", 14: "export attached to reconciliation; resumable audit upload protocol not implemented",
         15: "delete/forge/MAC tests; not every field, key substitution or old-chain replay", 17: "audit head in reconciliation record; no chain-head metric",
         18: "retention documented; legal-hold process needs owner", 19: "not started: audit MAC key rotation with continuity", 20: "independent verifier exists; tail truncation and cross-device substitution gaps"}),
 "05": ("xxxx~", "~x~xxx~x~~~x~!x", ["runtime/trust.py:verify_policy", "runtime/node.py:install_policy"], [T+"test_p0_lease_policy.py::PolicyProvenance"],
        "Bundle format lacks activation window/dependencies; policy build pipeline belongs to GAP-13.",
        {6: "bundle has version, issuer, trust domain, activated_at, author/approver; no activation window, dependencies, explicit floor field",
         8: "signer/alg/digest/schema validated; activation conditions/dependency versions not", 12: "structural validation only; no semantic dry-run",
         14: "author/approver recorded; CI attestation/compiler/engine versions not", 15: "alteration, rollback, same-version reuse, digest mismatch tested; expired signer partially",
         16: "version and age in health; digest/activation time not", 18: "documented in RUNBOOK RB-04; emergency revocation of a bundle needs GAP-13 contract",
         19: "blocked: reproducible policy build pipeline is GAP-13's (W-002)"}),
 "06": ("x~~~~", "x~~x~~xx~x~~x~x", ["runtime/node.py:apply_revocations", "runtime/trust.py:verify_lease"], [T+"test_p0_lease_policy.py::RevocationEpoch", T+"test_p1_resilience_suites.py::FaultInjection"],
        "Single global epoch; epoch update API is authorized but the epoch value itself is not a signed message.",
        {7: "persisted in journal (software rollback resistance, W-012)", 8: "single authority epoch + lease-id + grant revocations; no per-scope domains",
         10: "documented only (issuer failover out of scope)", 11: "apply_revocations is authz-gated but the epoch value is not signed (DoS by authorized caller possible)",
         14: "stale lease replay + restart tested; snapshot rollback, concurrent updates, forged high epochs not",
         16: "watermark in health; lease epoch not separately", 17: "authorized API; no two-person control", 19: "documented in THREAT_MODEL; authority-service DR is upstream"}),
 "07": ("x~x~!", "xxxx~~xxx~xx~xx", ["runtime/node.py:_decide", "runtime/node.py:reconnect"], [T+"test_p0_reconcile_adapters.py::Idempotency", T+"test_crash_recovery.py"],
        "Dedupe window is per partition; retention semantics across partitions documented but not formally bounded.",
        {10: "local dedupe per open partition; server side only in reference GAP-05", 11: "replayed flag + E0601 for content mismatch; full duplicate-state semantics not enumerated",
         15: "dedupe index cleared after reconciliation; a reused request id in a later partition yields a new decision (different epoch)",
         18: "cross-version semantics stated in ADR-005 only"}),
 "08": ("xxx~~", "~~~-~~xx~x~~~ ~", ["runtime/node.py:reconnect", "runtime/node.py:_resolve_conflict", "runtime/adapters.py:ReferenceReplication"],
        [T+"test_p0_reconcile_adapters.py::Reconciliation", T+"test_crash_recovery.py::test_T_C31_reconcile_crashpoints"],
        "Authoritative-wins with compensate/quarantine; no merge functions, operator replay tool or vector clocks.",
        {6: "accepted/compensated/quarantined/in-progress/partial; superseded/rolled-back states not modeled", 7: "conflict = authoritative write on same subject after partition start; no per-type classes",
         8: "one rule for all classes (authoritative wins) documented in ADR-005", 9: "N/A proposed: no merge functions are offered; approval pending",
         10: "idempotent compensation via GAP-01; no preconditions", 11: "quarantined outcome recorded; later re-entry of the subject is not blocked",
         14: "per-batch ack digest; no authoritative version/vector/epoch in ack", 16: "partial batches, duplicates, conflicts, peer failure tested; lost-ACK partially",
         17: "flapping fault test exercises repeated reconnects; no formal convergence property", 18: "outcome/conflict metrics; backlog/oldest age not",
         19: "not started: operator inspection/replay tool", 20: "multi-day logical soak + crash suite; not a real multi-hour partition"}),
 "09": ("~xx~!", "~x~~  xx!!x~ ~x", ["runtime/adapters.py:ReferenceReplication", "runtime/node.py:_submit_with_retry"], [T+"test_p0_reconcile_adapters.py"],
        "Real GAP-05 not available (W-002); interface is submit-only.", {6: "submit/ack only; no authoritative read API", 8: "documented as eventual + authoritative-wins only",
         9: "contract version negotiated; trust domain/tenant integrity metadata not checked", 10: "not started", 11: "not started: version vectors", 14: "blocked: no real GAP-05 fixtures (W-002)",
         15: "blocked: no GAP-05 versions (W-002)", 17: "breaker state in health; watermark/lag not", 18: "not started", 19: "documented in MASTER §7; transport is external"}),
 "10": ("~xx~!", "~ xxx~~!~~~~x~x", ["runtime/adapters.py:ReachabilityMonitor"], [T+"test_p0_reconcile_adapters.py::Reachability", T+"test_p1_resilience_suites.py::FaultInjection"],
        "Single authenticated signal; network-layer sources belong to GAP-12.", {6: "unknown/up/degraded/down/flapping; asymmetric/captive not distinct", 7: "not started: single signal",
         11: "asymmetric case surfaces as reconciliation failure (tested)", 12: "probe rate is caller-driven", 13: "blocked: DNS/IP/VPN handling is GAP-12's",
         14: "loss/latency/flap/spoof tested; DNS/TLS/NAT not", 15: "only derived state exposed", 16: "partition entry logged; not every transition", 17: "no probe tracing", 19: "documented in MASTER"}),
 "11": ("~xx~!", "~~x--~x~~!x~~~x", ["runtime/adapters.py:ReferencePolicyEngine", "runtime/node.py:_decide"], [T+"test_p0_reconcile_adapters.py::Policy"],
        "Reference evaluator only; no decision cache.", {6: "evaluate(policy, kind, subject, tier); lease fingerprint/epochs not passed", 7: "kind/subject bounded; no full normalization",
         9: "N/A proposed: no decision caching", 10: "N/A proposed: no decision caching", 11: "engine exceptions surface as coded errors; unavailability not a distinct code",
         13: "in-process; mTLS helpers provided", 14: "allow/deny/stale/upgrade tested; timeout/malformed/failover not", 15: "blocked: needs authoritative GAP-13 fixtures (W-002)",
         17: "version/age in health; latency/cache metrics not", 18: "breaker only; no timeouts/cancellation", 19: "documented as reference only"}),
 "12": ("~xx~!", "~~xx~x~~!x ~x~x", ["runtime/adapters.py:CapabilityPlane"], [T+"test_p0_reconcile_adapters.py::Capabilities"],
        "Signed grants with epoch revocation; no resource scope/delegation.", {6: "grant/revocation contract; delegation constraints absent", 7: "subject/caps/epoch/expiry/issuer; no resource scope or delegation depth",
         10: "bound to site + epoch; not policy digest", 12: "grant id recorded on decision; caller identity not forwarded to supervisor", 13: "forged, wrong-site, stale-epoch tested; delegation N/A",
         14: "blocked: no PLN-07 versions (W-002)", 16: "not started", 17: "mTLS helpers; adapter in-process", 18: "grants are not persisted across restart by design (re-fetched)", 19: "documented in RUNBOOK RB-07"}),
 "13": ("~xx~!", "~x~x ~~~xx~~x x", ["runtime/adapters.py:ReferenceSupervisor", "runtime/node.py:_execute", "runtime/node.py:resume_effects"], [T+"test_p0_reconcile_adapters.py::Supervisor"],
        "Synchronous reference supervisor; no async operations or response integrity.", {6: "5 action kinds; freeze/quarantine operations not in contract", 8: "in-process; mTLS helpers",
         10: "not started: async operations", 11: "failures recorded durably; status query by key not implemented", 12: "fencing generation only; no workload generation precondition",
         13: "duplicates, stale generation, failure tested; failover/delay not", 16: "breaker state only", 17: "admission bounds decide(); compensation not bounded",
         19: "not started: response integrity"}),
 "14": ("xxx~~", "xx~x~~~xx~ ~ ~~", ["runtime/authz.py", "runtime/opsapi.py"], [T+"test_p0_reconcile_adapters.py::Authz", T+"test_p1_operations.py::HealthMetricsLogs"],
        "Deny-by-default SPIFFE authz; PKI lifecycle and IPC hardening external.", {8: "trust domain enforced; certificate lifetimes/rotation are PKI's", 10: "site scoping in envelopes; per-request tenant scoping not",
         11: "TLS stack enforces validity; only identity parsing tested", 12: "files 0600; no IPC surface", 15: "several boundaries tested, not all 14", 16: "not started: needs PKI fixtures",
         17: "decide denials logged with code; not every boundary", 18: "not started", 19: "break-glass = overrides (RUNBOOK RB-08)", 20: "partial until every boundary is covered"}),
 "15": ("xxx ~", "xxx~ ~~~~~x ~x~", ["runtime/storage.py:Keyring", "runtime/crypto.py", "runtime/backup.py"], [T+"test_p0_durability.py::EncryptionKeys", T+"test_p1_operations.py::BackupRestore"],
        "Keys beside data in the reference provider (W-005).", {9: "os.urandom keys in 0600 file; TPM/KMS seam only", 10: "not started: KEK/DEK separation", 11: "AAD binds seq + key id; site not bound",
         12: "documented", 13: "best-effort zeroization (CPython limits)", 14: "backups encrypted; swap/core-dump controls not", 15: "wrong key, rotation, corrupted tag, backup tested",
         17: "not started", 18: "documented in RUNBOOK RB-07/09", 20: "fails while keys sit beside data (W-005)"}),
 "16": ("x~x~~", "~~~x~~ x~~~ ~x~", ["runtime/fencing.py", "runtime/node.py:__init__"], [T+"test_p0_durability.py::Fencing", T+"test_p1_resilience_suites.py::Concurrency"],
        "Single-host fencing only (W-011).", {6: "one active per state directory; documented", 7: "local persisted generation, not authority-issued", 8: "journal + supervisor carry generation; reference GAP-05 does not check it",
         10: "OS lock only", 11: "acquire → recover → resume effects; no quiesce of old authority", 12: "not started: two hosts", 14: "simultaneous start (subprocess) + stale gen; VM clone not",
         15: "open logs generation", 16: "generation in health", 17: "not started", 18: "documented", 20: "single host only (W-011)"}),
 "17": ("x~x~!", "xxxx~xx~x~~x~~~", ["runtime/node.py:_recover", "controller.py:to_snapshot", "runtime/fencing.py"], [T+"test_p0_durability.py::Fencing", T+"test_p0_durability.py::NoSilentReset"],
        "Software rollback resistance only.", {10: "journal MAC; no hardware monotonic storage (W-012)", 13: "restore bumps generation; older authority watermark relies on control plane",
         15: "stale-generation errors carry both values; not every error", 16: "values in health; last transition time not", 18: "older-generation records reconcile normally; documented", 19: "documented in MASTER §5", 20: "image rollback residual (R1)"}),
 "18": ("xx~x~", "xxxxxxxxx~x~x~~", ["runtime/node.py:_commit", "runtime/journal.py", "runtime/storage.py:atomic_write"], [T+"test_crash_recovery.py", T+"test_p0_durability.py::AtomicTx"],
        "Crash points cover every write type but not every byte offset; real I/O faults not injected.", {15: "capacity exhaustion simulated; real ENOSPC/read-only fs/permission loss not", 17: "journal seq in health; recovery flag not",
         19: "POSIX assumptions documented; other OSes unqualified (W-008)", 20: "not exhaustive"}),
 "19": ("xxxxx", "~xxx~x~~xxxxxx~", ["runtime/errors.py", "docs/ERROR_CODES.md"], [T+"test_p0_lease_policy.py::ErrorModel", T+"test_p1_contracts_integration.py::Contracts"],
        "No correlation id/severity/retry-after fields.", {6: "code/category/retryable/http_status/details; no correlation id or severity", 10: "decide() wraps all; some lifecycle paths can still raise reference-controller exceptions",
         12: "retryable flag; no retry-after", 13: "epoch/generation in selected details only", 20: "not every path wrapped"}),
 "20": ("xxxx~", "~x~xxxx~~x~ x~x", ["runtime/journal.py:_admit", "runtime/node.py:_on_pressure", "runtime/node.py:clear_storage_freeze"], [T+"test_p0_durability.py::JournalWAL", T+"test_p0_durability.py::NoSilentReset"],
        "Journal budget + reserve; other budgets (logs/tmp) external.", {6: "journal + reserve budgets; logs/tmp budgets external", 8: "80% warning + freeze; no hysteresis", 13: "not qualified on quota/inode/RO fs",
         14: "fill-to-exhaustion test; not at every transition", 16: "utilization/bytes; write latency/compaction debt not", 17: "not started", 19: "archive on compaction; no prune tool"}),
 "21": ("xxxx~", "xxxx~x-x~xxxxxx", ["runtime/config.py", "docs/CONFIGURATION.md"], [T+"test_p1_operations.py::Config", T+"fixtures/config_prod_example.json"],
        "No layered precedence.", {10: "single document; no layering", 12: "N/A proposed: configuration contains no secrets", 14: "one config version exists"}),
 "22": ("xxxx~", "~xx~ x~~~~~~~ ~", ["runtime/config.py:ConfigManager"], [T+"test_p1_operations.py::Config"],
        "ConfigManager is not yet wired to hot-apply into a running node (restart-required).", {6: "validation before activation; no separate staging area", 9: "no ticket/change id field", 10: "not started",
         12: "documented", 13: "atomic writes; crash-during-activation not tested", 14: "invalid/repeat/rollback tested; concurrency not", 15: "history files; not journaled",
         16: "not exposed in health", 17: "optional signed config", 18: "rollout.py covers versions, not config", 19: "not started", 20: "restart-required activation"}),
 "23": ("xxxx~", "xx~xx~xxx~~~ x~", ["controller.py:validate_tier_schedule", "runtime/config.py"], [T+"test_p1_operations.py::Config", T+"test_p1_resilience_suites.py::FaultInjection"],
        "Schedule digest not bound to decisions.", {8: "per-site config within validation bounds; no central approval of bounds", 11: "config_version bound; schedule digest not",
         15: "tier in health; next threshold not", 16: "tier-transition metric; per-transition audit not", 17: "CONFIGURATION.md", 18: "not started", 20: "digest binding missing"}),
 "24": ("~xxx~", "xx~x~xxxx~~xx~x", ["runtime/node.py:request_override", "runtime/node.py:approve_override", "runtime/node.py:cancel_override"], [T+"test_p1_operations.py::Overrides"],
        "No ticket reference or signed override records.", {8: "reason/ttl/scope; no ticket reference", 10: "journal MAC protects records; not individually signed", 15: "journaled; 'use' events not",
         16: "expiry/two-person/role tested; reboot/connectivity loss not", 19: "process in INCIDENT_SEVERITY; not enforced"}),
 "25": ("xxxx~", "x~x~xxxx~~xx xx", ["runtime/node.py:health", "runtime/opsapi.py"], [T+"test_p1_operations.py::HealthMetricsLogs"],
        "Health shares the node lock.", {7: "reachability + breakers; key store/persistence partial", 9: "no build digest", 14: "several faults, not all combinations", 15: "health takes the node lock (can wait behind reconnect)", 18: "not started"}),
 "26": ("xxxx~", "~~xx~xxx~~x~~~~", ["runtime/observability.py"], [T+"test_p1_operations.py::HealthMetricsLogs"],
        "Default histogram buckets; limited histograms.", {6: "core counters; revocation/journal-write counters not", 7: "decision latency only", 10: "generic buckets, not SLO-derived",
         14: "cardinality/format tested; monotonicity/reset not", 15: "dashboard queries only", 17: "not tracked", 18: "backend policy", 19: "no golden examples", 20: "partial"}),
 "27": ("xxxx~", "xxxx~~x~xxx~x~~", ["runtime/observability.py:StructuredLogger"], [T+"test_p1_operations.py::HealthMetricsLogs"],
        "Synchronous logging.", {10: "synchronous writes", 11: "no recursion guard", 13: "backend policy", 17: "wall clock; no trusted-time quality field", 19: "RUNBOOK lists entry points", 20: "partial"}),
 "28": ("xxxx~", "x~~x x~ xx~~-~~", ["runtime/observability.py:TraceContext"], [T+"test_p1_operations.py::HealthMetricsLogs"],
        "Context propagation only; no spans/exporter.", {7: "no spans created", 8: "malformed headers replaced; baggage not handled", 10: "not started", 12: "retries share parent context",
         13: "not started", 16: "not tested across threads", 17: "documented", 18: "N/A proposed: no exporter", 19: "partial (trace id in decision + batch)", 20: "partial"}),
 "29": ("xxxx~", "xx~~x~ x~~x~~~~", ["ops/alerts.rules.yml", "ops/dashboard.grafana.json"], [T+"test_p1_operations.py::HealthMetricsLogs"],
        "Rules statically validated, not executed in Prometheus.", {8: "for-durations; no hysteresis", 9: "runbook + class; version/config not in annotations", 11: "site variable only",
         12: "not started", 14: "severity mapping; owners unassigned (W-001)", 15: "static validation only", 17: "partial", 18: "partial", 19: "process defined", 20: "partial"}),
 "30": ("xxxx~", "~~~xx~x ~~~ ~x~", ["runtime/resilience.py", "runtime/node.py:decide"], [T+"test_p1_operations.py::Backpressure", T+"test_p1_resilience_suites.py"],
        "Admission on decide only; no per-tenant fairness or jittered backoff.", {6: "decide() bounded; other work classes not queued", 7: "per-dependency breakers; no per-tenant limits", 8: "control frames get reserve; no queue priority",
         11: "retry budget; no jittered backoff", 13: "not started", 14: "storm/burst; slow disk/policy not", 15: "rejections + retries; queue wait not", 16: "not analysed", 17: "not started", 18: "CONFIGURATION.md"}),
 "31": ("xx~x!", "x~xx~xx~~!xx!x~", ["runtime/faults.py", "tests/crash_worker.py"], [T+"test_crash_recovery.py"],
        "No CI; one filesystem.", {7: "kill -9 and os._exit; no host reboot/power cut", 10: "resume_effects exists; not asserted after crash", 13: "normal + reconnect; low-storage/key-rotation not",
         14: "random rounds (6); more in qualification", 15: "blocked: one OS/filesystem (W-008)", 18: "blocked: no CI (W-007)", 20: "most transitions covered"}),
 "32": ("xx~x!", "~xxxxxx!xx~x~x~", ["runtime/adapters.py", "runtime/testing.py"], [T+"test_p1_resilience_suites.py::FaultInjection", "tests/perf/bench.py:storm"],
        "Adapter-level simulation, not packet-level.", {6: "adapter-level injection", 13: "blocked: DNS is GAP-12's", 16: "storm timings recorded", 18: "logical multi-day; not wall-clock", 20: "partial"}),
 "33": ("xx~x!", "x~xx~ -~~~ ~x ~", ["runtime/node.py (single RLock)"], [T+"test_p1_resilience_suites.py::Concurrency"],
        "Coarse lock serializes; limited race tooling in CPython.", {7: "decide vs reconnect raced; others not", 10: "not stressed concurrently", 11: "not started", 12: "N/A proposed: no race detector for CPython; coarse lock",
         13: "seeded, modest iterations", 14: "no deadlock observed; not proven", 15: "harness timeouts only", 16: "not started", 17: "health shares lock", 19: "not started", 20: "partial"}),
 "34": ("xx~x!", "xxx~xx~ x   ~ ~", ["runtime/canonical.py", "runtime/trust.py"], [T+"test_p1_resilience_suites.py::PropertyFuzz"],
        "Seeded fuzz without coverage tooling.", {9: "partial timestamp fuzz", 12: "bit-flip/deletion tests only", 13: "not started", 15: "not started", 16: "not started", 17: "not started", 18: "in-suite smoke; no CI", 19: "not started", 20: "partial"}),
 "35": ("xx~x!", "xxxx~ ~~ x!xx~~", ["docs/THREAT_MODEL.md"], [T+"test_p1_resilience_suites.py::Adversarial"],
        "No PKI/IPC attack tests; no pentest.", {10: "adapter escalation partially", 11: "not started", 12: "tamper yes; transplantation no", 13: "disk/oversize/queue; FDs/connections not",
         14: "not started", 16: "blocked: independent pentest + scanner (W-009)", 19: "process in REVIEW_PROCESS", 20: "partial"}),
 "36": ("xx~x!", "~x~xx~xx xx~x~~", ["schemas/", "runtime/schema.py"], [T+"test_p1_contracts_integration.py::Contracts", T+"fixtures/golden_v1.json"],
        "No adjacent N-1 matrix.", {6: "15 wire schemas; journal frames not schema-described", 8: "typical + invalid; not min/max/deprecated sets", 11: "4.2.0 views vs 4.3.0; adjacent N-1 not",
         14: "not started", 17: "migration guard test only", 19: "documented", 20: "partial"}),
 "37": ("xx~x!", "!!x~xx~!~x~x ~!", ["runtime/testing.py", "runtime/adapters.py"], [T+"test_p1_contracts_integration.py::Integration"],
        "Reference stack only (W-002, W-003).", {6: "blocked: real adjacent implementations (W-002)", 7: "blocked (W-002)", 9: "identity via principals; no real mTLS", 12: "asymmetric only", 13: "blocked (W-002)",
         14: "partial", 16: "reference only", 18: "not started", 19: "no CI", 20: "blocked (W-002)"}),
 "38": ("xx~x~", "x~~~x !x~~ x~!!", ["tests/perf/bench.py", "evidence/perf_baseline.json"], [T+"test_p1_resilience_suites.py::LatencyRegression"],
        "Container measurements only (W-010).", {7: "p50/p95/p99/max; p99.9 not", 8: "single-writer throughput; saturation not", 9: "CPU/RSS/bytes; FDs/IOPS not", 11: "not started: ablation",
         12: "blocked (W-010)", 14: "partial", 15: "proposed targets (SLO.md)", 16: "not started (only in-test regression guard)", 18: "max recorded; no tail analysis", 19: "blocked (W-010)", 20: "blocked (W-010)"}),
 "39": ("xx~x~", "~~~x~ ~~xx~ x ~", ["tests/perf/bench.py"], ["evidence/perf_baseline.json"],
        "Logical-time soak; not multi-day wall clock.", {6: "logical multi-day", 7: "3 logical days", 8: "admission test only", 10: "partial", 11: "not started", 12: "flapping test", 13: "peak RSS only",
         16: "documented equivalence only", 17: "not started", 19: "no prior baseline (4.2.0 had none)", 20: "partial"}),
 "40": ("xx~x~", "xxxx~~~~xxxxxx~", ["runtime/capacity.py", "docs/CAPACITY_MODEL.md"], ["evidence/perf_baseline.json"],
        "Coefficients from build host only.", {10: "aggregate CPU only", 11: "estimate", 12: "payload bytes only", 13: "per state dir; fleet bound by peer", 20: "needs representative hardware (W-010)"}),
 "41": ("xx~~ ", "x~~~~ ~~~ ~ ~x~", ["runtime/backup.py", "runtime/node.py:migrate_state"], [T+"test_p1_operations.py::BackupRestore"],
        "No site binding or forced post-restore reconciliation.", {7: "encrypted + digests; site binding not", 8: "stop-the-node or crash-consistent copy", 9: "generation bumped; authority watermark relies on control plane",
         10: "documented in RUNBOOK", 11: "not started", 12: "digests/schema/empty target; site/age not", 13: "chain verified; reconciliation not forced", 14: "framework + guard test",
         15: "not started", 16: "wrong key tested; corrupted/wrong-site not", 17: "not started", 18: "RPO/RTO need owner", 20: "partial"}),
 "42": ("~xxx~", "xxxxx~x ~~xxx x", ["runtime/node.py:quarantine", "runtime/node.py:release_quarantine"], [T+"test_p1_operations.py::Quarantine"],
        "Supervisor not instructed to freeze workloads.", {11: "storage freeze automatic; integrity failure refuses start", 13: "not started", 14: "generation not checked on release", 15: "reboot/role/binding tested", 19: "not exercised"}),
 "43": ("x~x~ ", "x~x~xx~x   ~~ ~", ["runtime/rollout.py"], [T+"test_p1_operations.py::Rollouts"],
        "Decision logic only; no deployment integration.", {7: "health/denials gates", 9: "documented", 12: "logic only", 14: "not started", 15: "not started", 16: "not started", 17: "history kept in object", 18: "documented", 19: "not started", 20: "partial"}),
 "44": ("x~x~x", "~x~~~x~ ~~~~x~!", ["COMPATIBILITY_MATRIX.json", "runtime/adapters.py:negotiate"], [T+"test_p1_contracts_integration.py::CompatAndRelease"],
        "Adjacent real versions unknown.", {6: "adjacent real versions null (W-002)", 8: "ranges partial", 9: "features partial", 10: "consistency test only", 12: "4.2.0→4.3.0 only",
         13: "not started", 14: "golden fixtures", 15: "code version only", 16: "waiver process", 17: "process", 19: "partial", 20: "blocked (W-002)"}),
 "45": ("x~x~x", "~~xx ~~ xxxx!x~", ["pyproject.toml", "requirements.lock", "runtime/release.py"], [T+"test_p1_contracts_integration.py::CompatAndRelease"],
        "Hashes pending (W-004).", {6: "no build id/commit (no VCS in candidate)", 7: "pins without hashes (W-004)", 10: "not started: wheelhouse", 11: "not tested", 12: "python marker only",
         13: "not started", 18: "blocked: no scanner/network (W-009)", 20: "hashes + offline install pending"}),
 "46": ("xx~~!", "x~~~x~!! ~x~~~~", ["runtime/release.py"], [T+"test_p1_contracts_integration.py::CompatAndRelease"],
        "Local signing key (W-006).", {7: "no wheel hashes/licenses", 8: "local builder id", 9: "ephemeral key (W-006)", 11: "tool exists; not in admission", 12: "blocked (W-006)", 13: "blocked (W-009)",
         14: "not started", 15: "not retained externally", 17: "RUNBOOK/VULN doc", 18: "runtime listed; no base image", 19: "partial", 20: "partial"}),
 "47": ("!xxx~", "!!!~~~!~!!!!~~!", ["docs/GOVERNANCE.md"], [], "No named people (W-001).", {}),
 "48": ("!xxx~", "xxxxx!~~xx ~x~~", ["docs/ADR/"], [T+"test_p2_governance.py"], "ADRs proposed, not accepted.",
        {11: "blocked (W-001)", 12: "git history not available in candidate", 13: "convention stated", 16: "not started", 17: "process", 19: "process"}),
 "49": ("!xxx~", "xxxx~~~xxx!xx~~", ["tools/build_status.py", "evidence/CHECKLIST_STATUS.json", "evidence/RTM.json"], [T+"test_p2_governance.py"],
        "No reviewer approvals (W-001).", {10: "versioned per release; no history yet", 11: "local run ids", 12: "orphans flagged for requirements only", 16: "blocked (W-001)", 19: "process", 20: "partial"}),
 "50": ("!xxx~", "xxxxxxxxxx~~!~~", ["docs/SLO.md"], [], "Targets proposed only.", {16: "partial", 17: "dashboard panels", 18: "blocked (W-001)", 19: "process", 20: "pending approval"}),
 "51": ("!xxx~", "x~xxxxxx~xx!~~~", ["docs/INCIDENT_SEVERITY.md", "docs/RUNBOOK.md"], [], "Not exercised.",
        {7: "roles only; no paging targets", 14: "outline only", 17: "blocked: needs people (W-001)", 18: "requirement stated", 19: "process", 20: "pending exercises"}),
 "52": ("!xxx~", "~xxxxxxxxx~x~~~", ["docs/VULNERABILITY_AND_EOL.md"], [], "No security contact or scan (W-001/W-009).",
        {6: "security contact unassigned", 16: "process", 18: "SBOM + version in health", 19: "process", 20: "not tested"}),
 "53": ("!xxx~", "xx~xxxxxxx~~~x~", ["docs/REVIEW_PROCESS.md"], [], "Reviewers unassigned.", {8: "roles only (W-001)", 16: "process", 17: "gate integration only", 18: "requirement stated", 20: "no reviews held yet"}),
 "54": ("!xxx~", "xx!~xx~x~~xxxx~", ["docs/WAIVERS.md", "evidence/waivers.json"], [T+"test_p2_governance.py"], "Waivers proposed, unapproved.",
        {8: "blocked (W-001)", 9: "compensating controls described, deployment evidence partial", 12: "tracking field only", 14: "convention stated", 15: "process", 20: "visible but not approved"}),
 "55": ("!xxx~", "xxxx~xx~xx ~~x~", ["runtime/gate.py", "evidence/gate_decision.json"], [T+"test_p2_governance.py::Gate"],
        "Gate implemented; currently NO_GO.", {10: "archive digest + environment; no source commit (no VCS)", 13: "decision document unsigned", 16: "not started", 17: "documented in VULNERABILITY_AND_EOL", 18: "retention policy pending", 20: "returns NO_GO today"}),
 "56": ("~xxxx", "xxxxxxxxxxxxx!~", ["MASTER.md", "tools/check_docs.py"], [T+"test_p2_governance.py::Docs"], "Master authored; approval pending.", {19: "blocked (W-001)", 20: "pending approval"}),
}
ACC = "~x~!x~"          # 021 ADR approved? / 022 refs mapped / 023 release CI / 024 security review / 025 runbook / 026 RTM approved
ACC_NOTES = {21: "ADR drafted in docs/ADR (status: proposed); approval requires W-001", 23: "all suites pass locally (evidence/test_results.json); no release CI (W-007)",
             24: "no independent security review yet (W-009)", 26: "listed in CHECKLIST_STATUS/RTM; reviewer approval missing (W-001)"}
NOT_OPS = {"47", "48", "49", "53", "54", "56"}   # 025 health/runbook not applicable-ish -> partial
GENERIC = {"~": "partially implemented", "!": "blocked", " ": "not started in 4.3.0", "-": "not applicable (rationale recorded; approval pending)"}
LEGEND = {"x": "[x]", "~": "[~]", "!": "[!]", " ": "[ ]", "-": "[-]"}


def parse(src: Path):
    s = src.read_text()
    comps = {}
    for m in re.finditer(r"^## (\d\d)\. (.+?)\n\n\*\*Priority:\*\* (P\d)  \n\*\*Control family:\*\* (.+?)  ", s, re.M):
        comps[m.group(1)] = {"title": m.group(2).strip(), "priority": m.group(3), "family": m.group(4).strip()}
    items = [(c, int(i), t) for c, i, t in re.findall(r"\*\*GAP04-C(\d\d)-(\d\d\d)\*\* — (.+)", s)]
    return s, comps, items


def main():
    src, comps, items = parse(SRC)
    waivers = json.loads((PKG / "evidence" / "waivers.json").read_text())["waivers"]
    tests = json.loads((PKG / "evidence" / "test_results.json").read_text()) if (PKG / "evidence" / "test_results.json").exists() else {}
    run = tests.get("run_id", "local-unrecorded")

    def waivers_for(comp, n):
        out = []
        for w in waivers:
            for c in w["controls"]:
                if c in (f"C{comp}", f"C{comp}-{n:03d}") or (c.startswith("*-") and c[2:] == f"{n:03d}"):
                    out.append(w["id"])
        return sorted(set(out))

    controls = {}
    for comp, n, text in items:
        uni, spec, impl, tst, gap, notes = C[comp]
        if n <= 5:
            st = uni[n - 1]
        elif n <= 20:
            st = spec[n - 6]
        else:
            st = ACC[n - 21]
            if n == 25 and comp in NOT_OPS:
                st = "~"
        note = notes.get(n) if 6 <= n <= 20 else ACC_NOTES.get(n)
        if st != "x" and not note:
            note = GENERIC[st] + ("; " + gap if gap else "")
        ev = []
        if st in "x~":
            ev = impl + tst + ([f"evidence/test_results.json#{run}"] if tst else [])
        wv = waivers_for(comp, n)
        if n in (23,):
            wv = sorted(set(wv + ["W-007"]))
        if n in (21, 26):
            wv = sorted(set(wv + ["W-001"]))
        if n == 24:
            wv = sorted(set(wv + ["W-009"]))
        if st == "!" and not wv:
            wv = ["W-001"] if comp in {"47", "48", "49", "50", "51", "52", "53", "54", "55", "56"} or n == 1 else wv
        controls[f"GAP04-C{comp}-{n:03d}"] = {"status": st, "text": text, "evidence": ev, "note": note, "waivers": wv,
                                              "verified_on": tests.get("date") if st == "x" else None, "approved_by": None}
    summary = {}
    for comp, meta in comps.items():
        sts = [v["status"] for k, v in controls.items() if k[7:9] == comp]
        cnt = {s: sts.count(s) for s in "x~!- "}
        final = "Verified" if cnt["x"] == len(sts) else ("Blocked" if cnt["!"] and meta["priority"] == "P0" and cnt["!"] > 2 else "In progress")
        summary[comp] = {**meta, "counts": {"x": cnt["x"], "~": cnt["~"], "!": cnt["!"], "-": cnt["-"], " ": cnt[" "]},
                         "final_status": final, "go_impact": {"P0": "Blocking", "P1": "Required evidence", "P2": "Governance"}[meta["priority"]],
                         "implementation": C[comp][2], "tests": C[comp][3], "gap": C[comp][4],
                         "waivers": sorted({w for k, v in controls.items() if k[7:9] == comp for w in v["waivers"]})}
    tot = {s: sum(1 for v in controls.values() if v["status"] == s) for s in "x~!- "}
    doc = {"schema": "PK_GAP04_CHECKLIST_STATUS/1", "checklist_version": "1.0.0", "baseline": "4.2.0", "implementation": "4.3.0",
           "generated": tests.get("date"), "test_run": run, "legend": {"x": "implemented + evidence", "~": "partial", "!": "blocked", "-": "N/A (approval pending)", " ": "not started"},
           "totals": tot, "components": summary, "controls": controls}
    (PKG / "evidence" / "CHECKLIST_STATUS.json").write_text(json.dumps(doc, indent=1))

    # ---- RTM for the original 100 checks
    ck = json.loads((PKG / "CHECKLIST.json").read_text())["items"]
    M = {1: ("C56", "MASTER.md"), 2: ("C56", "MASTER.md"), 3: ("C56 C09 C10 C11 C12 C13", "MASTER.md"), 4: ("C01 C06", "MASTER.md"),
         5: ("C56", "MASTER.md"), 6: ("C01 C14", "runtime/trust.py"), 7: ("C56", "contract.py"), 8: ("C56", "MASTER.md"),
         9: ("C47", "docs/GOVERNANCE.md"), 10: ("C48", "docs/ADR/README.md"), 11: ("C56", "MASTER.md"), 12: ("C56 C23", "MASTER.md"),
         13: ("C50 C38", "docs/SLO.md"), 14: ("C19 C08", "runtime/errors.py"), 15: ("C23 C56", "controller.py"), 16: ("C36 C44", "COMPATIBILITY_MATRIX.json"),
         17: ("C40 C30", "docs/CAPACITY_MODEL.md"), 18: ("C10 C32", "runtime/adapters.py"), 19: ("C56 C19", "MASTER.md"), 20: ("C49", "evidence/RTM.json"),
         21: ("C14 C36", "runtime/authz.py"), 22: ("C36", "schemas/"), 23: ("C14", "runtime/authz.py"), 24: ("C14 C12", "runtime/authz.py"),
         25: ("C07 C30", "runtime/resilience.py"), 26: ("C19", "runtime/errors.py"), 27: ("C44 C36", "runtime/adapters.py"), 28: ("C30 C40", "runtime/canonical.py"),
         29: ("C36", "tests/fixtures/golden_v1.json"), 30: ("C37", "tests/test_p1_contracts_integration.py"), 31: ("C44 C45", "requirements.lock"),
         32: ("C21 C45", "runtime/config.py"), 33: ("C21", "runtime/config.py"), 34: ("C21 C22", "runtime/config.py"), 35: ("C21", "runtime/config.py"),
         36: ("C22", "runtime/config.py"), 37: ("C22 C18", "runtime/config.py"), 38: ("C22 C43", "runtime/rollout.py"), 39: ("C21 C27", "runtime/observability.py"),
         40: ("C17 C56", "runtime/node.py"), 41: ("C35", "docs/THREAT_MODEL.md"), 42: ("C14 C12", "runtime/authz.py"), 43: ("C14 C15", "runtime/authz.py"),
         44: ("C14 C01 C10", "runtime/trust.py"), 45: ("C05 C46", "runtime/trust.py"), 46: ("C14 C15", "runtime/authz.py"), 47: ("C15 C14", "runtime/storage.py"),
         48: ("C02 C01 C11", "runtime/clock.py"), 49: ("C04", "runtime/journal.py"), 50: ("C35", "tests/test_p1_resilience_suites.py"),
         51: ("C56 C31", "MASTER.md"), 52: ("C25", "runtime/node.py"), 53: ("C30", "runtime/resilience.py"), 54: ("C30", "runtime/resilience.py"),
         55: ("C16", "runtime/fencing.py"), 56: ("C25 C30", "runtime/node.py"), 57: ("C03 C18 C31", "runtime/journal.py"), 58: ("C16 C07", "runtime/fencing.py"),
         59: ("C42 C24", "runtime/node.py"), 60: ("C31 C32", "tests/test_crash_recovery.py"), 61: ("C38", "evidence/perf_baseline.json"), 62: ("C38 C50", "docs/SLO.md"),
         63: ("C38 C39", "tests/perf/bench.py"), 64: ("C38", "tests/perf/bench.py"), 65: ("C38", "docs/CAPACITY_MODEL.md"), 66: ("C38", "docs/CAPACITY_MODEL.md"),
         67: ("C30 C20", "runtime/resilience.py"), 68: ("C38", "docs/CAPACITY_MODEL.md"), 69: ("C40", "runtime/capacity.py"), 70: ("C38 C55", "runtime/gate.py"),
         71: ("C25", "runtime/opsapi.py"), 72: ("C26", "runtime/observability.py"), 73: ("C27", "runtime/observability.py"), 74: ("C28", "runtime/observability.py"),
         75: ("C27 C26", "runtime/observability.py"), 76: ("C08 C11", "runtime/node.py"), 77: ("C08 C49", "runtime/node.py"), 78: ("C43 C46", "runtime/release.py"),
         79: ("C27 C28", "docs/THREAT_MODEL.md"), 80: ("C29", "ops/alerts.rules.yml"), 81: ("C34", "tests/test_controller.py"), 82: ("C36", "tests/test_p1_contracts_integration.py"),
         83: ("C37", "tests/test_p1_contracts_integration.py"), 84: ("C44 C36", "COMPATIBILITY_MATRIX.json"), 85: ("C34", "tests/test_p1_resilience_suites.py"),
         86: ("C33", "tests/test_p1_resilience_suites.py"), 87: ("C35", "tests/test_p1_resilience_suites.py"), 88: ("C39", "tests/perf/bench.py"),
         89: ("C32 C41", "tests/test_p1_resilience_suites.py"), 90: ("C55", "runtime/gate.py"), 91: ("C50", "docs/SLO.md"), 92: ("C43 C42", "runtime/rollout.py"),
         93: ("C44", "COMPATIBILITY_MATRIX.json"), 94: ("C52", "docs/VULNERABILITY_AND_EOL.md"), 95: ("C41", "runtime/backup.py"), 96: ("C51", "docs/RUNBOOK.md"),
         97: ("C51", "docs/INCIDENT_SEVERITY.md"), 98: ("C53", "docs/REVIEW_PROCESS.md"), 99: ("C54", "docs/WAIVERS.md"), 100: ("C55", "runtime/gate.py")}
    NOTE = {64: "per-tenant overhead not measured", 66: "optimizations limited to batching", 68: "power not measured (W-010)",
            77: "decision records carry bindings + reason; no dedicated explain UI", 78: "no live infrastructure-graph correlation",
            43: "no sandboxing of ambient OS authority", 46: "per-site isolation only; tenant isolation delegated"}
    rtm = []
    for it in ck:
        comps_, art = M[it["ordinal"]]
        comps_ = comps_.split()
        sts = [summary[c[1:]]["counts"] for c in comps_]
        x = sum(s["x"] for s in sts); tot_ = sum(sum(s.values()) for s in sts)
        rtm.append({"check_id": it["check_id"], "dimension": it["dimension"], "requirement": it["requirement"],
                    "artifacts": [art], "components": comps_, "status": "partial",
                    "verified_share": round(x / tot_, 3) if tot_ else 0, "note": NOTE.get(it["ordinal"]),
                    "owner": None, "reviewer": None})
    (PKG / "evidence" / "RTM.json").write_text(json.dumps({"schema": "PK_GAP04_RTM/1", "version": "4.3.0", "items": rtm}, indent=1))

    # ---- annotated checklist
    out = []
    lines = src.splitlines()
    cur = None
    for line in lines:
        m = re.match(r"^## (\d\d)\. ", line)
        if m:
            cur = m.group(1)
        m = re.match(r"^- \[ \] \*\*(GAP04-C\d\d-\d\d\d)\*\* — (.+)$", line)
        if m:
            c = controls[m.group(1)]
            out.append(f"- {LEGEND[c['status']]} **{m.group(1)}** — {m.group(2)}")
            bits = []
            if c["evidence"]:
                bits.append("Evidence: " + ", ".join(f"`{e}`" for e in c["evidence"][:4]))
            if c["note"]:
                bits.append("Note: " + c["note"])
            if c["waivers"]:
                bits.append("Waiver(s): " + ", ".join(c["waivers"]))
            if bits:
                out.append("  - " + " · ".join(bits))
            continue
        if cur and line.startswith("- **Owner:**"):
            s_ = summary[cur]
            out += [f"- **Owner:** ________ (unassigned — W-001)", f"- **Reviewer/approver:** ________ (unassigned — W-001)",
                    "- **Target release:** 4.3.0", f"- **Evidence bundle / CI run:** `evidence/test_results.json` run `{run}` (local; no release CI — W-007)",
                    f"- **Waiver(s):** {', '.join(s_['waivers']) or 'none'}",
                    f"- **Status:** {s_['final_status']} ({s_['counts']['x']} verified / {s_['counts']['~']} partial / {s_['counts']['!']} blocked / {s_['counts'][' ']} not started / {s_['counts']['-']} N/A)",
                    f"- **GO impact:** {s_['go_impact']}", f"- **Implementation:** {', '.join('`'+i+'`' for i in s_['implementation'])}",
                    f"- **Remaining gap:** {s_['gap']}"]
            cur = cur + "!"
            continue
        if cur and cur.endswith("!") and re.match(r"^- \*\*(Reviewer/approver|Target release|Evidence bundle|Waiver|Status|GO impact)", line):
            continue
        out.append(line)
    head = [f"> **Status run:** GAP-04 4.3.0 against checklist 1.0.0 · generated {tests.get('date')} from `tools/build_status.py` · test run `{run}`",
            f"> **Totals:** {tot['x']} verified [x] · {tot['~']} partial [~] · {tot['!']} blocked [!] · {tot[' ']} not started [ ] · {tot['-']} N/A pending approval [-] — of {len(controls)} controls.",
            "> **Production gate:** NO_GO (see `evidence/gate_decision.json`). A checkbox is [x] only where code/tests/artifacts exist and were run; nothing is marked complete on narrative alone.", ""]
    txt = "\n".join(out)
    txt = txt.replace("### Purpose", "\n".join(head) + "\n### Purpose", 1)
    (PKG / "GAP04_v4.3.0_Checklist_Status.md").write_text(txt + "\n")
    # ---- residual-gap register (generated from the same data so it cannot drift)
    L = ["# GAP-04 — Residual Gaps After the v4.3.0 Implementation Pass", "",
         "Replaces the 4.2.0 register. Every one of the 56 components now has implementation and/or governance artifacts; none is fully verified, because each still needs named approval, release-CI evidence, independent security review, or real adjacent-layer integration. Per-control detail: `evidence/CHECKLIST_STATUS.json` and `GAP04_v4.3.0_Checklist_Status.md`. Generated by `tools/build_status.py`.", "",
         f"**Totals ({len(controls)} controls):** {tot['x']} verified · {tot['~']} partial · {tot['!']} blocked · {tot[' ']} not started · {tot['-']} N/A pending approval.", "",
         "| # | Component | Pri | Status | Verified | Partial | Blocked | Not started | Remaining gap | Waivers |", "|---|---|---|---|---|---|---|---|---|---|"]
    for k, c_ in summary.items():
        n_ = c_["counts"]
        L.append(f"| {k} | {c_['title']} | {c_['priority']} | {c_['final_status']} | {n_['x']} | {n_['~']} | {n_['!']} | {n_[' ']} | {c_['gap']} | {', '.join(c_['waivers'])} |")
    L += ["", "## What engineering cannot close alone",
          "- **W-001** named owners/approvers/reviewers (every exit record, ADR, SLO, waiver and the GO decision).",
          "- **W-002/W-003** real GAP-01/05/12/13, PLN-07 and `pk_core` builds for integration and conformance.",
          "- **W-005/W-006/W-012** hardware-backed keys, HSM release signing, hardware monotonic counters.",
          "- **W-007/W-008/W-009/W-010** release CI, multi-platform qualification, independent security review and scans, representative edge hardware.",
          "", "The formal gate (`runtime/gate.py`) returns **NO_GO** until these are resolved."]
    (PKG / "MISSING_COMPONENTS.md").write_text("\n".join(L) + "\n")
    print(json.dumps(tot))


if __name__ == "__main__":
    main()
