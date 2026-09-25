# Recurring review process (checklist #97)

| Review | Cadence | Reviewer | Output |
|---|---|---|---|
| Access/scope policy | monthly | security owner | `reviews/YYYY-MM-scope.md` |
| Vault policy | quarterly | security + ops | same folder |
| Dependencies/CVE | weekly (automated SBOM diff) | service owner | CI artifact |
| Configuration | on every commit (two-person) | ops | provenance record |
| Threat model / architecture | semi-annual + triggers | security | THREAT_MODEL.md revision |
| SLO/capacity, runbooks, ownership | quarterly | service owner | revisions |
Out-of-cycle triggers: SEV1/SEV2, provider/identity/protocol change. Overdue high-risk actions escalate to the service owner's manager after 14 days. Each record: date, scope, reviewer, findings, due dates, closure evidence. **No review has been held yet** — the first records are due once owners are assigned.
