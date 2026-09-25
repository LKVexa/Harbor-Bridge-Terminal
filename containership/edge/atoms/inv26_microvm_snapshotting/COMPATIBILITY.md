# Versioning and compatibility (C016, C027, C084, C093)

Source: `compatibility.json`. Package versions follow SemVer; each wire/storage contract has its own
independent major version (`PK_SNAPSHOT_*/<n>`). Receivers reject unknown fields and unknown majors **before
mutating state** (`schema.require` raises `SNAP_UNSUPPORTED_VERSION` for a same-family different version).
Security features are not negotiable: there is no downgrade path that drops encryption, binding, grants or
reseed (LOCKED config keys).

**Golden N-1/N/N+1 fixtures:** `tests/fixtures/conformance/cases.json` contains v2 documents (N) that must pass
and v1 documents (N-1) that must be refused; there is no N+1 yet. Mixed-version rolling-upgrade tests with
persisted snapshots across two real releases cannot run until a second release exists (C027 PARTIAL).

**Old snapshots** are re-captured, never migrated, when the VMM major, CPU architecture, device model or
envelope major changes. The 5.0.0 in-memory `SnapshotStore` (`snapshot.py`) is retained as the dependency-free
reference model and its tests still pass; it is not used by the service.
