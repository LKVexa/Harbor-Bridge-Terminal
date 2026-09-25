# Review process

| ID | INV55-GOV-REVIEW | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

| Review | Cadence | Trigger for ad-hoc review | Participants | Output |
|---|---|---|---|---|
| Threat model | quarterly | new provider/auth method, protocol change | security owner, service owner | updated threat-model.md |
| Access (roles/rules/scopes) | quarterly | staff change | service owner | signed-off rule list + policy digest |
| Waivers | monthly | expiry | all owners | waiver-register.md |
| SLO | monthly | budget burn | ops owner | SLO report |
| Dependency/EOL | monthly | advisory | release manager | patching log |
| Docs | each release | behaviour change | author + reviewer | change-history row |

Every code change MUST be reviewed by a CODEOWNERS entry; changes to `identity.py`, `audit.py`, `secretvalue.py`, `providers/`, `errors.py` MUST additionally be reviewed by the security owner. CI (`.github/workflows/ci.yml`) is a required check. Protected-branch enforcement: NOT CONFIGURED (no owners assigned).

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-22 | CI reference |
