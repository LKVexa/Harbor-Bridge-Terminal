# ADR-003 — Filesystem strategy: descriptor-relative, no string re-resolution

**Status:** Accepted · **Date:** 2026-09-22

## Decision
* A preopen is an **open directory fd** acquired once at grant time (`O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC`).
* Guest paths are validated lexically (relative, UTF-8, no NUL, no `..`, ≤ 4096 B, ≤ 255 B/component, ≤ 128 components) and **never joined to a host path string**.
* Linux ≥ 5.6: a single `openat2(fd, path, RESOLVE_BENEATH|RESOLVE_NO_SYMLINKS|RESOLVE_NO_MAGICLINKS|RESOLVE_NO_XDEV)` — atomic against rename/symlink races.
* Other POSIX: component-wise `openat(..., O_NOFOLLOW)` walk with per-step device check.
* **All symlinks are refused**, including ones that would stay inside the preopen (simplest provable rule).
* Windows: unsupported → `PROVIDER_UNAVAILABLE` (fail closed). A handle-relative `NtCreateFile` implementation is future work (MC-020).

## Evidence
`tests/test_fs_descriptor.py` runs every case under both resolvers: final/intermediate symlink, relative inner symlink, host-root rename-and-replant, 3 000-iteration symlink-swap race, mount crossing via `/proc`, read-only preopens, closed preopen. `test_adversarial.py::Fuzz.test_path_resolvers_never_escape` fuzzes both resolvers.
