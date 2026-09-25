# Ownership and on-call (INV29-MC102)

| Role | Holder | Contact alias | Status |
|---|---|---|---|
| Accountable service owner | David Paul Russell (LinearFinance.org) | `@inv29-owners` | provisional — confirm |
| Security owner | _to be named_ | `@inv29-security` | **OWNER_ACTION** |
| Runtime / integration owner (INV-27, INV-44, PLN-04 liaison) | _to be named_ | `@inv29-runtime` | **OWNER_ACTION** |
| Primary on-call rotation | _to be defined_ | `inv29-oncall` (pager alias) | **OWNER_ACTION** |
| Escalation | owner → security owner → platform director | — | provisional |

Use organisational aliases, never personal phone numbers or secrets, in this file.

## Approval requirements
| Change type | Approvals required |
|---|---|
| `schemas/` (public records) | service owner + one consumer (PLN-04) owner |
| `admission.py`, `model.py`, `DEFAULT_DENYLIST`, policy defaults | service owner + security owner |
| Signing / provenance / keyring handling | security owner (mandatory) |
| Release (tag + evidence bundle) | service owner, after `RELEASE_CHECKLIST.md` is complete |
| Emergency disable | any on-call engineer; post-hoc review within 2 business days |
| Waivers (`governance/WAIVERS.json`) | service owner + security owner; P0 cannot be waived |

## Review
Validate this file at every release (`tools/build_release.py` refuses to mark MC102 closed while any role is unnamed) and on any team/org change.
