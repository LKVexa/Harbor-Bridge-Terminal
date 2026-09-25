# Incident response (INV-38-C097)

Severity model and containment in `ops/severity.yaml`. SEV-1 covers memory/
isolation violation, sealing failure and cross-tenant access (immediate page +
incident commander). Containment actions: disable bypass, drain queues, revoke
VF, quarantine node, roll back config/release, stop service. Evidence preservation
covers logs/traces/audit/decision records, config/release digests and volatile
provider counters. Recovery requires identity/policy refresh and provider health
verification before re-enabling bypass. Runbooks: `ops/runbooks/`. Post-incident
review links back to requirements/tests/waivers. **Status:** `DONE`.
