# Recurring reviews (C098)

| Review | Cadence | Inputs | Evidence to file | Last performed |
|---|---|---|---|---|
| Access (key holders, operator roles, capabilities granted via TenantBus) | quarterly | owners.json, audit chain `capability.grant` events | signed review note | never |
| Policy (topic publishers, states, residency) | quarterly + on change | config generations + provenance | diff + approval | never |
| Dependencies (SBOM, CVEs, Dapr version vs support window) | monthly | `tools/sbom.py`, COMPATIBILITY.md | advisory scan result | never |
| Configuration drift | monthly | active digest vs config repo | digest comparison | never |
| Architecture (ADR-0001, THREAT_MODEL) | semi-annual + per MAJOR | ADR, threats.json | approval record | never |
| Waivers, debt, deprecations | monthly | governance/waivers.json | renewals/closures | never |
| Runbook drill (bootstrap, rollback, emergency disable) | quarterly | OPERATIONS.md | drill log by a non-author | never |

"never" is accurate: this repository has no operating history yet.
