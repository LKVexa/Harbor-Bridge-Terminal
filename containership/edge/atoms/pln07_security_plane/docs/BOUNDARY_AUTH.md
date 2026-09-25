# Boundary authentication specification (MC-64, MC-03)

| Operation | Caller must be | Checks |
|---|---|---|
| `issue` | authenticated principal with role `grant-issuer`, same tenant | attestation for target environment; policy; quota |
| `attenuate` | authenticated **holder** (principal.subject == grant.subject, same tenant) | parent verifies now; depth policy |
| `revoke` | authenticated, same tenant, role `revoker` or `grant-issuer` | epoch fencing |
| `verify` | unauthenticated (bearer check by an enforcement point) | full chain verify with context |
| `/admin/*` | loopback only on the reference host | — |

**Authenticator contract.** `authenticate(credentials) -> Principal` or raise `AuthenticationFailed` with a uniform message. It must not leak which field was wrong, must compare secrets in constant time and must carry attestation evidence names in `Principal.attestation`.

**Adapters.** Reference: `StaticTokenAuthenticator` (HMAC tokens, ≥32-byte secret). Production: mTLS/SPIFFE workload identity or GAP-06 hardware attestation. `AttestationPolicy` sets required evidence per environment (e.g. `prod: {tpm}`).

**Transport.** TLS termination is the host's job. The reference host binds to 127.0.0.1 by default and caps request bodies at 64 KiB.
