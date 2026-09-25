# Ambient-authority confinement

| ID | INV55-SEC-AMBIENT | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: security-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

In code:
- No global "current user" or environment-variable identity fallback: every operation takes an explicit credential (`identity.py` module docstring; `_guard`).
- Provider, authenticator, policy, audit, clock are injected into `SecretsService.__init__`; nothing is read from ambient globals.
- Config refuses plaintext credentials (`config.py::_CREDENTIAL_KEYS`).
- Ambient filesystem reads: `KubernetesAuth.login` reads `jwt_path`; `FileAuditSink` writes `path`; `config.load_layers` reads the config dir.

Process confinement (MUST at deployment; NOT IMPLEMENTED in repo — no manifests shipped):
- Run as non-root, read-only root FS, writable only the audit directory.
- Egress only to Vault address(es) and telemetry collector.
- Drop all Linux capabilities; seccomp RuntimeDefault; no host PID/IPC/network.
- Disable core dumps (memory-handling.md).

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
