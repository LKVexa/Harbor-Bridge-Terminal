# Vulnerability response, patching and end-of-life (MC-31; C094)

**Status:** process defined; reporting channel and people **not yet assigned** (owner action).

## Reporting

Report privately to the `inv64-security-contact` role (address to be published by the owner, e.g. `security@linearfinance.org` — *placeholder, not live*). Do not open public issues. Reports are acknowledged under embargo; coordinated disclosure after a fix is available or 90 days, whichever first, unless actively exploited.

## Severity and SLAs

Severity = CVSS v3.1/v4 base score adjusted by INV-64 context (tenant-crossing, auth bypass, supply chain ⇒ at least High). Override only by `inv64-security-contact` with written rationale in the incident record.

| Severity | Acknowledge | Triage | Mitigation available | Fix released | Operator notice |
|---|---|---|---|---|---|
| Critical | 24 h | 48 h | 72 h | 7 days | on mitigation |
| High | 2 days | 5 days | 14 days | 30 days | on fix |
| Medium | 5 days | 10 days | — | 90 days | release notes |
| Low | 10 days | 30 days | — | next minor | release notes |

Scope includes INV-64 code, `pk_core`, CPython, `cryptography`, build tooling, OAM/IDL tooling, adjacent INV components (hand-off to their owners) and transitive dependencies.

## Intake and monitoring

CI job `advisories` runs `pip-audit` against the certification constraints (needs package-index access; not executable in the 4.3.0 build session). Findings above policy (≥ High with a fix available) fail the release gate via `ops/REGISTER.json` or a failing evidence file. Exceptions: register entry type `exception`, security approval, compensating controls, expiry ≤ 30 days (Critical) / 90 days (High).

## Patches and revocation

Emergency patch = patch release from the supported branch, full gate (no skipped controls), signed by the managed signer (MC-39). A vulnerable release is **revoked** by adding its artifact digests to the trust policy's `denied_digests` (`trust.py`), which blocks its consumption everywhere the policy is deployed.

## End of life

EOL is announced ≥ 90 days ahead in CHANGELOG and `compatibility.json` (`support_lines`). After EOL no fixes are made; Critical issues in EOL lines are disclosed with upgrade guidance only.

## Drills

An emergency-patch tabletop is required before production certification (not yet held — MC-31 blocker). Record date, participants, timeline and findings in `ops/REVIEWS.json` history.
