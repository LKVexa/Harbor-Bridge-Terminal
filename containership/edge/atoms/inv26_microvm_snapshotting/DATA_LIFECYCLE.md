# Data lifecycle, secure erase and remanence (X010, C039, C095)

| Location | Content | Lifetime | Control |
|---|---|---|---|
| blob storage | ciphertext | until delete | per-snapshot DEK; delete = blob overwrite+unlink **and** wrapped DEK replaced by `erased` (crypto-erase) |
| metadata | wrapped DEK, manifest, grants, config | until delete / forever for tombstones | wrapped DEK erased on delete; no plaintext |
| work dir (must be tmpfs 0700) | VMM state + memory files | seconds, during capture/load | state files overwritten+unlinked; mapped memory files unlinked only (overwriting a MAP_PRIVATE-mapped file corrupts the guest) |
| process heap | plaintext image, DEK, seed | one operation | dropped after use; bytearray DEK zeroized; immutable `bytes` copies cannot be wiped in CPython (residual) |
| logs / audit / metrics / responses | identifiers, codes, sha256(seed) proof | retention policy | schema/allowlist redaction; tests assert seed, token signatures and wrapped DEKs never appear |
| crash dumps / swap | could contain heap | — | deployer: `LimitCORE=0`, no swap or encrypted swap for workers (RUNBOOK day-0) |
| backups (metadata export) | wrapped DEKs | per backup policy | checksummed; useless without KEK; KEK destroy = crypto-erase of backups too |

**Residual risk statement:** plaintext guest memory necessarily exists in host RAM and tmpfs during restore;
CPython cannot guarantee zeroization of immutable buffers; SSD/COW media make overwrite-before-delete
best-effort — crypto-erase is the primary deletion mechanism. Tests:
`test_delete_crypto_erases`, `test_no_secret_material_in_logs_audit_or_responses`,
`FirecrackerEndToEnd.test_full_path` (work dir empty after restore).
