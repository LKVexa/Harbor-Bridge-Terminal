# Vulnerability / EOL policy (component 55)

- **Runtime dependencies:** none beyond the CPython standard library. The supported
  interpreter floor is CPython 3.10; a CPython minor line past its upstream EOL date is
  unsupported for production and the regression gate host must be re-baselined on a
  supported line.
- **Advisory intake:** CPython security releases (python.org security announcements) and
  the three test-lane tools (`jsonschema`, Node.js, OpenSSL). No advisory feed is wired
  into this archive — the intake is a **human process** until an owner names a feed
  (BLOCKED, owner UNASSIGNED).
- **Severity SLA (PROPOSED):** critical 7 days, high 30 days, medium 90 days, low next release.
- **Crypto:** Ed25519 only (`keys.ALLOWED_ALGORITHMS`); the HMAC fixture verifier is
  `DEPRECATED_ALGORITHMS` and must never be configured in production. Adding an algorithm
  is an ADR-level change.
- **Pure-Python Ed25519:** not constant-time. Acceptable for verification of public data;
  unacceptable for signing secrets in production (waiver W-002, expiry set by owner).
