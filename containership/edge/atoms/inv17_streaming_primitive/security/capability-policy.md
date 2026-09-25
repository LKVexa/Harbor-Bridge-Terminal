# INV-17 Capability / Authorization Policy

**Controls:** C024, C042, C043
**Owner:** UNASSIGNED — owner to fill
**Machine-readable companion:** `security/capability-policy.json` (maintained separately)

## Rights (`security::RIGHTS`)

| Right | Checked where (in code) | Meaning |
|---|---|---|
| `open` | `control::StreamRegistry.open` | Create a stream under a tenant/workload/stream id |
| `read` | `StreamRegistry.get(..., right="read")` when a caller requests it | Obtain handle for reading |
| `write` | `StreamRegistry.write` (via `get`) | Write through the registry (quota/shed enforced) |
| `grant` | `StreamRegistry.get(..., right="grant")` when requested | Obtain handle to grant credit |
| `close` | Not checked by `StreamRegistry.close` (takes no token) | Declared only |
| `transfer` | `StreamRegistry.transfer` | Move a stream to another tenant/workload; **always single-use** |
| `admin` | Not used by token path; emergency controls use `admins` allow-list | Reserved |

`security::END_RIGHTS`: reader = {read, grant, close}; writer = {write, close}. Advisory template
for issuers; not enforced by `Stream`.

## Policy rules implemented

1. **Default deny:** every registry operation except `close`/`streams`/`health` requires a verified token.
2. **Least privilege binding:** a token binds exactly one stream id, tenant and workload.
3. **Bounded lifetime:** `ttl` must satisfy `0 < ttl <= max_ttl` (default 300 s).
4. **Single use:** tokens containing `transfer`, or issued with `single_use=True`, carry the signed claim `su` (`Capability.single_use`) and are rejected on reuse (`TokenReplay`). Only single-use nonces are held in the bounded replay cache; when it is full, verification fails closed with `TrustServiceUnavailable(dependency="replay-cache")` rather than evicting a live nonce.
5. **Revocation:** `CapabilityAuthority.revoke(token)`.
6. **Emergency controls** (`emergency_disable`, `enable`, `quarantine`, `release`) require a principal in `StreamRegistry.admins`; denials audited as `authz.denied`.
7. **Admission gate before authz:** `StreamRegistry._gate` refuses disabled components and frozen tenant/workload scopes (`ComponentDisabled`) before token verification.

## Delegation / attenuation

Not implemented. Tokens cannot be attenuated by holders; only the issuer (host holding `KeyRing`) mints.

## Gaps to close

- `StreamRegistry.close` takes no token — any caller with the registry object may close any stream id.
- Rights `close` and `admin` are not enforced on any path.
- Tests: `tests/test_security.py`, `tests/test_control.py` (planned).
