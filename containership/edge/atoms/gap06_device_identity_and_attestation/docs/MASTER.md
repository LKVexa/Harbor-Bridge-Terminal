# GAP-06 MASTER — RECONSTRUCTED (v5.0.0)

> **Provenance notice (35.01).** The original `MASTER.md` named by README 4.1.0 was never in any supplied archive. This file is a *reconstruction from the implemented code* on 2026-09-22. It is not the lost source text and must not be cited as such. Architecture/security owner review: **not performed** (no owner assigned).

## Purpose and scope
Own node identity and the attestation lifecycle: enroll nodes with proof of possession, verify hardware-rooted evidence against a signed, versioned measurement policy, issue expiring verdicts, quarantine drift, and issue workload identities bound to attested hosts. Does **not** own capability probing, artifact signing, policy authorship, general node lifecycle or grant issuance (unchanged from `contract.py`).

## Architecture
```
node ──mTLS──> transport ──> AttestationService
                               ├─ schemas.validate        (PK_*/1, closed)
                               ├─ authz.Authorizer        (role + env/site/tenant, node-as-self)
                               ├─ ratelimit.Admission     (per-principal + global, bounded)
                               ├─ clock.TrustedClock      (fail closed)
                               ├─ replay.ChallengeBook    (durable single-use nonce, lease/fence)
                               ├─ verifier.Verifier       (tpm quote, event log, IMA, relay, clone)
                               │     └─ algorithms / certchain / tpm
                               ├─ policy.PolicyPublisher  (M-of-N signed, monotonic)
                               ├─ store.DurableStore      (hash-chained WAL, snapshots)
                               ├─ audit.AuditLedger       (hash chain + Ed25519, anchored head)
                               ├─ ops.QuarantineEnforcer  (durable outbox → GAP-01 / SCH-01)
                               └─ ops.Telemetry / Health / explain
enrollment.Enrollment  (EK chain → PoP → bind, rotate, revoke, replace)
workload.WorkloadIssuer (node verdict ∧ image allow-list ∧ tenant → signed token)
```
The v4.2.0 in-memory `attestation.Attestor` is retained unchanged for compatibility and its 17 tests still pass; new deployments should use `mc.service.AttestationService`.

## Trust boundaries and state
See `docs/THREAT_MODEL.md` (TB1–TB6, AS1–AS7). Authoritative state: the `DurableStore` tables `nodes, ek_binding, challenges, verdicts, decisions, policy_active, policy_history, quarantine, idempotency, lease`.

## APIs
`POST /v1/challenge {node}` · `POST /v1/attest PK_ATTESTATION/1` · `POST /v1/level {node}`; enrollment and policy publication are library APIs in this version (their transport routes are not bound). Schemas: `schemas/*.schema.json`; errors: `docs/ERROR_CATALOG.md`.

## Checklist cross-reference (35.03)
The 100-item `CHECKLIST.json` and the 781-item missing-components checklist are both reported item-by-item in `CHECKLIST_STATUS.md` (generated, with evidence links).

## Version history (35.04)
4.0.0 master-applied scaffold → 4.1.0 assert hardening → 4.2.0 audited reference state machine → **5.0.0** missing-components pass (this reconstruction). Compatibility: the `attestation` module API is unchanged; `mc/` is additive.
