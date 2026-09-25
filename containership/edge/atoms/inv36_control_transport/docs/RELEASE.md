# Release, rollout and rollback (MC-21.006-.011, MC-11)

## Staged rollout (proposed)

| Stage | Population | Soak | Promotion criteria | Automatic halt |
|---|---|---|---|---|
| canary | 1 host + its guests in one non-critical site | 24 h | no SEV1/2; handshake failure rate < 0.1 %; p99 within thresholds; zero integrity failures not explained by attack | any auth/integrity anomaly, CRITICAL shed, availability SLO burn > 2x |
| 5 % | one site | 24 h | as above | as above |
| 25 % | multiple sites | 48 h | as above | as above |
| 100 % | fleet | - | - | - |

## Host/guest version sequencing

5.0 and 5.1 share PK_CTRL_FRAME/2 but 5.1 adds PK_CTRL_STREAM/1 + PK_CTRL_HS/1 framing, so **5.0 and 5.1 endpoints do not interoperate on the wire**. Roll out per host pool: drain the pool's sessions, upgrade host agent and guest agents together (or run both versions on distinct ports 5035/5036 during migration), then re-establish. Within 5.1.x, peers of adjacent patch/minor versions interoperate (golden fixtures enforce this).

## Rollback

Prerequisites: previous signed artifact available; config snapshot compatible (config schema unchanged within 5.x); no protocol major change between the two builds.

Rollback is **unsafe without a coordinated pool drain** across the 5.0 <-> 5.1 boundary (wire-incompatible, see above). Key epochs, revoked serials and policy versions are enforced from the verifier's policy and revocation feed, so an older 5.1.x build keeps honouring them; before rolling back past a security fix, check the CHANGELOG security section - rollback is unsafe if the incident depends on a check the older build lacks.

Config rollback: `ConfigStore.rollback`. Emergency disable: quarantine directive or kill switch (`docs/RUNBOOKS.md#quarantine`).

## Release record

Each release captures: decision, approvers, gate evidence (`gate-evidence.json` + sha256), artifact digests (`SHA256SUMS`), signature, SBOM, provenance, config version used in canary, compatibility matrix revision (`compat/matrix.json`), ADR revision. Artifacts published are exactly those built by the validated CI job; nothing is rebuilt after approval.
