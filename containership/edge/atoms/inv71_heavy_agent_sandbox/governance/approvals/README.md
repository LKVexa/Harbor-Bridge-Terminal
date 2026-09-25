# Approvals

This directory holds signed approval records (ADR acceptance, release acceptance, waiver approvals). It is intentionally empty: no accountable owner exists yet, and the remediation pass does not mint approvals. `tools/production_gate.py` requires, for the exact release digest, approval records from the service owner, security, SRE/operations and release authority.

Record format: `{"schema":"PK_HEAVYBOX_APPROVAL/1","subject":"release|adr|waiver","subject_digest":"sha256","role":"...","principal":"...","decision":"approve|reject","date":"YYYY-MM-DD","signature":"..."}`
