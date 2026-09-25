# ADR-005 — Identity, authorization, keys and encryption

* Status: **Proposed** · Traceability: C023, C024, C041–C048, MC-021..025

* Identity: SPIFFE-style URI SAN in X.509 client certs, `spiffe://<td>/tenant/<t>/env/<e>/site/<s>/wl/<w>/<name>`; name prefixes `admin-`/`peer-` define purpose. mTLS (TLS ≥ 1.2, AEAD suites, TLS 1.3 preferred) is required on every non-loopback listener; config validation refuses otherwise.
* Bearer tokens (HMAC-SHA256, kid-rotated, audience+expiry) only for loopback/break-glass and disabled by default.
* Authorization: deny-by-default versioned policy; rules match roles × actions × namespace glob × key prefix; checked after authentication and before any read or mutation; decisions audited when denied; atomic rollout with one-step rollback.
* Keys: root material comes only from `secret://` references (KMS/CSI-mounted files with 0600 or env); purpose-separated derivation (`wal`, `audit`, `backup`); data keys held in memory for the process lifetime; KMS outage after start does not stop serving, KMS outage at start refuses to start (fail safe). Data at rest (WAL, snapshots, backups) sealed with AES-256-GCM with AAD binding file kind + generation; keyring rotation keeps old kids readable.
* Secrets never enter logs, traces, metrics labels, error details or explain records (central `redact()` + allow-listed error details + allow-listed span attributes).

## Secret / key inventory (MC-024-01)

| Secret | Purpose | Owner | Rotation | Exposure impact |
|---|---|---|---|---|
| `data-key` (root → `wal` derived data key) | seal WAL + snapshots | security owner | yearly or on suspicion; keyring keeps old kids | confidentiality of all state at rest |
| `backup` keyring | seal backups (independent of data key) | security owner | yearly | confidentiality of backups |
| backup signing key | HMAC backup manifests | security owner | yearly | forged backups accepted |
| `audit-key` (→ `audit`) | HMAC audit chain | security owner | yearly, new chain segment | undetectable audit tampering |
| `token-key` (→ `token`) | bearer tokens (loopback/break-glass) | security owner | 90 days | impersonation within token scope |
| TLS server key | listener identity | operations owner | ≤ 90 days (hot reload) | MITM of clients |
| client cert keys | workload identity | workload owners | ≤ 30 days | tenant impersonation |
| `INV05_SIGNING_KEY` | sign CI evidence | security owner | yearly | forged release evidence |
