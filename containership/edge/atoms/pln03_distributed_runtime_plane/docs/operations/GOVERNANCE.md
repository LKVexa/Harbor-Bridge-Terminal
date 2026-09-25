# Operational governance (MC-051)

- **Incident severity & paging:** docs/ESCALATION.md.
- **Recurring reviews:** ownership every 90 days (OWNERS.yaml), threat model each minor release, SLO/error-budget monthly, dependency/vulnerability scan every CI run, compatibility matrix each release.
- **Exceptions / waivers / debt register:** `docs/operations/EXCEPTIONS.yaml` — every entry has id, requirement, reason, approver, expiry. Expired waivers fail the audit.
- **Post-incident:** blameless review within 5 business days; actions tracked to closure in the debt register.
