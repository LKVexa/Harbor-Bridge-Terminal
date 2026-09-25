# Operator runbooks (INV30-GAP-066 · INV-30-C096, C040)

## Day 0 — bootstrap an empty node
1. Verify artifact: `python -m …release --verify --out evidence/` → `verified: true`.
2. Discover: `ops env` → record `cheri.state`. If `present`, install the native helper (CHERI_BACKEND.md).
3. Provision secrets: minting key and principal keys (≥32 bytes, file mode 0600 or env) and reference them in the
   overlay patch (`secret_refs.minting_key: "file:/etc/inv30/minting.key"`).
4. `ops config-check --context <ctx> --mode production` → `ok: true`.
5. `ops health --context <ctx>` → `ready: true`; archive output as baseline.
*Failure:* CONFIG_INVALID → fix the named field; DEPENDENCY_INCOMPATIBLE → install pk_core 4.0.x or run model-only.

## Day 1 — deploy
1. Generate release evidence; gate verdict must be GO/GO_MODEL_ONLY (hardware tier only if `hardware_tier_verdict=GO`).
2. `ops promote` through canary stages (ROLLOUT.md) with health JSON from dashboards.
*Failure:* any red gate → `ops rollback`; invariant alert → `ops disable` + INCIDENT_RESPONSE.md SEV1.

## Day 2 — operate
* Daily: check dashboards; `AuditLedger.verify(expected_head=<anchored>)`; export anchored head.
* Tenant misbehaving: `service.quarantine_tenant(...)`; release after review.
* Rotate keys: provision new secret, activate config, restart (all handles invalidated by design; clients re-mint).
* Dependency failure (GAP-02 unprobed): hardware workloads are refused — expected; fix discovery, do not override.
* Quarterly: REVIEW_PROCESS.md.
