# GAP-04 Disconnected-Operation Controller — Master Source

**Document version:** 4.3.0
**Software series:** GAP-04 4.x (Post-Kubernetes Master Prompt & Workflow Series v4.0.0, group 04_Gap_Subsystems)
**Status:** authored 2026-09-22 for 4.3.0 — **pending review/approval** by architecture, security, operations and component owner (W-001). Until approved, this document is authoritative for *what is implemented* and *what is required*, not a record of acceptance.
**Correction (C56-016):** the 4.2.0 README claimed a bundled `MASTER.md`; it was absent from that archive. This file is newly authored from the 4.2.0 contract (`contract.py`), the 100-item `CHECKLIST.json`, the 56-component missing-components register, and the 4.3.0 implementation. No parent-series master was available to recover.

## 1. Normative vs informative
Sections 3–10 are **normative**: statements using MUST / MUST NOT are requirements, verified by the tests named in `evidence/CHECKLIST_STATUS.json`. Sections 2, 11 and 12 are informative. Where this document and code disagree, it is a defect in one of them; `tools/check_docs.py` and the contract tests fail CI on drift that they can detect.

## 2. Purpose, scope and non-goals
GAP-04 owns site behaviour while the control plane is unreachable: it installs bounded, signed autonomy leases; narrows local authority as a partition ages; refuses unsafe local decisions; records every local decision durably and tamper-evidently; and reconciles them honestly on reconnect.
**Non-goals:** transport/NAT traversal (GAP-12), state replication semantics (GAP-05), policy authorship (GAP-13), node lifecycle (GAP-01), capability issuance (PLN-07), guaranteeing correctness of decisions taken on stale policy, replacing the control plane.

## 3. Invariants (normative)
* **I1** No decision is accepted without a verified, unexpired, unrevoked lease whose scope equals the site scope and whose policy digest equals the verified active policy.
* **I2** No decision exceeds lease capabilities ∩ tier permissions ∩ policy ∩ (PLN-07 grant, when enabled). Operator overrides can only narrow.
* **I3** Local decisions are legal only while partitioned; lease/policy/trust changes are legal only while reachable (authenticated) and after the partition is reconciled.
* **I4** A decision is acknowledged only after its frame is fsync'ed; every acknowledged decision appears in the reconciliation record.
* **I5** Safety time never goes backwards; lease age, policy age and partition duration cannot be reset by reboot or clock manipulation.
* **I6** Authority epoch, policy version, trust-bundle version and controller generation are monotonic and persisted.
* **I7** A stale or duplicate controller instance cannot append, execute, or reconcile.
* **I8** Every failure crossing a boundary carries a stable `GAP04-Ennnn` code.

## 4. Architecture overview
```
 control plane ──signed lease/policy/trust/time/heartbeat/grants──▶ DisconnectedNode (runtime/node.py)
                                                                    ├─ trust.py      verify leases/policies (Ed25519, PK_CANON/1)
                                                                    ├─ clock.py      trusted time + HWM
                                                                    ├─ controller.py tier state machine (reference, dependency-free)
                                                                    ├─ journal.py    WAL + hash chain + HMAC (+AES-GCM)
                                                                    ├─ fencing.py    OS lock + generation
                                                                    ├─ adapters.py   GAP-12 / GAP-13 / PLN-07 / GAP-01 / GAP-05
                                                                    ├─ authz.py      mTLS SPIFFE identities, deny-by-default
                                                                    ├─ observability.py / opsapi.py  metrics, logs, traces, /healthz
                                                                    └─ config.py, rollout.py, backup.py, release.py, gate.py
```
Data/control flow for one offline decision: authz → trusted time → idempotency check → quarantine/override → lease + policy binding → policy eval (GAP-13) → grant check (PLN-07) → controller tier check → **WAL frame (fsync)** → supervisor command with fencing token (GAP-01) → effect frame.

### 4.1 Trust boundaries
(1) network ↔ node: every inbound authority object is signed and purpose-bound; heartbeats are nonce-challenged. (2) caller ↔ node: mTLS SPIFFE identity + `Authorizer` boundaries (`runtime/authz.py`). (3) node ↔ disk: encrypted, MAC'd frames; keys via `KeyProvider`. (4) node ↔ adjacent layers: versioned contracts, fencing tokens, idempotency keys.

## 5. State machine
Connectivity: `unknown → up/degraded ↔ down/flapping` (hysteresis `up_after`/`down_after`; flapping ⇒ partitioned). Authority tiers during a partition follow `tier_schedule` (default `full` 0 s, `sustain` 1800 s, `freeze` 7200 s) and become `expired` at lease expiry. Caps: storage freeze, RTC-only time, and operator overrides force at most `freeze`; quarantine/disable refuse everything.

### 5.1 Lease lifecycle
issue (control plane) → `install_lease` (reachable, reconciled, policy installed, verify, replay check, epoch ≥ watermark) → active → expired | revoked (`apply_revocations`) | superseded (new lease; old one can never be reinstalled).

### 5.2 Partition lifecycle
`down/flapping` observed → `partition` (epoch++ persisted) → offline decisions → reachable again → `reconnect`.

### 5.3 Reconciliation lifecycle
`reconcile_begin` (deterministic txn id, audit head) → batches → per-batch ack persisted → conflicts compensated or quarantined → `reconcile_complete` (PK_RECONCILIATION_RECORD/2) → compaction with archive. Crash at any point resumes with the same txn id.

### 5.4 Failure model
Crash-stop processes, torn writes at the tail, arbitrary message loss/duplication/reorder, Byzantine network peers without signing keys, local root attacker (see `docs/THREAT_MODEL.md` for residual risks R1–R5). Not tolerated: compromise of issuer signing keys (mitigated by revocation/epoch), whole-disk rollback while partitioned (R1).

## 6. Adjacent contracts (normative)
| Layer | Contract | Direction | Required fields | Schema |
|---|---|---|---|---|
| GAP-12 | `PK_REACHABILITY/1` via signed `PK_HEARTBEAT/1` | upstream | site, nonce, time, signature | `schemas/PK_HEARTBEAT-1.schema.json` |
| GAP-13 | `PK_POLICY_ENGINE/1`, bundles `PK_POLICY_BUNDLE/1` | upstream | policy_version, author≠approver, rules, signature | `schemas/PK_POLICY_BUNDLE-1.schema.json` |
| PLN-07 | `PK_CAPABILITY/1`, grants `PK_CAPABILITY_GRANT/1` | upstream | principal, capabilities, epoch, validity, signature | `schemas/PK_CAPABILITY_GRANT-1.schema.json` |
| GAP-01 | `PK_SUPERVISOR_COMMAND/1` | downstream | command_id (= decision id), authority_epoch, generation, traceparent | `schemas/PK_SUPERVISOR_COMMAND-1.schema.json` |
| GAP-05 | `PK_REPLICATION_BATCH/1` | peer | txn_id, batch_no, decisions, audit_head, generation | `schemas/PK_REPLICATION_BATCH-1.schema.json` |
| pk_core | conformance `Contract` (`contract.py`) | framework | unchanged from 4.2.0 | — |
Unsupported contract identifiers MUST be refused with `GAP04-E0901`. Supported versions: `COMPATIBILITY_MATRIX.json`.

## 7. Security requirements
Crypto profile `PK_CRYPTO/1`; canonical encoding `PK_CANON/1`; identity = SPIFFE over TLS 1.3 mTLS; trusted-time priority and holdover per `docs/THREAT_MODEL.md` §6; key management via `KeyProvider` (TPM/KMS required for production, W-005). Error details MUST NOT contain secrets; logs redact signatures, nonces, tokens and keys and hash subjects.

## 8. Persistence requirements
Single WAL (ADR-003); every transaction one fsync'ed frame; recovery = last snapshot + delta replay for the open epoch; torn tail truncated; mid-file corruption fails closed; journal budget with reserved control capacity and deterministic emergency freeze; compaction only after acknowledged reconciliation, archived; encrypted backup/restore that bumps generation; state schema migrations via `MIGRATIONS` with downgrade refusal.

## 9. Verification strategy
| Area | Suite |
|---|---|
| Lease/policy/epoch/error model | `tests/test_p0_lease_policy.py` |
| Time, WAL, audit, encryption, fencing, transactions | `tests/test_p0_durability.py` |
| Idempotency, reconciliation, adapters, authz | `tests/test_p0_reconcile_adapters.py` |
| Crash/restart (process kill at 10 crash points + random SIGKILL) | `tests/test_crash_recovery.py` |
| Config, overrides, health, metrics, logs, traces, alerts, backpressure, backup, quarantine, rollout | `tests/test_p1_operations.py` |
| Fault injection, concurrency, property/fuzz, adversarial, latency regression | `tests/test_p1_resilience_suites.py` |
| Schema contracts, golden fixtures, integration, compatibility, release | `tests/test_p1_contracts_integration.py` |
| Governance artifacts, gate fail-closed, traceability stability, docs | `tests/test_p2_governance.py` |
| Performance/soak/storm/fleet | `tests/perf/bench.py` → `evidence/perf_baseline.json` |
| GO gate | `runtime/gate.py` → `evidence/gate_decision.json` |

## 10. Operations
Health/readiness/metrics endpoint `runtime/opsapi.py`; alerts `ops/alerts.rules.yml`; dashboard `ops/dashboard.grafana.json`; runbook `docs/RUNBOOK.md`; severity/containment `docs/INCIDENT_SEVERITY.md`; SLOs `docs/SLO.md`; capacity `docs/CAPACITY_MODEL.md`; ownership/escalation `docs/GOVERNANCE.md`; reviews `docs/REVIEW_PROCESS.md`; vulnerabilities/EOL `docs/VULNERABILITY_AND_EOL.md`; waivers `docs/WAIVERS.md`.

## 11. Missing-component register
The 56 post-audit components and their 1,456 control IDs (`GAP04-Cnn-nnn`) are tracked in `evidence/CHECKLIST_STATUS.json` and rendered in `GAP04_v4.3.0_Checklist_Status.md`; the original 100 checks are traced in `evidence/RTM.json`. Residual gaps: `MISSING_COMPONENTS.md`.

## 12. Assumptions, dependencies, known limitations and Non-goals
Assumes POSIX filesystems with working `fsync` on files and directories; a control plane that issues signed leases/policies/time tokens/heartbeats with increasing epochs; one controller per site state directory. Known limitations are the waivers W-001…W-013. Non-goals are listed in §2.

## 13. Artifact manifest
Normative artifacts: this file; `schemas/*.json`; `runtime/errors.py` (error registry); `COMPATIBILITY_MATRIX.json`; `docs/ADR/*`; `evidence/CHECKLIST_STATUS.json`; `evidence/waivers.json`; `runtime/gate.py` (gate policy `PK_GAP04_GATE/1`). Integrity: `MANIFEST.sha256`. Documentation updates are part of the definition of done for any control change.
