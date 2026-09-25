# Recurring Reviews

| Review | Cadence | Inputs | Record |
|---|---|---|---|
| Architecture | semi-annual + on major | DESIGN.md, ADRs, gaps.json | `governance/reviews.json` |
| Access (identity keys, issuers, audit key holders) | quarterly | trusted_issuers, key ids | same |
| Policy (INV-13 grants for chained callees) | quarterly | provider export | same |
| Dependency (Python, build backend, pk_core) | quarterly | SBOM, constraints.txt | same |
| Configuration (prod overrides) | quarterly | ConfigStore history | same |
| Waivers/debt | monthly | `governance/waivers.json` | expired waivers fail the release gate |
