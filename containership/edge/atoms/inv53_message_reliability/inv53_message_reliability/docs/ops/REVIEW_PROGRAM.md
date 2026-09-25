# Recurring review program (C098)

| Review | Cadence | Owner | Input | Output |
|---|---|---|---|---|
| Access (grants, principals, key ids) | quarterly | security_owner | grants config, `Keyring.kids()` | removed grants, retired keys |
| Owners and contacts | quarterly | service_owner | `governance/owners.json` | confirmed or nulled roles |
| Dependencies | monthly | technical_owner | pk_core pin, Python EOL dates | updated pins, SBOM |
| Configuration drift | monthly | operations_owner | effective config digests per site | reconciled layers |
| Threat model | per minor release, ≥ yearly | security_owner | THREAT_MODEL.md | updated threats/tests |
| Architecture (ADRs) | per major release | technical_owner | docs/adr | accepted/superseded ADRs |
| Waivers and debt | monthly | service_owner | governance/WAIVERS.json | closed or re-approved waivers (≤ 90 days) |
| Performance thresholds | per release | qa_owner | CI bench evidence | approved thresholds |
Each review writes a dated record under `governance/reviews/` (none exist yet — the program has not started).
