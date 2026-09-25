# Incident response (INV55-IR-001, DRAFT — roles UNASSIGNED)

| Severity | Definition | Page | Ack | Escalate after |
|---|---|---|---|---|
| SEV1 | confirmed secret exposure, cross-tenant access, audit tampering | security on-call + service owner | 5 min | 15 min → security owner |
| SEV2 | suspected exposure; provider compromise/outage > 15 min | service on-call | 15 min | 30 min |
| SEV3 | degraded (DEGRADED responses, breaker flapping) | ticket | 4 h | 1 business day |

Roles: incident commander, security lead, scribe, comms. Channel: dedicated incident room, no secret values ever pasted.

## Playbooks (containment → eradication → recovery)
* **Suspected secret exposure:** `freeze("secret:<name>")` → rotate (new version) → `retire(name, old, destroy=True)` via break-glass (two people) → revoke provider leases → unfreeze → verify with `explain(request_id)` that no grant followed.
* **Stolen workload identity:** remove the workload from every scope (SCOPE), rotate IdP key id if the key is suspected, freeze `tenant:<t>` if scope is unknown.
* **Vault token compromise:** revoke the AppRole secret-id and token in Vault; restart INV-55 (fresh login); review audit for grants during the window.
* **Authorization bypass / cross-tenant:** freeze `global`; preserve audit file + external head; add regression test before unfreezing.
* **Audit tampering:** `verify_file(path, seal_key, expected_head)` against the externally stored head; treat any failure as SEV1; preserve both copies.
* **Provider compromise/outage:** quarantine via `freeze("op:rotate")`; if compromised, rotate everything served after restoring a clean provider.
* **Leaked build/config credential:** `tools/secret_scan.py` finding → revoke at the issuer, purge history, rotate dependents.

Forensics without further exposure: collect audit chain (no values), metrics, traces, config provenance; never collect process memory dumps unless the security lead approves (they contain plaintext).

Exit: recovery validated (health ready, no DENIED anomalies), post-incident review within 5 business days, corrective actions tracked in `WAIVERS.json`/backlog, threat model and tests updated.
