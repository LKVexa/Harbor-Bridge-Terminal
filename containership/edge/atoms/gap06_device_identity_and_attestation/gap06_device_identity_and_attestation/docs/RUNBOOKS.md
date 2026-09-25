# GAP-06 Runbooks (MC-54, with MC-45/47 procedures)

Status: **drafts, never executed in staging** (no staging exists). Every command below runs against this archive's reference implementation; production equivalents are marked `[PROD-TBD]`. Runbook owner: UNASSIGNED.

## Day 0 — prerequisites
1. Python 3.11+, `pip install -r requirements.lock` (pins `cryptography==46.0.7`).
2. Trust anchors: obtain vendor EK root certificates through a governed import (checksum + signature + approver) `[PROD-TBD]`; load into `TrustStore(anchors=…)`; record `TrustStore.fingerprint_set()` in the evidence bundle.
3. Keys: create `audit` and `wl` keys in the KeyStore; publish public keys to verifiers of the audit ledger.
4. Policy approvers: pin ≥3 approver public keys, threshold ≥2 (`ops.CONFIG_SCHEMA.policy_threshold`).
5. Baseline: `python -m unittest discover -s gap06_device_identity_and_attestation/tests -p "test_*.py"` then `python -m gap06_device_identity_and_attestation.tools.release` → archive `evidence/`.

## Day 1 — deploy
1. Validate config: `ops.load_config(doc, signature_ok=<verified>)` — refuses unsigned/out-of-bounds values. Expected: dict with `_digest`.
2. Start service; readiness (`ops.Health.report()`) must be `ready` (store, time, trust store critical). `unready` → do not route traffic.
3. Enrol nodes: operator with role `enroll` runs `Enrollment.begin` → node signs challenge with AK → `complete`. Expected: record `status: active`. Failure branches: `E_CERT_CHAIN` (EK not from a pinned root — stop, do not add anchors ad hoc), `E_DUPLICATE_IDENTITY` (possible clone — open a SEV2 incident).
4. Publish first policy with quorum signatures; verify `publisher.active()['digest']` equals the approved digest.

## Day 2
### Policy publication / rollback (MC-45)
- Rollout ring: set `rollout.percent` (e.g. 5 → 25 → 100). Halt condition: `gap06_attest_total{result="reject",code="E_MEASUREMENT_REJECTED"}` rising above the pre-rollout baseline.
- Rollback: re-sign the previous content as a **new higher version**. Never restore an older store snapshot to "roll back" (restore floor refuses it: `E_POLICY_ROLLBACK`).
- Emergency disable: set `rollout.percent` to 0 in a new quorum-signed version — nodes outside rollout receive `E_MEASUREMENT_REJECTED` (fail closed), which is the intended safe state.
### Trust-anchor rotation
Add the new anchor alongside the old (overlap), re-validate enrolled EKs, then remove the old anchor in a later change. `[PROD-TBD]` staged activation tooling.
### Key rotation
`KeyStore.rotate(name, principal=…)`; publish the new public key to ledger verifiers before the old version is destroyed.
### Quarantine review / reintegration (MC-11)
1. `explain(node)` → reason code. 2. Preserve evidence (ledger segment, decision record). 3. Node re-attests; only with a fresh `trusted` verdict can an operator holding `quarantine_release` call `QuarantineEnforcer.release`.
### Time-integrity failure (MC-10)
Symptom `E_TIME_UNTRUSTED` on every request. Service is fail-closed by design. Fix the time source, then an operator calls `TrustedClock.reset_after_review()` followed by a fresh `sync()`. Never disable freshness checks.
### Replay-state storage pressure (MC-18)
Run `ChallengeBook.prune(now)`. Never delete `challenges` rows whose `expires + skew_margin` is in the future. If still full, admission returns `E_OVERLOADED` — that is the safe behaviour.
### Partition recovery (MC-08)
Never reset lease tokens or store generations. The replica that cannot `LeaseManager.acquire` stays fenced.
### Backup / restore (MC-27)
`store.backup(path)` → record returned sha256. Restore only with `DurableStore.restore(path, dir, min_generation=<last known generation>)`.
### Audit verification
`AuditLedger.verify(path, public_keys, anchored_head)` daily; any `E_LEDGER_TAMPER` → SEV1.

## Incident severities (MC-47)
| Sev | Examples | First actions |
|---|---|---|
| SEV1 | trust-anchor/AK/approver key compromise, ledger tamper, mass false-trust | freeze policy publication (no new versions), rotate affected keys, revoke affected enrolments, preserve ledger + store snapshot |
| SEV2 | duplicate-identity alerts, sustained replay attempts, quarantine enforcement not acked | quarantine affected nodes, confirm `enforced()` |
| SEV3 | elevated rate limiting, degraded health | tune within `CONFIG_SCHEMA` bounds via signed config |
Paging targets, IC rota and external disclosure paths: **UNASSIGNED** (requires an owning organisation).
