# INV-68 threat model 4.3.0 (MC-13; C041; feeds MC-16)

**Status:** DRAFT — security_owner unassigned; not yet reviewed (ops/REVIEWS.json).
**Method:** STRIDE per trust boundary; each threat → control → test/evidence.

## Assets

A1 placement integrity (no overcommit, correct hosts) · A2 configuration (headroom,
overcommit, limits, quotas) · A3 audit ledger · A4 trust-root keys (HMAC token keys,
audit MAC/anchor key, release signing key) · A5 tenant confidentiality (workload
names, lineage) · A6 availability of packing for SCH-01.

## Actors

External caller with a valid scheduler token (possibly compromised tenant) ·
caller without credentials · malicious or buggy upstream (INV-67) · compromised
capacity source · operator (insider) · stale/duplicate controller · attacker with
read access to logs · attacker with write access to the state directory.

## Trust boundaries (data flow)

```
 SCH-01/INV-67 ──token+request──▶ [B1 service boundary] ──▶ engine (pure)
 capacity source ──snapshot──────▶ [B2 dependency boundary]
 operator/controller ──control───▶ [B3 control boundary] ──▶ ConfigStore (disk) [B4 state boundary]
 service ──records──────────────▶ audit ledger (disk) [B4]      logs/metrics ──▶ [B5 telemetry export]
```

## Threats

| ID | STRIDE | Boundary | Threat | Control | Test / evidence |
|---|---|---|---|---|---|
| T1 | S | B1 | forged or wrong-key token | HMAC-SHA256 verify, kid lookup, fail closed | `test_MC06_forged_expired_replayed_and_wildcard_tokens_refused` |
| T2 | S/R | B1 | token replay | single-use nonce within validity window | same test; STRESS S5 (16-thread replay race) |
| T3 | E | B1 | scheduler token minted with admin capabilities | per-kind capability ceiling | `test_MC06_valid_token_authenticates_with_ceiling` |
| T4 | I/E | B1 | cross-tenant packing / data read | tenant scope check; per-request packing; tenant-scoped idempotency | `test_MC06_tenant_boundary`; INTEGRATION SCH01 refusal |
| T5 | T | B1 | hostile input (NaN, bool, huge numbers, deep nesting, unknown fields) corrupting accounting | strict validation, finite floats, unknown-field refusal | FUZZ (3000 service + 3000 engine cases, 0 findings); regression fixtures |
| T6 | D | B1 | resource exhaustion (huge batches, request floods) | payload/workload/name limits, admission queue, tenant quotas | `test_MC07_limits_*`, `test_MC05_tenant_quotas`, FAULTS F13, STRESS S1 |
| T7 | D | B1 | algorithmic complexity attack (one-host-per-workload batches) | closed-host pruning; worst case measured | PERF worst-5000 (43 ms p50 vs 51 s in 4.2.0) |
| T8 | T | B2 | stale or spoofed capacity (partition, replayed snapshot, future timestamp) | staleness bound, future-skew bound, breaker | FAULTS F01–F03 |
| T9 | T/E | B3 | unauthorised config change or freeze | capabilities `config:*`, `control:freeze`; audit fail-closed | `test_MC20_*`, `test_MC15_config_change_fails_closed_without_audit` |
| T10 | T | B3 | split brain: stale controller overwrites config | epoch fence + CAS + inter-process lock | FAULTS F10; STRESS S4/S7 |
| T11 | T | B4 | on-disk config tampering | digest-addressed snapshots re-verified on load; tampered backups refused | FAULTS F07; `test_MC37_backup_restore_round_trip_and_tamper_detection` |
| T12 | R/T | B4 | audit record deletion/edit/truncation | hash chain + optional HMAC + sealed anchor | `test_MC15_pack_decisions_are_audited_and_chain_verifies` |
| T13 | R | B4 | audit sink outage hides actions | bounded buffer, counted loss + `audit.loss` record, fail-closed for policy changes | FAULTS F05/F06 |
| T14 | I | B5 | secrets or tenant data in logs/errors/metrics | central redaction, allow-listed labels, cardinality cap, secret scan | `test_MC11_*`, SECRET_SCAN, FUZZ secret-echo oracle |
| T15 | I | B5 | log injection | JSON encoding escapes control characters | `test_MC11_structured_logs_redact_and_escape_injection` |
| T16 | T | supply chain | tampered release artifact | SHA256SUMS + Ed25519 DSSE provenance; managed signer required for GO | RELEASE_VERIFY (FAIL until managed signer) |
| T17 | I | side channel | timing of token verification leaks MAC bytes | `hmac.compare_digest` | code review (auth.py) |
| T18 | E | engine | escape/sandbox | pure Python, no eval/exec/subprocess/network in runtime modules | `test_no_bare_asserts_in_runtime_source` (AST scan) + review; not an isolation boundary |

## Residual risks (need owner acceptance)

* R1 shared-secret HMAC trust root (DEBT-001) — key compromise allows minting until rotation.
* R2 in-process idempotency/rate state (DEBT-002) — multi-replica deployments.
* R3 the state directory is trusted for availability (an attacker who can delete it causes NOT_READY; tampering is detected, deletion is not prevented).
* R4 side channels beyond T17 (cache/timing of packing itself) are out of scope.

## Review

Review cadence 180 days (ops/REVIEWS.json). Any new boundary, dependency or
capability requires a threat-model update in the same change.
