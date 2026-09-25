# Staged rollout, rollback and emergency disable (work item 27 — C038, C092)

## Stages
`dev → test → canary (≤ 5 % of hosts, one site) → limited (≤ 25 %) → broad`.
Each environment has its own `CatalogueStore` (environment-specific subset, C035).

| Stage | Entry | Observation | Exit / auto-halt |
|---|---|---|---|
| dev/test | green CI, RTM check | tests | all suites pass |
| canary | signed gate artifact for this digest | 24 h | halt on any SEV1/2 alert, activation failure, boot-refusal rate +1 % |
| limited | canary exit | 48 h | same thresholds |
| broad | limited exit + owner approval | — | — |

## Rollback
`CatalogueStore.rollback(token, target_digest, expected_digest=…, reason=…)`: requires
`catalogue.rollback`, only to a recorded known-good digest, re-validates the document, emits an
activation record (`kind=rollback`) and `config.rolled_back` audit. Automatic rollback triggers: failed
post-activation health check, boot-refusal regression in canary. Anti-downgrade: rollback cannot
target any digest never activated in this store.

## Emergency disable
`emergency_disable(token, device, reason, incident_id, expires)`: break-glass token only; narrows
(never widens); keeps catalogue history intact; `permits()` returns false immediately; restored via
`restore_device` (requires `catalogue.activate`) — audited both ways. Expired disables are reviewed at
the next recurring review; they are not auto-lifted.

Deployment tooling must consume the signed gate artifact (`tools/gate.py`) and refuse a digest with no
matching GO gate (BLOCKED until item 26 completes).
