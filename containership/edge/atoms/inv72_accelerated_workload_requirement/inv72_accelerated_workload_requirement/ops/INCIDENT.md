# INV-72 incident procedure (C097)

Severity, paging and escalation timings: `ops/ESCALATION.json`. Roles: `ops/OWNERS.json`.

1. **Detect** — an alert from `ops/alerts.json` or a report. Open an incident record (template below).
2. **Classify** — SEV1 if isolation or strict-fit may have been violated, or the audit/journal chain
   fails verification. Security-class incidents page `inv72-security-owner` in addition.
3. **Contain** (choose the narrowest that stops harm):
   * one device: `quarantine(dev, reason, revoke=True)`
   * one tenant: remove its grants in the KeyProvider (tokens then fail `ACCEL_FORBIDDEN`)
   * whole component: `disable(reason)`
   * bad configuration: `ConfigStore.rollback(...)`
4. **Preserve evidence** — `audit.export()` and record `head()`; copy the journal; `store.snapshot()`;
   `explain(decision_id)` for every implicated decision.
5. **Recover** — fix, `enable()`, `unquarantine()`; confirm `status()["ready"]` and alert silence.
6. **Review** — within 5 business days; findings go to `ops/REVIEWS.json` `findings_register`.

## Record template

```
id: INC-YYYYMMDD-N      sev:        commander:        security-owner paged: y/n
detected (UTC):         contained (UTC):        recovered (UTC):
alert / report:
affected tenants (pseudonyms), devices, decision ids:
containment actions (with audit seq numbers):
evidence: audit head (seq, hash), journal digest, snapshot digest
root cause:
follow-ups (owner, due):
```

No incident exercise has been held (W-007).
