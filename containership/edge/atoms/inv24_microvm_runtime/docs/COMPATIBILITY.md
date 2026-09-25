# Compatibility and versioning policy (MC-011)

- **Runtime version** follows SemVer. MAJOR changes may break schemas/snapshots; MINOR adds fields/components compatibly; PATCH fixes only.
- **Schemas** are versioned by suffix (`PK_MICROVM/1`). A breaking change creates `/2`; `/1` is supported for one MAJOR release after `/2` ships.
- **Snapshots** restore only on the same runtime MAJOR, an approved Firecracker version in `supported_firecracker`, same arch and a CPU-feature superset.
- **Error codes** are append-only.

Machine-readable matrix: `release/compatibility.json`. Status of every cell other than
"python 3.10–3.12 / linux / stdlib" is **NOT_TESTED** until a real-host matrix run (MC-049).
