# Security policy (MC-008)

## Reporting a vulnerability
Report privately to the security owner named in `ops/OWNERS.json` (`inv28-security-owner`). Do not open a public issue.

> **Pending (owner action):** `ops/OWNERS.json` currently holds role aliases, not named people or a monitored address. Until the owner fills them in, there is **no working private reporting channel**, and the release gate stays NO_GO (`governance_check`).

Include the affected version (`VERSION`), the component (`INV-28`), a reproduction, and the impact.

## Response targets
See `ops/SLA.md`. Acknowledgement is due within 2 business days. Critical issues get a fix or mitigation, including emergency disable of the affected toolchain entry, within 7 days.

## Supported versions
Only 4.3.x receives security fixes (`ops/COMPATIBILITY_MATRIX.json`).

## Scope
The INV-28 register, policy, selection, binding ticket and their schemas are in scope. Upstream unikernel toolchains are out of scope; report those to the upstream project. Toolchain advisories feed in through `PK_ADVISORY_FEED/1`.

## Hardening already in place
See `docs/THREAT_MODEL.md` (threats T-01 to T-15 with tests) and `evidence/SAST.json`, `evidence/SECRET_SCAN.json` and `evidence/DEPS.json`.
