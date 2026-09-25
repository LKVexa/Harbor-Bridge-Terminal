# Exception / waiver / technical-debt register

| ID | INV55-GOV-WAIVERS | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

No waiver has been approved; every approver is `<UNASSIGNED>` with `status: PENDING-OWNER-APPROVAL` and every expiry is `<EXPIRY: TBD>`. CLOSED means fixed in code with cited evidence, not owner-approved.

Source of gate references: `evidence/exit_gate.json` (verdict **NO_GO**, 2026-09-23T07:04:43Z). "B" = blocking reason, "C" = condition; `#n` = checklist component.

## Open

| ID | Gap | Gate refs | Compensating control / evidence | Status |
|---|---|---|---|---|
| WVR-001 | Real Vault never run: no Vault binary and container registry blocked in the authoring environment; `tests/test_vault_real.py` (3 tests) skip; CI `vault-real` (1.17 only) not yet executed | B: 3 real-Vault skips, #15, #82; C: #16, #83 | `tests/test_vault_adapter.py` fake Vault over real HTTP+TLS; skip ≠ pass | OPEN |
| WVR-002 | `pk_core` not bundled; 3 conformance tests skip | B: 3 `test_component` skips; C: #35 | none | OPEN |
| WVR-003 | No artifact signing (GAP-07 key custody) | C: #42 | sha256 in `evidence/release_evidence.json`, `evidence/sbom.cdx.json` | OPEN |
| WVR-004 | No power/thermal measurement | C: #68 | method in power-thermal.md | OPEN |
| WVR-005 | Only single-host in-process benchmark; no soak, fleet-scale or profiling | C: #62, #63, #65, #69, #87 | `evidence/benchmark_baseline.json` | OPEN |
| WVR-006 | No engineering/security/operations approvals on any artifact | B: #38, #96; C: #2, #3, #4, #5, #8, #11, #62, #79, #90, #92, #93 | all docs Draft; `approvals` all PENDING in exit gate | OPEN |
| WVR-008 | Symmetric HS256 single workload key | B: #18 | key custody; freeze procedure | OPEN |
| WVR-010 | No multi-endpoint Vault failover | C: #55 | Vault HA behind LB | OPEN |
| WVR-012 | Scopes/retirements persisted per instance, not replicated | — | apply to every instance; `destroy=true` | OPEN |
| WVR-013 | Service does not auto-renew provider leases / Vault token | B: #15 | re-login at 0.67×TTL; `renew`/`renew_self` tested | OPEN |
| WVR-016 | SPIFFE/OIDC authenticators and peer/node identity not implemented; need identity issuer | B: #18, #41 | pluggable `Authenticator`; mTLS client cert to Vault | OPEN |
| WVR-017 | No integration with INV-59 policy service or INV-46 runtime | B: #19; C: #25 | local deny-by-default `PolicyEngine` | OPEN |
| WVR-019 | Encryption at rest is Vault seal/KMS owned by platform; no evidence | B: #45 | delegated (encryption.md) | OPEN |
| WVR-020 | Canary/staged rollout automation absent | B: #91 | manual plan; `ConfigController.rollback` | OPEN |
| WVR-021 | Restore drill against real Vault snapshot not performed | B: #94 | procedure in backup-restore.md | OPEN |
| WVR-022 | Runbooks not exercised by an operator | B: #95 | — | OPEN |
| WVR-023 | No real owners/on-call; branch protection and required reviewers not configured | B: #100; C: #1 | placeholder CODEOWNERS | OPEN |
| WVR-024 | Incident-response tabletop not held | B: #96 | — | OPEN |
| WVR-025 | `MASTER.md` absent from snapshot | C: #13 | master-workflow.md | OPEN |
| WVR-026 | No hash-pinned dependency lock (needs networked resolver run) | C: #34 | zero runtime deps; `jsonschema` pinned for tests; SBOM | OPEN |
| WVR-027 | Project LICENSE not chosen | C: #36 | — | OPEN |
| WVR-028 | CI pipeline defined but not executed on hosting CI | C: #37 | local runs: 131 pass, 6 skip, 0 fail | OPEN |
| WVR-029 | CPython cannot guarantee no transient secret copies | C: #49 | `SecretValue.wipe`; process isolation guidance | OPEN |
| WVR-031 | `pseudonymise()` not applied by any export pipeline | C: #50 | names absent from metrics | OPEN |
| WVR-032 | Batching not implemented | C: #66 | TTL cache | OPEN |
| WVR-033 | Log shipping, OTLP trace export, dashboards/alerts not deployed | C: #73, #74, #80 | in-process signals; rule specs in dashboards-alerts.md | OPEN |
| WVR-034 | No separate high-cardinality store; no infra-graph correlation | C: #75, #78 | `DecisionLedger`; digests on every decision | OPEN |
| WVR-035 | Real network partition against Vault HA not run | C: #88 | in-process partition/reconnect test | OPEN |
| WVR-036 | First recurring review not held | C: #97 | review-process.md | OPEN |
| WVR-030 | Contract SLO p99 < 5 ms not met under 16-way in-process concurrency (p99 21.4 ms, throughput 1.8k vs 4.3k ops/s; GIL + service RLock) | C: #62, #69 (related) | process-per-core scaling; low per-process concurrency | OPEN |

| WVR-037 | Expired/dropped leases do not wipe their `SecretValue` (shared with TTL cache); only `drain()` wipes | C: #49 (related) | process isolation; core dumps disabled | OPEN |
| WVR-038 | Idempotency/duplicate protection is single-instance; no cross-instance fencing | B: #58 | `expected_version` CAS at Vault | OPEN |

## Closed (code fixes; not owner-approved)

| ID | Gap | Evidence |
|---|---|---|
| WVR-007 | Scopes/retirements lost on restart | write-ahead `_save_state`; `tests/test_service_contract.py::LifecycleContract.test_scopes_and_retirements_survive_restart`, `test_state_write_failure_leaves_memory_unchanged` |
| WVR-009 | Quota keyed on unauthenticated fields | `tests/test_security_adversarial.py::Elevation.test_quota_charged_to_authenticated_tenant` |
| WVR-011 | Audit chain restarted on reboot | `audit.resume_from_file`, boot quarantine; `tests/test_config_audit_telemetry.py::AuditTests.test_file_sink_resume` |
| WVR-014 | Vault DR secondary reported reachable | `VaultProvider.health` |
| WVR-015 | Protocol family not matched to operation | `tests/test_service_contract.py::ResolveUseContract.test_unsupported_and_mismatched_protocol` |
| WVR-039 | Path traversal in names; unvalidated tenant/sub/roles claims; freeze by any tenant's operator (security review) | `tests/test_security_adversarial.py::Elevation.test_path_traversal_in_names_rejected`, `test_tenant_claim_cannot_contain_path_separator`, `Spoofing.test_malformed_signed_claims_are_unauthenticated_and_audited` |
| WVR-018 | Per-tenant policy overhead 2.73× (found by benchmark) | cached digest + per-tenant rule index in `PolicyEngine`; 0.99× in `evidence/benchmark_baseline.json` |

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-22 | Closed WVR-007/009/011/014/015; added WVR-012/013 |
| 4.3.0 | 2026-09-23 | Security review: WVR-037/038 open, WVR-039 closed |
| 4.3.0 | 2026-09-23 | Mapped every exit-gate blocking reason and condition; added WVR-016–036 |
