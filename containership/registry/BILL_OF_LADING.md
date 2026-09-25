# Bill of lading -- UC-2.8.0

6 berth(s), 6691 scripts, 26890898 bytes. Per node: N_SMALL 4341, N_MEDIUM 1841, N_LARGE 83, N_XLARGE 426.

| berth | kind | scripts | bytes | N_SMALL | N_MEDIUM | N_LARGE | N_XLARGE | CARGO.pal witness | BERTH.pal witness (studio R2) | segments | .tif fabrics | hull cargo |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---|
| `sub_mssl_to_lctlc` | subsystem | 1 | 18488 | 0 | 0 | 0 | 1 | `3704379664640541329` | `3765766587618232233` | 1 | 6 | - |
| `sub_pa21_language_studio` | subsystem | 23 | 478955 | 4 | 1 | 1 | 17 | `13787820642529720862` | `10906907802389691971` | 1 | 6 | - |
| `vm_large` | vm | 893 | 4241632 | 438 | 359 | 41 | 55 | `11338925930947832812` | `15355811372695196182` | 11 | 6 | - |
| `vm_medium` | vm | 241 | 1513315 | 96 | 61 | 30 | 54 | `75913186513227538` | `14203227011441505260` | 3 | 6 | - |
| `vm_small` | vm | 20 | 109905 | 9 | 2 | 8 | 1 | `9816649208978189246` | `15298326914918377449` | 1 | 6 | - |
| `vm_xtra_large` | vm | 5513 | 20528603 | 3794 | 1418 | 3 | 298 | `18176639773570921958` | `3207394530149930380` | 66 | 6 | - |

`.tif fabrics` counts the containers with their own fabric image (the five DF containers + the hull face); `hull cargo` names the studio containers a berth carries broken up (BUILD re-assembles and mounts them in the hull with their own pictures). Rebuilt from disk on every change; `uc verify` compares this file with a fresh scan.
