# Compatibility — PLN-06 (4.3.0)

Policy: `docs/VERSIONING.md`.

## API compatibility

- 4.1/4.2 calls to `DataPlane(...)`, `admit(...)`, `complete/cancel`, `health()`, `metrics()` are unchanged (retained tests in `tests/test_runtime.py`).
- 4.3 adds locality `vm_control` (additive enum value in `PK_TRANSFER/1`), the governed service, and new schemas. `_StructuredError` now subclasses `Exception` (existing `except ValueError/PermissionError/RuntimeError` handlers keep working).
- `PK_DATA_PLANE_HEALTH/1` is deprecated in favour of `/2` (DEP-001; removal no earlier than 5.0.0).

## Supported-version matrix

| Dimension | Supported | Executed evidence (this release) |
|---|---|---|
| Python | 3.10, 3.11, 3.12, 3.13 | 3.11.15 — 92 run / 89 pass / 3 waived skips, normal and `-O` |
| CPU arch | x86_64, arm64 | x86_64 only (W-014) |
| OS | Linux (POSIX shm, AF_VSOCK) | Linux 6.x |
| TLS | OpenSSL ≥ 1.1.1, TLS ≥ 1.2 | system OpenSSL (see evidence dossier) |
| `pk06-rpc` | v1 | v1 ↔ v1; unknown version refused (tested) |
| Component interface | `pk:data-plane/transfer@1.0.0` | tested; other versions refused |
| Hypervisors (vsock) | KVM/Firecracker/Cloud Hypervisor (planned) | socketpair profile only (W-014) |
| RDMA stacks | none shipped | probe only (W-004) |
| pk_core | pinned version TBD | unavailable (W-008) |
| GAP-13 / GAP-14 / PLN-03 | protocol v1 | reference fixtures only (W-005..W-007) |
