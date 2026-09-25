# Ownership and escalation — PLN-06 (WP #1, C009/C097)

Authoritative, machine-readable record: [`../OWNERSHIP.json`](../OWNERSHIP.json). CODEOWNERS: [`../.github/CODEOWNERS`](../.github/CODEOWNERS).

| Role | Holder | Status |
|---|---|---|
| Service owner | David Paul Russell | proposed — confirm |
| Repository owner | David Paul Russell | proposed — confirm |
| Technical lead | — | **vacant** |
| Security contact | — | **vacant** |
| SRE / on-call target | — | **vacant** |
| Backup owner | — | **vacant** |

**Escalation chain:** SRE on-call → technical lead → service owner → security contact.
**RACI:** see `OWNERSHIP.json.raci` (policy change, transport change, production release, emergency disable, incident command, evidence sign-off).
**Two-maintainer rule:** changes to `security.py`, `integrity.py`, `transports.py`, `service.py`, `data_plane.py`, `config*`, `.github/`, `tools/`, `WAIVERS.json` require two Code Owner approvals (branch protection).
**Fail-closed:** `tools/release_gate.py` blocks release while any role is vacant/proposed, while CODEOWNERS contains `@OWNER-TBD-*`, or when the ownership review is older than 90 days.
**Service catalog:** not yet registered (W-001) — register with tier, support hours, dependency owners, channels and pager service ID, then record the ID in `OWNERSHIP.json.service_catalog`.
