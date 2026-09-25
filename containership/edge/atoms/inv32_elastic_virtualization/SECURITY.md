# Security policy (INV-32)

* Report vulnerabilities privately to the security owner named in `inv32_elastic_virtualization/governance.json`
  (currently **unassigned** — until named, route to the repository owner and do not open a public issue).
* Include: affected version, reproduction, impact on host reserve / tenant isolation / audit integrity.
* Patch SLAs: critical 72 h, high 14 d, medium ≤ 90 d (see docs/GOVERNANCE_AND_COMPATIBILITY.md).
* Any new action/capability added to `authz.ACTIONS` requires a security review entry in docs/THREAT_MODEL.md.
