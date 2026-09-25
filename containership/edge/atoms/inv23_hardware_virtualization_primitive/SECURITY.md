# Security policy — INV-23

## Supported versions
| Version | Security fixes |
|---|---|
| 5.0.x | yes |
| 4.2.x | critical fixes only until 2027-03-31 |
| ≤ 4.1 | no |

## Reporting a vulnerability
Report privately to the component owner, **davidpaulrussell@linearfinance.org**, subject
`[INV-23 SECURITY]`. Do not open a public issue. Include: affected version/commit, host
platform and backend (`inv23-probe` output with secrets removed), reproduction steps,
impact (e.g. false `usable`, split-brain, token disclosure), and any proposed fix.

## Process
- Acknowledge within 3 business days; triage within 7.
- Severity: **Critical** — false `usable`/bare-metal verdict or ownership split-brain
  reachable by an unprivileged local user; **High** — fencing/token bypass requiring
  local privileges, native-helper substitution; **Medium** — DoS of the claim slot,
  telemetry leakage of identifiers; **Low** — hardening gaps.
- Coordinated disclosure: fix + advisory within 90 days, sooner for Critical.
- The owner is the response owner; there is no separate security team (single-owner
  project, recorded in CODEOWNERS).

## Hardening notes for operators
- Claim state lives in a per-user 0700 directory (`$XDG_RUNTIME_DIR/inv23` or
  `%LOCALAPPDATA%\inv23\claims`). For machine-wide coordination, provision a directory
  owned by a dedicated group, mode 0770 (POSIX, `allow_group=True`) or an ACL granting
  Modify only to participating principals (Windows). Never use a world-writable path.
- Treat the `Claim.token` as a secret: it is never logged or serialised by INV-23.
