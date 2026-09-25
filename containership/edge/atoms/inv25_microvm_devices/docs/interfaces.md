# INV-25 boundary inventory (C021, C025)

| Boundary | Kind | Contract | Trust zone |
|---|---|---|---|
| `DeviceCatalogue` / `DeviceSpec` | in-process Python API | `model.py` | trusted caller |
| `catalogue_from_export` | file/artifact parse | PK_DEVICE_CATALOGUE/1 | untrusted input |
| `DeviceCatalogue.diff` / `replace` | data | PK_DEVICE_SURFACE_DIFF/1 | — |
| `CatalogueStore.propose/approve/activate/rollback/emergency_disable/restore_device` | control-plane API (wrap as RPC) | tokens + PK_DEVICE_ERROR/1 | cross-zone, authenticated |
| Activation history | event/file | PK_DEVICE_CONFIG_ACTIVATION/1 | append-only |
| Audit log | event/file (JSONL) | PK_DEVICE_AUDIT_EVENT/1 | append-only, hash-chained |
| State file | file | INV25_STORE_STATE/1 (atomic replace, digest re-verified on load) | local |
| `health()` / `signals()` / `explain()` | diagnostics | JSON dicts | operator |
| Runtime handoff (INV-24) | peer | `CatalogueStore.active` + `permits()` | peer |
| Policy (GAP-13) | peer | `dependency_probe` + fixture `decide()` | peer |
| `pk_core` | framework | `pk_bootstrap.require_pk_core` | build-time |

No WIT/RPC server ships in this package; a service wrapper must enforce authn/authz at its edge by
calling the store API (which enforces again — defence in depth).

## Timeout / cancellation / retry / idempotency / backpressure (C025)
- All operations are synchronous and bounded (validated ceilings); no call blocks on the network.
- Callers own timeouts; cancellation before the commit point leaves no trace except audit.
- Idempotency: activation replays of a committed candidate return the original record; tokens are
  single-use (nonce); CAS on `expected_digest` prevents lost updates.
- Backpressure: per-subject token bucket and a 32-slot pending queue shed load with retryable codes.
