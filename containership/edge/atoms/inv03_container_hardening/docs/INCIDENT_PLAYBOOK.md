# Incident playbook — INV-03 (checklist item 60)

**Status: PROPOSED.**

| Severity | Trigger examples | Response time |
|---|---|---|
| SEV1 | suspected container escape; admitted workload found privileged; audit chain verification fails | 15 min |
| SEV2 | runtime downgrade on a node; IDS intrusion finding on one workload; baseline tamper refused | 1 h |
| SEV3 | exception expired while still needed; latency SLO burn | next business day |

## Containment
1. **Stop new admissions if scope is unknown:** `engine.set_emergency(<security-admin>, True, "<INC-id>")` (deny-all; there is no admit-all).
2. **Contain the workload:** execute `engine.quarantine_plan(workload, reason)` steps in order — label, network-isolate, freeze, preserve evidence, then terminate unless the incident commander holds.
3. **Revoke waivers** touching the workload: `ExceptionStore.revoke(...)` (takes effect on the next decision).
4. **Roll back the baseline** if the incident follows a baseline change: `store.rollback(store.epoch)`.

## Recovery
- Verify the audit chain against the last externally recorded head.
- Re-admit workloads only through the webhook after `set_emergency(..., False, "<INC-id> contained")`.
- Post-incident review within 5 business days; add the scenario to `tests/test_h_certification.py::Adversarial`.
