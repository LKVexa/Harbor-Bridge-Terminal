# Encryption in transit and at rest

| ID | INV55-SEC-ENCRYPTION | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: security-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

## In transit (#44)
- Vault address MUST be `https`; `http` is refused unless `allow_insecure_http=True` AND host is `127.0.0.1`, `localhost` or `::1` (`VaultProvider.__post_init__`). This exists for loopback tests only.
- `build_tls_context`: `ssl.create_default_context(cafile=...)`, `minimum_version = TLSv1_2`, `check_hostname = True`, `CERT_REQUIRED`, optional client cert.
- Cipher suites: Python/OpenSSL defaults; no explicit cipher policy. Certificate pinning beyond CA file: NOT IMPLEMENTED.
- Caller → INV-55 transport: in-process API; TLS for any network front end is the host's responsibility (NOT IMPLEMENTED here).

## At rest (#45)
- INV-55 stores no secret values at rest. Values exist only in process memory.
- At-rest protection is delegated to Vault (seal: Shamir / auto-unseal via cloud KMS or HSM). Configuration of the seal is out of scope (`contract.py` not_owns "Key custody and HSMs").
- Audit file contains no values; protected by file mode 0600 and host disk encryption (deployment responsibility).

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
