# CHERI backend adapter (INV30-GAP-004 · INV-30-C010, C021, C031, C084)

`CheriHardwareBackend` is complete on the Python side (discovery, availability, fail-closed selection); the
**native helper is not built** — it needs CHERI hardware or CHERI-QEMU plus CHERI LLVM, neither of which exists in
the remediation environment.

## Helper protocol (stdin/stdout JSON, one request per line)
```
{"op":"mint","base":N,"length":N,"perms":["read"]}  -> {"ok":true,"handle":"h..."}  (sealed, otype = INV-30)
{"op":"derive","handle":"h","base":N,"length":N,"perms":[..]} -> CSetBounds/CAndPerm; exact-bounds or refuse
{"op":"check","handle":"h","addr":N,"size":N,"op":"read"} -> performs the real load/store via the capability;
      hardware fault (SIGPROT) is mapped to BOUNDS_VIOLATION / PERMISSION_VIOLATION
{"op":"invalidate","handle":"h"} -> clears the tag (CClearTag) / revocation via CheriBSD revoker
{"op":"forge_test"} -> writes capability bytes as data, reloads, returns tag bit (must be 0)
```
## Work remaining (tracked as INV30-GAP-004 blockers)
1. Select profile (Morello board or CHERI-RISC-V FPGA/QEMU) and record in CHERI_SPEC_PIN.md.
2. Build helper purecap with CHERI Clang; pin its digest in config; verify digest before exec.
3. Enable `test_hardware_backend` (differential vs model + tag-forgery test) on that node in CI.
4. Measure hardware NFR thresholds; add hardware rows to `config/perf_thresholds.json`.
