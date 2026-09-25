# Recurring review program (item 61)
| Review | Cadence | Owner | Output |
|---|---|---|---|
| Threat model | quarterly + on trust-boundary change | security reviewer | updated THREAT_MODEL.md |
| Exceptions/waivers expiry | monthly | primary owner | exceptions.json updated; expired waivers fail the gate |
| Compatibility matrix | each Kubernetes minor release | platform reviewer | SUPPORTED_VERSIONS.md |
| SLO/capacity | quarterly | SRE | baseline refresh |
| RBAC least-privilege | quarterly | security reviewer | rbac diff sign-off |
| Game day (failover, freeze, restore) | twice yearly | SRE | exercise record in evidence/ |
