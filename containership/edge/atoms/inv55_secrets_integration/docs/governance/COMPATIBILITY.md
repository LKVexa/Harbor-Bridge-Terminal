# Supported-version compatibility matrix (checklist #16, #83, #92)

| Component | Supported | Evidence | Status |
|---|---|---|---|
| CPython | ≥ 3.10 (declared in pyproject) | test suite run on 3.11.15 in this pass | 3.10 / 3.12 / 3.13 NOT RUN |
| OS | Linux (tested), Windows/macOS (stdlib only; untested) | — | partial |
| Vault server | 1.15 – 1.18 (proposed range, KV v2 API) | **none** — adapter only exercised against `tests/fake_vault.py` | NOT CERTIFIED (W-001) |
| Vault KV engine | v2 only | KV v1 unsupported by design | — |
| Vault auth | token file, AppRole | double only | NOT CERTIFIED |
| Wire protocol | PK_SECRET_{RESOLVE,ROTATE,SCOPE}/1 | schemas + fixtures + tests | implemented |
| Config schema | inv55-config/1 | tests | implemented |
| pk_core | whatever version the estate ships | not present in upload | BLOCKED |
Third-party runtime dependencies: **none** (stdlib only); the lock is therefore empty and the SBOM lists only this package.
