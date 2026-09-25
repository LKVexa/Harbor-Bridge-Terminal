# Least privilege (INV-38-C042) & ambient authority (C043)

The data-plane process runs non-root holding only `CAP_IPC_LOCK`; forbidden
capabilities (`CAP_SYS_ADMIN`, `CAP_NET_ADMIN`, `CAP_SYS_RAWIO`, `CAP_DAC_OVERRIDE`)
are asserted absent. Device access is restricted to the assigned VF; inherited
FDs and env secrets must be sanitized. `privilege_check.py` returns violations and
fails closed. Matrices: `security/privilege-matrix.yaml`,
`security/ambient-authority-inventory.yaml`, `security/sandbox-profile.json`.
Tests: `tests/test_privilege.py`. **Status:** `IN_PROGRESS` — runtime enforcement
and sandbox-escape tests need a real OS/sandbox host.
