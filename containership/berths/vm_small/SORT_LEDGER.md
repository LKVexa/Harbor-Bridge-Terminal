# vm_small -- sort ledger

Berth `vm_small` (vm), UC-2.1.3. Source: `Small.zip` (zip, 3fd95ec274d475d759d60832b413fbff9e3a8db5003da7e34a3c37d5b3b79fab). 20 scripts sorted by policy 1.0.1 (rules S0-S9, first match wins; see `reports/SORT_POLICY.md`).

| node | scripts | bytes | rules | kinds |
|---|---:|---:|---|---|
| `N_SMALL` (DF_Small) | 9 | 6944 | S0:1, S6:6, S8:2 | json:5, markdown:2, mssl_asm:1, mssl_doc:1 |
| `N_MEDIUM` (DF_Medium) | 2 | 2335 | S5:2 | json:1, sums:1 |
| `N_LARGE` (DF_Large) | 8 | 100450 | S4:8 | c:5, c_header:2, make:1 |
| `N_XLARGE` (DF_Xtra_Large) | 1 | 176 | S2:1 | image:1 |

| script | node | rule | kind | bytes | lines | band | why |
|---|---|---|---|---:|---:|---|---|
| `MANIFEST.json` | `N_MEDIUM` | S5 | json | 742 | 1 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `Makefile` | `N_LARGE` | S4 | make | 2953 | 75 | LOW | make belongs with the freestanding C core and its build system |
| `README.md` | `N_SMALL` | S8 | markdown | 2530 | 43 | LOW | markdown of 2530 bytes (<= 8 KiB): teaching-sized |
| `SHA256SUMS.txt` | `N_MEDIUM` | S5 | sums | 1593 | 19 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `deploy/BOTTLE_ROCKET_SIM_CORE_3.0.0_MODEL.brimg` | `N_XLARGE` | S2 | image | 176 | 0 | LOW | bulk cargo (image of 176 bytes) needs the roomiest, hosted node |
| `evidence/AUDIT_DIGEST.json` | `N_SMALL` | S6 | json | 542 | 1 | LOW | json of 542 bytes (<= 4 KiB) |
| `evidence/OPERATIONAL.json` | `N_SMALL` | S6 | json | 612 | 1 | LOW | json of 612 bytes (<= 4 KiB) |
| `evidence/SIZE.json` | `N_SMALL` | S6 | json | 252 | 1 | LOW | json of 252 bytes (<= 4 KiB) |
| `evidence/q17/SIDECAR.json` | `N_SMALL` | S6 | json | 188 | 1 | LOW | json of 188 bytes (<= 4 KiB) |
| `examples/boot.mssl` | `N_SMALL` | S0 | mssl_asm | 189 | 9 | LOW | MSSL/ASM-1 assembly is the guest dialect of BOTTLE ROCKET 3.0.0-MODEL |
| `host/br_sizes.c` | `N_LARGE` | S4 | c | 622 | 15 | MID | c belongs with the freestanding C core and its build system |
| `host/brctl.c` | `N_LARGE` | S4 | c | 11709 | 243 | VERY_HIGH | c belongs with the freestanding C core and its build system |
| `spec/BR_SPEC.json` | `N_SMALL` | S6 | json | 1158 | 1 | LOW | json of 1158 bytes (<= 4 KiB) |
| `spec/PROFILE.md` | `N_SMALL` | S8 | markdown | 815 | 7 | LOW | markdown of 815 bytes (<= 8 KiB): teaching-sized |
| `src/CORE.mssl` | `N_SMALL` | S6 | mssl_doc | 658 | 1 | LOW | mssl_doc of 658 bytes (<= 4 KiB) |
| `src/brasm.c` | `N_LARGE` | S4 | c | 9509 | 217 | VERY_HIGH | c belongs with the freestanding C core and its build system |
| `src/brasm.h` | `N_LARGE` | S4 | c_header | 232 | 10 | LOW | c_header belongs with the freestanding C core and its build system |
| `src/brvm.c` | `N_LARGE` | S4 | c | 69670 | 1570 | VERY_HIGH | c belongs with the freestanding C core and its build system |
| `src/brvm.h` | `N_LARGE` | S4 | c_header | 5482 | 158 | HIGH | c_header belongs with the freestanding C core and its build system |
| `tests/test_main.c` | `N_LARGE` | S4 | c | 273 | 10 | MID | c belongs with the freestanding C core and its build system |
