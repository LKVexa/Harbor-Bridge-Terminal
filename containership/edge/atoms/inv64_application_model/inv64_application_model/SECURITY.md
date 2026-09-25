# Security notes

4.3.0 moves the security controls that 4.2.0 left to "the calling control plane"
into this package. The full architecture and threat model are in
**SECURITY_ARCHITECTURE.md**; vulnerability handling is in **SECURITY_RESPONSE.md**.

## Trust boundary

Manifest input is untrusted. `manifest.py` (with `redaction.py`) remains pure
Python with no filesystem, network, process, credential, or device access and
is importable without `pk_core`. The integration boundary (`service.py`)
authenticates (`auth.py`) and authorizes (`authz.py`) every caller before any
semantic processing, binds tenancy to the authenticated identity
(`tenancy.py`), bounds work (`semantics.py`), and records tamper-evident audit
events (`audit.py`).

## Parser defenses (4.2.0, extended in 4.3.0)

1 MiB byte ceiling; nesting ≤ 64 (4.3.0 — 4.2.0 raised `RecursionError`);
duplicate keys refused; non-finite numbers refused; collection ceilings;
strict identifiers; aggregate validation; canonical identity only for valid
manifests; inline secrets refused and never echoed (4.3.0).

## Residual risks (tracked)

- Logical, not memory, isolation between tenants in one process (REG-005).
- No managed signer / KMS / trust anchors provisioned; release signatures are ephemeral (REG-003).
- `pk_core` cannot be reviewed (absent).
- Validation cost increase from secret scanning (REG-004).

## Security testing

`tests/test_v43.py` (abuse cases per control), `tools/fuzz.py` (property,
mutation and differential fuzzing with regression corpus),
`tools/faults.py`, `tools/stress.py`, `tools/secret_scan.py`.
