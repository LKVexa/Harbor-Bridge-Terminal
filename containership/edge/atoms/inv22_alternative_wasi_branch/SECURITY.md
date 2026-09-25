# Security policy — INV-22 Alternative WASI branch

## Supported versions

| Version | Supported | Notes |
|---|---|---|
| 4.3.x | Yes (pre-production) | Production exit gate is currently **NO_GO** (see `evidence/gate.json`). |
| 4.2.x and older | No | Upgrade to 4.3.x. |

## Reporting a vulnerability

- **Intake contact: `OWNER-TO-ASSIGN`.** The owner must name a monitored private address or ticket queue (MC-57). Until then, report privately to the repository owner. Do not open a public issue.
- Include: affected version, component (`matrix`, `shim`, `cert`, `store`, `auth`, `config`), reproduction, impact.

## Response targets (proposed; owner to approve)

| Severity | Acknowledge | Fix or mitigation |
|---|---|---|
| Critical (trust bypass, cert forgery, capability escalation) | 1 business day | 7 days |
| High | 3 business days | 30 days |
| Medium / Low | 5 business days | next release |

## Security-relevant design commitments

- Unknown, unclassified, stale or unverifiable input fails closed (`INV22.*` error codes).
- Certificate signing keys never reach verifier processes; key compromise is handled by marking the key `revoked` in the trust store, which invalidates every certificate it signed (tested in `tests/test_trust_state.py::Certificates::test_rotation_and_compromise`).
- The audit log is append-only and hash-chained; `inv22 audit-verify <store>` checks it.

## Key-compromise procedure

See `docs/RUNBOOKS.md` → RB-04.
