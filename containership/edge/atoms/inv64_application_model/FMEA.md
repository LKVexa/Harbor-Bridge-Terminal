# Failure-mode and effects analysis (MC-20; C051-C060)

Recovery objective for local failures: **RTO ≤ 1 s** to a consistent state after restart (`tools/faults.py RTO_S`, release-blocking). RPO for activation state: last committed revision (journal fsync). Owners are roles from ops/owners.json.

| ID | Component / failure | Detection signal | User-visible outcome | Retry? | Containment | Recovery | Test |
|---|---|---|---|---|---|---|---|
| FM-PARSE-1 | hostile/oversized/deep manifest | `manifest.*` codes, rejections metric | `rejected_before_activation` | no | per request; bounded cost | none needed | fuzz, ParserHardeningTest |
| FM-ADJ-1 | adjacent layer slow | deadline exceeded, latency histogram | `retryable_failure` (`deadline.exceeded`) | caller, with backoff | no partial bind | automatic when peer recovers | faults f01, integration |
| FM-ADJ-2 | adjacent layer down / connection reset | `admission.overloaded`, dependency failures | `retryable_failure` | yes (budgeted) | retry budget stops storms | automatic | f02 |
| FM-ADJ-3 | adjacent malformed response | `internal` + defect alert | `retryable_failure` | yes | unbind | page adjacent owner | f03 |
| FM-ADJ-4 | adjacent version out of range | `version.unsupported` | `rejected_before_activation` | no | before any call | upgrade per compatibility.json | f04 |
| FM-CFG-1 | process killed after PREPARE | recovery record `aborted` | none (old revision stays) | client may retry | journal | automatic on restart | f05 |
| FM-CFG-2 | process killed after COMMIT | recovery record `rolled_forward` | new revision active | no | journal | automatic on restart | f06 |
| FM-CFG-3 | bad config passes validation but breaks health (crash loop) | health probe false, auto-rollback metric | rolled back, candidate quarantined | only after re-approval | quarantine | operator re-approval | f11 |
| FM-CFG-4 | duplicate activation after restart | `activation.conflict` | refused | no | CAS | none | f12 |
| FM-CFG-5 | snapshot corrupted on disk | startup refuses (JSONDecodeError) | status blocked (host) | no | refuse to start | restore from backup (BACKUP_RESTORE.md) | f13, BackupReleaseTest |
| FM-CFG-6 | disk full during activation | OSError from journal/snapshot write | `internal`, no commit | yes after space freed | PREPARE not written ⇒ nothing changed | free space; restart | inspection (write-before-commit ordering) |
| FM-AUD-1 | audit sink unwritable | `inv64_audit_dropped_total`, `audit.events_dropped` status | ordinary ops continue (bounded buffer); critical ops refused | yes | buffer 1,000; `audit.loss` record chained on recovery | automatic drain | f07 |
| FM-TRUST-1 | identity/trust source down | `auth.trust_unavailable` | `retryable_failure` after cache TTL | yes | cached trust ≤ 300 s | automatic | f08 |
| FM-TIME-1 | clock skew beyond allowance | `auth.not_yet_valid` / `auth.expired` spikes | rejected | no | skew ±60 s | fix NTP | f09 |
| FM-POL-1 | authz policy missing/corrupt | `authz.policy_invalid`, status `policy.missing` | all requests denied (fail closed) | yes | last verified policy kept | activate a valid policy / rollback | f10 |
| FM-KEY-1 | KMS/key outage | `crypto.unavailable` | sealed writes refused | yes | no plaintext fallback | automatic | CryptoTest |
| FM-OVL-1 | conflicting / stale overlays | `overlay.*` | rejected before activation | no | merge refuses | fix overlays | OverlayActivationTest |
| FM-NET-1 | partition between site and control plane | stale desired revision, dependency stale | site keeps last healthy revision | — | local autonomy | reconcile to desired on reconnect | stress s7 |
| FM-SPLIT-1 | two writers for one target | `activation.conflict` for the loser | loser refused | — | CAS on `expected_active` (single-writer per target directory; distributed writers must use a fencing epoch = revision ID) | none | stress s3 |
| FM-LOAD-1 | burst beyond capacity | admission rejections, inflight at limit | `retryable_failure` + retry hint | yes | no queue | automatic | stress s4 |
| FM-TEL-1 | telemetry sink down | `inv64_telemetry_sink_errors_total` | none | — | bounded ring, errors counted | automatic | TelemetryTest |
| FM-DEF-1 | unexpected exception | code `internal`, alert A06 | `retryable_failure`, no success reported | yes | per request | page owner | ServiceTest (audit failure path) |

Degraded mode: when an optional dependency is unhealthy status is `degraded`
and all operations continue. Operations that are **blocked** in degraded
states: activation without a healthy audit sink, trust/policy changes without
audit, new trust establishment without the trust source, sealed writes without
the key service.

Unsafe conditions → quarantine/disable, never ambiguous operation: failed
health ⇒ quarantine; no known-good revision ⇒ refuse rollback and leave the
target blocked; operator emergency disable = add blocked reason
`emergency.disabled` (status blocked, readiness false).
