# Authentication (M07)

Workload tokens: `base64url(claims).base64url(HMAC-SHA256)`; claims `iss, aud, iat, exp, nonce, kid, sub` + identity five-tuple. Checks: strict canonical base64url (fuzz finding), known non-revoked `kid`, constant-time signature compare, issuer and audience, validity ≤ 3600 s with 30 s skew, nonce replay cache (heap-swept, bounded; full cache sheds with OVERLOADED rather than accepting).

Trust-root configuration: `host.json` → `authn.issuer`, `authn.audience`, `authn.keys{kid: keyfile}`. Rotation: add new kid, re-issue, then add old kid to `revoked_kids`.

Peer/transport authentication is mTLS (`crypto/transport.py`, TLS 1.3, `CERT_REQUIRED`). Operators use the same token type with an ops identity; emergency disable needs two distinct operator principals.

**Production gap:** the HMAC scheme is the adapter seam; a SPIFFE/JWT-SVID or attested-identity issuer from the INV-60 fabric must be plugged in and validated before production (RTM C044 notes).
