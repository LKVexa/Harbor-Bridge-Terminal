# Incident response  (component 96)
Severity: Sev1 data loss/corruption/cross-tenant exposure/security bypass; Sev2 unavailability or SLO breach; Sev3 degraded.
1. **Detect:** alerts in `ops/alerts.yaml`; audit `verify()` failure; `INV54-E0503/E0501/E1001` in logs.
2. **Contain:** quarantine affected tenant (`quarantine_tenant`) or whole broker (lifecycle QUARANTINED); rotate compromised keys (key ring keeps the old key only for the grace window, then remove).
3. **Preserve evidence:** export audit chain + head, decision log, config provenance, metrics snapshot.
4. **Recover:** restore from backup into an empty dir; re-verify; release quarantine.
5. **Review:** blameless postmortem within 5 business days; add a failure-catalogue row and a regression test.
Escalation per `OWNERSHIP.md` (on-call UNASSIGNED — gap).
