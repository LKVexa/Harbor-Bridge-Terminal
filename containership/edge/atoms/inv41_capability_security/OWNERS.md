# INV-41 ownership

Machine-readable: `OWNERS.json` (validated by `tools/governance_check.py`); review policy: `CODEOWNERS`.

* **Accountable owner (proposed, unconfirmed):** David Paul Russell — davidpaulrussell@linearfinance.org
* **Backup owner, technical owner, security / release / policy approvers, incident commander:** UNASSIGNED — the production gate fails until named (BLOCKERS.json B-OWN-01).
* **Emergency path:** SEV1 → incident commander (ack 15 min, decision 60 min) → security approver → accountable owner. Full tiers in `OWNERS.json`.
* Emergency mitigation / revocation / quarantine: incident commander or security approver. Release rollback: release approver or incident commander. Security exceptions: security approver only, with expiry (EXCEPTIONS.json).
* Ownership transfer: PR changing OWNERS.json + CODEOWNERS approved by outgoing and incoming owner and the security approver.
* Review cadence: 90 days; last reviewed 2026-09-22.
