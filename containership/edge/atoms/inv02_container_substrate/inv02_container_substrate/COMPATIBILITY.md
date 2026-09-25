# Compatibility matrix (MC74 / MC66)

## Declared support

| Dimension | Supported | Notes |
|---|---|---|
| Python | 3.10 – 3.13 (CPython) | stdlib only; uses `str.removeprefix`, PEP 604 types |
| OS | Linux | store locking uses `fcntl`; runtime paths are Linux-only |
| Architectures | amd64, arm64 | platform selection also handles arm/v5–v7, 386 |
| OCI runtimes | runc ≥ 1.1, crun ≥ 1.8; runsc (gVisor), kata as sandboxed classes | CLI adapter `runtime.OCIRuntime` |
| cgroups | v2 (unified) for `CgroupV2Manager`; runc handles v1 hosts from the same spec | |
| Image formats | OCI image manifest/index v1.1; Docker schema 2 manifest/list | schema 1 refused |
| Layer compression | tar, tar+gzip | zstd refused with `LAYER_UNSUPPORTED_COMPRESSION` |
| Persisted store schema | 2 (reads 1 via migration) | newer schemas refused |
| Legacy manifests | v4.1 `{"layers":[...]}` read + `migrate_legacy_manifest` | |

## Verified tuples (evidence in `evidence/`)

| Python | Kernel | Arch | Runtime | cgroup | Result |
|---|---|---|---|---|---|
| 3.11.15 | 6.18.44 | x86_64 | runc 1.3.5 (libseccomp 2.5.5) | v1 | unit + integration pass; user-namespace container **skipped** (host forbids `MS_PRIVATE` remount inside userns) |

## Not yet verified (open for MC66 / E-04)

arm64 host; crun; runsc; kata; cgroup v2 host with `CgroupV2Manager` against a live
cgroupfs; rootless (user-namespace) containers; Python 3.10/3.12/3.13; a real remote
registry (Docker Hub / GHCR / Harbor — MC58). CI (`.github/workflows/ci.yml`) runs the
Python matrix; the runtime matrix needs self-hosted runners.
