# Versioning and compatibility (INV-40-C016, C027)

* Package: SemVer. Major = breaking contract change; minor = additive; patch = fixes.
* Wire documents are `NAME/major` (`PK_FULL_VM/1`, `PK_FULL_VM_BOOT/1`, `PK_FULL_VM_STATE/1`, `PK_FULL_VM_ERROR/1`, `PK_FULL_VM_CONFIG/1`, `PK_FULL_VM_AUDIT/1`). Within a major: fields may be *added* (optional), never removed, renamed or re-typed; error codes are append-only (`fvt/errors.py::CATALOG`).
* Supported window: this build speaks major 1 of every document. A peer offering no common major gets `PK_FULL_VM_VERSION_UNSUPPORTED` (`fvt/compat.py::negotiate`). When major 2 ships, N and N-1 are both served for at least one minor release cycle (policy PROPOSED).
* Config documents carry `config_version`; activation records it with provenance.
* Deprecations are entered in `governance/EXCEPTIONS.json` with an expiry.
