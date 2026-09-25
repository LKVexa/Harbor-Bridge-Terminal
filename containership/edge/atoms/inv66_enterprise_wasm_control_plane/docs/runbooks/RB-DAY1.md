# RB-DAY1 — Deploy, smoke, staged rollout (MC-064-T02, MC-061)

1. **Gate.** Deploy only if `python tools/release.py gate` prints `GO`. Today it prints **NO_GO**; the reasons are in `release/exit_gate.json`. Break-glass deploys need the audited procedure in `deploy/rollout.json`.
2. **Canary.** Follow the stages in `deploy/rollout.json` (1 replica → 10 % → 50 % → 100 %). At each stage, hold for the soak time and check these halt signals:
   - `rate(ecp_admissions_total{outcome="refused"})` more than 3× baseline
   - p99 `ecp_admission_latency_ms` > 50
   - any `ecp_audit_append_failures_total` or `ecp_audit_verify_failures_total` increase
   - `/readyz` not ready
3. **Smoke** (expected outputs):
   - `curl -s https://HOST/healthz` → `{"status":"alive","version":"4.3.0"}`
   - `curl -s https://HOST/version` → the protocol list and the active `config_generation` (must equal the recorded one)
   - Admit a known-good signed manifest with a test deployer token → `admitted:true, state:delivered`
   - Admit from `ghcr.evil.example` → `admitted:false`, `ECP_REGISTRY_NOT_APPROVED`
4. **Initial RBAC / registries / signers.** Stage a generation, get 2 approvers, then activate with CAS (see RB-DAY2 §Policy change).
5. **Readiness sign-off.** Record in `release/reviews.jsonl`: approver, generation, artifact digest.
6. **Rollback.** Redeploy the previous artifact digest (immutable). For config, use `rollback_config(<previous generation>)`. Both are journaled.
