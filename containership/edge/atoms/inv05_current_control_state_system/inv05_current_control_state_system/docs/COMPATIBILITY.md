# Compatibility and support matrix

Traceability: C016, C027, C084, C093; MC-027, MC-046-01.

| Component | Supported | Notes |
|---|---|---|
| Python runtime | 3.10 – 3.13 (CI: 3.10, 3.11, 3.12, 3.13) | `backend.SUPPORTED_PYTHON`, startup self-test |
| OS / arch | Linux x86_64 and aarch64 (POSIX fsync semantics) | macOS dev only; Windows unsupported |
| `cryptography` | ≥ 42, < 47 (tested 46.0.7) | required when `storage.encrypt_at_rest=true` |
| Protocol | `PK_CSTATE` 1.0 and 1.1 (server 1.1) | N/N-1 minors; new minors add optional fields only |
| Event / record / snapshot / backup schemas | `cstate.event/1`, WAL v1, `cstate.snapshot/1`, `cstate.backup/1` | readers reject unknown majors |
| Backend | `inv05-local-mvcc/1` (proven); external consensus backend **pending** (ADR-002) | |
| `pk_core` | pin pending (`deploy/pk_core_pin.json`, EX-003) | framework gate only |
| Adjacent layers INV-04 / GAP-05 / INV-07 / PLN-03 | protocol 1.x; GAP-05 via `cstate.repl_*/1.0` | executable environments pending (EX-004) |

Mixed-version policy: during a rolling upgrade N and N-1 servers coexist; clients negotiate with `hello` and use only the intersection of capabilities. Downgrade: WAL v1 and snapshot v1 are unchanged in 4.3.0, so rollback to 4.2.x is data-compatible for the store files (4.2.x never read them). Any future record-format change requires a new major and a migration step (`docs/ROLLOUT.md`).
