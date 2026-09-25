# Threat model (4.3.0)

| Threat | Control | Test |
|---|---|---|
| Exfiltration via unrestricted egress | capability + allow-list + address class, default deny | test_egress, test_aio.OutgoingTest |
| SSRF to host-internal/metadata | address classification incl. mapped/NAT64/metadata IPs; IP literals off | test_egress.test_rebinding_to_private_classes |
| DNS rebinding / TOCTOU | validate all answers, reject mixed sets, pin connect_ip, no caching of denials, revalidate on TTL/reconnect | test_egress.test_answer_change_between_checks_is_revalidated |
| Redirect to denied origin / loops | per-hop authorisation, depth cap, loop detection | test_egress.test_redirects |
| Proxy tunnelling | ambient proxy env ignored | test_egress.test_proxy_env_ignored |
| Header splitting / smuggling | token names, CR/LF/NUL rejection, hop-by-hop & pseudo-header refusal, trailer denylist, no shadowing | test_protocol, fuzz |
| Whole-body buffering / memory exhaustion | bounded streams, limits, admission, load shedding | test_aio.StreamTest, AdmissionTest |
| Capability forgery / replay / amplification | HMAC, env/tenant/workload binding, expiry+skew, revocation, epoch kill switch, attenuating delegation | test_identity |
| Cross-tenant leakage | per-tenant capability binding, pseudonymous log ids, trusted-only trace continuation | test_identity, ObservabilityTest |
| Log injection / cardinality attacks | bounded + escaped strings, fixed label sets | test_protocol.ErrorModelTest, ObservabilityTest |
| Audit tampering | hash chain + HMAC + anchor, independent verifier | AuditTest |
| Dependency substitution / shadowing (pk_core) | installed-package resolution only, origin check, version range | pk_compat.probe |
| Compromised registry / stale mirror | **open** — needs pinned digest + signature once pk_core source is named | — |
