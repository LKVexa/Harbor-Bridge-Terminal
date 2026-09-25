# INV-68 vulnerability response, patching and end-of-life (MC-36; C094)

**Intake contact:** UNASSIGNED — security_owner must be named (ops/owners.json). Until
then reports go to the repository owner (David Paul Russell, LinearFinance.org).

## Intake and triage
1. Private report (email/issue marked security) → acknowledge within 2 business days.
2. Triage within 5 business days: reproduce, CVSS v3.1/v4 score, affected versions
   (`compatibility.json` support window), exploitability in INV-68 deployments.
3. Dependency advisories: the runtime has no third-party dependencies; dev tooling
   (`requirements-dev.lock`) is re-checked every 30 days (ops/REVIEWS.json) and on
   any advisory touching jsonschema/referencing/rpds-py/attrs/setuptools.

## Remediation SLA (from triage)
| Severity | Fix available | Released to supported versions |
|---|---|---|
| Critical (CVSS ≥ 9) | 72 h | 7 days |
| High (7–8.9) | 7 days | 14 days |
| Medium (4–6.9) | 30 days | next minor |
| Low | best effort | next minor |

## Patch engineering and emergency release
Fix on the oldest supported branch, forward-port; every patch runs the full evidence
suite (`tools/run_evidence.py`); emergency releases may shorten canary bake times
(ROLLOUT_POLICY) but never skip the exit gate, signing, or the audit of the rollout.
Checks deferred under an emergency release must complete within 5 business days (post-release full qualification), tracked as a register entry. Interim mitigation: `freeze` (RUNBOOK §6) or configuration tightening (limits/quotas).

## End-of-life
A minor is supported 12 months after its successor ships; EOL is announced ≥ 90 days
ahead in CHANGELOG and `compatibility.json` (`status: deprecated` → `eol`). After EOL
only Critical fixes, at owner discretion.

## Disclosure
Coordinated: advisory after fixed versions are available or 90 days, whichever first.
