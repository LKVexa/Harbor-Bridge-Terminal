# Incident response model (item 60)
* **Severity:** SEV1 cross-tenant action, suspected compromise, or duplicate launch/cancel; SEV2 controller down > 15 min or all placements Degraded; SEV3 single-tenant impact.
* **First moves:** SEV1 → freeze (runbook), preserve `audit.jsonl` + head, page security reviewer. SEV2 → degraded-mode runbook.
* **Roles:** incident commander (on-call SRE), comms, security (SEV1), downstream liaison.
* **Evidence:** audit chain verify, `/configz` digest, controller logs (JSON, trace ids), Kubernetes events.
* **Close-out:** blameless review within 5 working days; actions tracked in the exceptions/technical-debt ledger.
