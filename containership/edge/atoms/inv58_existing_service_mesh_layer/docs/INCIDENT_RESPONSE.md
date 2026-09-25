# Incident response (v4.3.0)

Paging and escalation targets are roles in `governance/OWNERSHIP.json`; they have no people yet, so this procedure cannot be executed as written (INV-58-C097 BLOCKED).

| Severity | Trigger (alert) | Page | Response |
|---|---|---|---|
| SEV1 | bounded-attempt violation; audit chain verification failure; `E_INTERNAL` on data plane; cross-tenant access observed | L1 immediately, L2 at 15 min, L3 at 30 min | 15 min |
| SEV2 | bypass flows rising; identity unmapped spike; fail-closed dependency down > 5 min | L1 | 30 min |
| SEV3 | shed rate rising; degraded mode > 30 min; perf gate regression | ticket | next business day |

## Playbooks
- **Retry storm:** check `inv58_effective_attempts`; quarantine hot routes; if systemic, break-glass freeze; confirm with `explain`.
- **Identity mapping failures:** check `inv58_identity_unmapped_total{reason}`; `tenant_mismatch` → possible impersonation → SEV1 security; `unmappable` → PLN-07 issuing non-conforming SANs (DEP-01).
- **Mesh bypass:** `bypass_evidence(tenant)`; contact tenant owner; quarantine tenant if persistent.
- **Policy conflict / bad config:** `rollback_config`; attach rejected-config audit record.

## Containment → recovery → evidence
Contain (quarantine / freeze), recover (rollback / restore), then capture: audit export with head, status snapshot, sealed state snapshot, metrics export, timeline. Post-incident review within 5 business days; each fixed defect adds a regression test in `tests/test_security_regression.py`.
