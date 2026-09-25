# Governance (C009, C098, C099, C100)

* **Ownership (C009):** `ops/ownership.json` + `CODEOWNERS` define roles, aliases, authorities and escalation;
  `tools/governance_check.py` fails the production gate while any required role is unassigned or on-call
  routing is missing. **All roles are unassigned** — only the repository owner can name people.
* **Reviews (C098):** `ops/REVIEWS.json` cadence (access 90 d, policy 180 d, dependencies 30 d, config drift
  30 d, architecture 365 d + triggers, threat model 180 d). No review has been performed yet.
* **Exceptions/debt (C099):** `ops/REGISTER.json` — waivers need a risk statement, approver (not the
  implementer), remediation owner and expiry; debt and deprecations tracked with owners. Every waiver is
  PENDING because no approver exists.
* **Exit gate (C100):** `tools/gate.py` consumes the evidence bundle and produces `evidence/EXIT_GATE.json`
  with a deterministic verdict and its SHA-256; it is `NO_GO` while any production blocker is open. Reviewer
  independence: the implementer (this build) cannot sign off its own evidence.
