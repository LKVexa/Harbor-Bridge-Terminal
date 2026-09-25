# Runbooks — INV-03 (checklist item 59)

**Status: PROPOSED.** Package-side commands below were run in the build environment; cluster-side
commands (`kubectl …`) were not, because no cluster was available.

## Day 0 — install
1. `python -m compileall -q inv03_container_hardening && python -B inv03_container_hardening/tools/release_gate.py`
   (expect `NO_GO` today; read `RELEASE_GATE.json` → `reasons`).
2. Generate keys (32+ random bytes each): baseline signing key, audit seal key, auth token key. Store in the KMS (item 35, BLOCKED — until then, a mounted secret).
3. Sign the baseline: `sign_baseline(default_document(), Keyring({...}), "<signer>")`, then `BaselineStore(path, kr).activate(art, 0)`.
4. Deploy the webhook server (`hardening/admission.py::make_server`, TLS cert for `inv03-webhook.inv03-system.svc`).
5. `kubectl apply` the `WEBHOOK_CONFIGURATION` (failurePolicy **Fail**) with the CA bundle filled in.
6. Health: `curl -k https://<svc>/readyz` → 200; `/metrics` shows `inv03_decisions_total`.
7. Verify: apply `fixtures/invalid/01_privileged.json`'s pod — must be denied with `not-privileged`.

## Day 1 — change the baseline
1. Edit the document, bump `version`, sign, then `activate(artifact, expected_epoch=store.epoch)`. `EPOCH_CONFLICT` means someone else won — re-read and retry.
2. Roll out with `Rollout` stages 1→5→25→50→100 %; the gate rolls back on a denial-rate increase > 2 points or any error.
3. Failure branch: `store.rollback(store.epoch)`; confirm `/metrics` denial rate returns to the pre-change level.

## Day 2 — steady state
- Daily: `tools/recurring_review.py` → expired/pending waivers (`sweep`), audit chain verification.
- Exception request → approve (different human) → auto-expiry; renewals capped at 2, then escalate.
- Runtime upgrades: raise the `runsc` floor in the baseline only after every node reports the new version (`RuntimeInventory.inventory()`).

## Failure signatures
| Reason code | Meaning | First action |
|---|---|---|
| `BASELINE_UNAVAILABLE` | no/invalid baseline | restore `baseline.json` or re-activate |
| `CLOCK_UNTRUSTED` | time source failed or went backwards | fix NTP; decisions stay denied until then |
| `SANDBOX_RUNTIME_UNAVAILABLE` | node missing/unhealthy/downgraded `runsc` | drain node, reinstall runtime |
| `DEPENDENCY_FAILURE` | audit ledger unwritable | free disk / fix volume; admits are refused meanwhile |
| `EMERGENCY_DENY_ALL` | kill switch on | see INCIDENT_PLAYBOOK.md |
| `INTERNAL_DEFECT` | evaluator bug | page; file defect with `decision_id` |
