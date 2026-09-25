# Copy / hop / context-switch analysis (MC-064; C065, C066)

Measured by `bench/perf_suite.py` (`copies` block) and asserted in `tests/test_repository.py`.

| Hop | Copies of image bytes | Notes |
|---|---|---|
| caller → `ImageBlob.of(bytes)` | 0 (a `bytes` argument is reused; `bytearray`/`memoryview` are copied once) | sha256 + sha512 computed once |
| blob → `elf.parse` | 0 (`bytes(b) is b`) | memoryview slices, `bytes.find` for names |
| blob → VMM | 1 write to a private 0400 file, then 1 read to re-hash | the VMM maps the file itself |
| process hops | 1 child process per instance (the VMM); no shell; no intermediate helpers | |

Duplication to watch: `Symbol` dataclass objects dominate time and memory on large symbol tables
(20,000 symbols ≈ 4.9 MB peak, p50 ≈ 90–110 ms). This is TD-1: a lazy symbol iterator would remove it.
