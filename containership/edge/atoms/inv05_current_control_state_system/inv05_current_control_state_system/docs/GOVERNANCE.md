# Governance: ownership, reviews, exceptions, licensing

Traceability: C009, C098, C099; MC-052 and every `MC-*-36` / `MC-*-33` item.

## Accountable roles (MC-052-01) — **proposed, confirm (EX-006)**

| Role | Proposed holder | Responsibility |
|---|---|---|
| Accountable engineering owner | David Paul Russell (package owner) | releases, ADR approval, exceptions |
| Security owner | *to be named by the package owner* | threat model approval, key management, vuln SLA |
| Operations owner | *to be named by the package owner* | runbooks, on-call, DR drills |
| Escalation | owner → security owner → operations owner | SEV1 paging per `operations/INCIDENTS.md` |

Every component (MC-001..MC-052) inherits these roles in `traceability/mc_status.json` until reassigned.

## Recurring reviews (C098, MC-052-04)
| Review | Cadence | Inputs |
|---|---|---|
| Architecture / ADRs | each minor release | ADRs, compatibility matrix |
| Security & threat model | quarterly + each minor | THREAT_MODEL, exceptions, SBOM scan |
| Access & policy | quarterly | active policy version, role map, cert issuance |
| Dependencies | monthly | `requirements.lock`, SBOM, advisories |
| Operational readiness | before each production promotion | release gate report, DR drill result |

## Exceptions / waivers / debt (C099, MC-052-03)
`docs/EXCEPTIONS.json` (machine-readable, validated in CI: each entry needs owner, rationale, compensating control, expiry date not in the past).

## Licensing (MC-052-05/06)
The package owner has not selected an outbound licence; `LICENSE` is intentionally absent and tracked as EX-007. Third-party obligations are listed in `THIRD-PARTY-NOTICES.md` and in the SBOM.
