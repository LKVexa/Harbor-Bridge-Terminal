# Compatibility — INV-37 v4.3.0

Covers INV-37-C016, C027, C084, C093. Status legend: **C** certified in this repository's run · **D** designed, not certified · **U** unsupported (fails closed).

## Versioning policy (C016)
| Surface | Version id | Compatible change | Breaking change → requires |
|---|---|---|---|
| Python API | package semver | add optional kwargs/methods | remove/rename/semantic change → major |
| Manifest / chunk | `PK_BULK_MANIFEST/1`, `PK_BULK_CHUNK/1` | add optional fields ignored by readers | any change to digest definition or required fields → `/2` + negotiation |
| Resume | `PK_BULK_RESUME/1` (read), `/2` (read/write) | — | new id |
| Config | `INV37_CONFIG/1` | add key with safe default | rename/remove/semantic change → `/2` + migration notes |
| Checkpoint | `INV37_CHECKPOINT/1`, `INV37_LEASE/1` | add ignored field (seal covers it) | layout change → `/2`, N-1 reader, migration tool |
| Transport ABI | `INV37_SHM_DESCRIPTOR/1` | — | new id |
| Token | `v1` | add optional claim | new version |
Deprecation minimum 180 days / one minor release (governance/DEPRECATIONS.json). Golden fixtures: `conformance/golden/v4.2.0.json` (produced by the original 4.2.0 code) + `conformance/fixtures/` locked by `FIXTURES.lock`; changing a locked fixture fails CI and needs architecture review. Emergency exception: waiver with ≤ 90-day expiry and a rollback plan.

## Matrix (C093)
| Dimension | Value | Status |
|---|---|---|
| CPython | 3.11.15 | C |
| CPython | 3.10, 3.12, 3.13 | D (multi-version CI not run) |
| OS | Linux x86_64 | C |
| OS / arch | Linux aarch64, macOS, Windows | D |
| Shared memory | POSIX shm (`/dev/shm`) | C |
| Host ↔ guest | virtio/vhost, ivshmem | U |
| Containers | shared IPC namespace between producer and receiver | D |
| Peer 4.2.0 | RESUME/1, manifest v1 | C (fixture `negotiate.v1_peer`, golden) |
| Peer 4.3.0 | RESUME/2, SHM descriptor v1 | C |
| pk_core | any | D — optional; adapter tests NOT_EXECUTED here; no version pinned |
| INV-36 / GAP-14 / PLN-06 / INV-38 | — | D — contract references only; integration is gate criterion `vm_topology_integration` |

Rolling upgrade: 4.2 and 4.3 can coexist; 4.3 negotiates RESUME/1 with 4.2 peers. Downgrade 4.3 → 4.2 loses durable checkpoints (4.2 is in-memory); restart affected transfers from source.
