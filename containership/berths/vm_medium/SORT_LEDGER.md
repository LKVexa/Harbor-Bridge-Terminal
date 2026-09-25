# vm_medium -- sort ledger

Berth `vm_medium` (vm), UC-2.1.3. Source: `Medium.zip` (zip, fcc7ec8e027d187fa00ab7bc7bb9e69a98f35c362931bc6a6b636541ce9f9c1a). 241 scripts sorted by policy 1.0.1 (rules S0-S9, first match wins; see `reports/SORT_POLICY.md`).

| node | scripts | bytes | rules | kinds |
|---|---:|---:|---|---|
| `N_SMALL` (DF_Small) | 96 | 142697 | S6:44, S7:1, S8:51 | markdown:49, json:33, log:11, text:2, shell:1 |
| `N_MEDIUM` (DF_Medium) | 61 | 518146 | S0:2, S5:37, S6:10, S7:1, S8:11 | json:18, sums:16, markdown:13, log:6, plist:3, lctlc11:2, signature:1, key:1 |
| `N_LARGE` (DF_Large) | 30 | 504357 | S4:28, S6:1, S7:1 | c:20, c_header:7, make:1, log:1, shell:1 |
| `N_XLARGE` (DF_Xtra_Large) | 54 | 348115 | S2:28, S3:26 | python:26, binary:20, image:8 |

| script | node | rule | kind | bytes | lines | band | why |
|---|---|---|---|---:|---:|---|---|
| `AUDIT_ERRATA.md` | `N_SMALL` | S8 | markdown | 3693 | 51 | MID | markdown of 3693 bytes (<= 8 KiB): teaching-sized |
| `CHANGELOG_4_8.md` | `N_SMALL` | S8 | markdown | 1717 | 16 | LOW | markdown of 1717 bytes (<= 8 KiB): teaching-sized |
| `CHANGELOG_4_9.md` | `N_SMALL` | S8 | markdown | 1313 | 21 | LOW | markdown of 1313 bytes (<= 8 KiB): teaching-sized |
| `CHANGELOG_5_0.md` | `N_SMALL` | S8 | markdown | 1007 | 9 | LOW | markdown of 1007 bytes (<= 8 KiB): teaching-sized |
| `MANIFEST.json` | `N_MEDIUM` | S5 | json | 10764 | 321 | MID | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `Makefile` | `N_LARGE` | S4 | make | 16848 | 250 | MID | make belongs with the freestanding C core and its build system |
| `PACKAGE_INFO.json` | `N_SMALL` | S6 | json | 1350 | 31 | LOW | json of 1350 bytes (<= 4 KiB) |
| `README.md` | `N_MEDIUM` | S8 | markdown | 8221 | 69 | MID | markdown of 8221 bytes (<= 128 KiB) |
| `REPRODUCE_4_8.md` | `N_SMALL` | S8 | markdown | 1146 | 24 | LOW | markdown of 1146 bytes (<= 8 KiB): teaching-sized |
| `REPRODUCE_4_9.md` | `N_SMALL` | S8 | markdown | 1061 | 26 | LOW | markdown of 1061 bytes (<= 8 KiB): teaching-sized |
| `REPRODUCE_5_0.md` | `N_SMALL` | S8 | markdown | 539 | 14 | LOW | markdown of 539 bytes (<= 8 KiB): teaching-sized |
| `SHA256SUMS` | `N_MEDIUM` | S5 | sums | 23824 | 240 | MID | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `br_prod_host.plist` | `N_MEDIUM` | S5 | plist | 430 | 14 | LOW | plist named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `brtrust.plist` | `N_MEDIUM` | S5 | plist | 430 | 14 | LOW | plist named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `brvm.plist` | `N_MEDIUM` | S5 | plist | 6137 | 183 | MID | plist named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `compat/BOTTLE_ROCKET_4.1.0.brimg` | `N_XLARGE` | S2 | image | 176 | 0 | LOW | bulk cargo (image of 176 bytes) needs the roomiest, hosted node |
| `compat/BOTTLE_ROCKET_4.2.0.brimg` | `N_XLARGE` | S2 | image | 272 | 0 | LOW | bulk cargo (image of 272 bytes) needs the roomiest, hosted node |
| `compat/BOTTLE_ROCKET_4.6.0.brimg` | `N_XLARGE` | S2 | image | 272 | 0 | LOW | bulk cargo (image of 272 bytes) needs the roomiest, hosted node |
| `compat/BOTTLE_ROCKET_4.6.0.brsb` | `N_XLARGE` | S2 | image | 688 | 0 | LOW | bulk cargo (image of 688 bytes) needs the roomiest, hosted node |
| `conformance/ISA_ABI_CORPUS_4_3_0.json` | `N_MEDIUM` | S6 | json | 5885 | 267 | HIGH | json of 5885 bytes (<= 256 KiB) |
| `deploy/BOTTLE_ROCKET_4.7.0_COLUMNED_LCTL_VIRTUAL_DEVICE_IO_SERVICE_ARCHITECTURE.brimg` | `N_XLARGE` | S2 | image | 272 | 0 | LOW | bulk cargo (image of 272 bytes) needs the roomiest, hosted node |
| `deploy/BOTTLE_ROCKET_4.7.0_COLUMNED_LCTL_VIRTUAL_DEVICE_IO_SERVICE_ARCHITECTURE.brir` | `N_SMALL` | S8 | text | 547 | 8 | LOW | text of 547 bytes (<= 8 KiB): teaching-sized |
| `deploy/BOTTLE_ROCKET_4.7.0_COLUMNED_LCTL_VIRTUAL_DEVICE_IO_SERVICE_ARCHITECTURE.brsb` | `N_XLARGE` | S2 | image | 688 | 0 | LOW | bulk cargo (image of 688 bytes) needs the roomiest, hosted node |
| `deploy/BOTTLE_ROCKET_4.7.0_COLUMNED_LCTL_VIRTUAL_DEVICE_IO_SERVICE_ARCHITECTURE.provenance.json` | `N_MEDIUM` | S5 | json | 514 | 1 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `docs/4.9/ABI.md` | `N_SMALL` | S8 | markdown | 318 | 2 | LOW | markdown of 318 bytes (<= 8 KiB): teaching-sized |
| `docs/4.9/ARCHITECTURE.md` | `N_SMALL` | S8 | markdown | 532 | 2 | LOW | markdown of 532 bytes (<= 8 KiB): teaching-sized |
| `docs/4.9/BRIM.md` | `N_SMALL` | S8 | markdown | 362 | 2 | LOW | markdown of 362 bytes (<= 8 KiB): teaching-sized |
| `docs/4.9/BUILD.md` | `N_SMALL` | S8 | markdown | 442 | 2 | MID | markdown of 442 bytes (<= 8 KiB): teaching-sized |
| `docs/4.9/COLUMNED_LCTL.md` | `N_SMALL` | S8 | markdown | 374 | 2 | LOW | markdown of 374 bytes (<= 8 KiB): teaching-sized |
| `docs/4.9/DEVICE.md` | `N_SMALL` | S8 | markdown | 328 | 2 | LOW | markdown of 328 bytes (<= 8 KiB): teaching-sized |
| `docs/4.9/ISA.md` | `N_SMALL` | S8 | markdown | 351 | 2 | LOW | markdown of 351 bytes (<= 8 KiB): teaching-sized |
| `docs/4.9/OPERATIONAL.md` | `N_SMALL` | S8 | markdown | 444 | 2 | LOW | markdown of 444 bytes (<= 8 KiB): teaching-sized |
| `docs/4.9/PERSISTENCE.md` | `N_SMALL` | S8 | markdown | 350 | 2 | LOW | markdown of 350 bytes (<= 8 KiB): teaching-sized |
| `docs/4.9/PORTING.md` | `N_SMALL` | S8 | markdown | 478 | 2 | LOW | markdown of 478 bytes (<= 8 KiB): teaching-sized |
| `docs/4.9/RECOVERY.md` | `N_SMALL` | S8 | markdown | 403 | 2 | LOW | markdown of 403 bytes (<= 8 KiB): teaching-sized |
| `docs/4.9/SECURITY.md` | `N_SMALL` | S8 | markdown | 425 | 2 | LOW | markdown of 425 bytes (<= 8 KiB): teaching-sized |
| `docs/5.0/OPERATIONAL_GATE.md` | `N_SMALL` | S8 | markdown | 712 | 7 | LOW | markdown of 712 bytes (<= 8 KiB): teaching-sized |
| `docs/5.0/RELEASE.md` | `N_SMALL` | S8 | markdown | 888 | 7 | LOW | markdown of 888 bytes (<= 8 KiB): teaching-sized |
| `evidence/AUDIT_DIGEST.json` | `N_SMALL` | S6 | json | 427 | 17 | LOW | json of 427 bytes (<= 4 KiB) |
| `evidence/BASELINE_4_8.json` | `N_SMALL` | S6 | json | 1089 | 20 | LOW | json of 1089 bytes (<= 4 KiB) |
| `evidence/BASELINE_4_9.json` | `N_SMALL` | S6 | json | 803 | 18 | LOW | json of 803 bytes (<= 4 KiB) |
| `evidence/BR-470_ACCEPTANCE.json` | `N_MEDIUM` | S5 | json | 2616 | 117 | MID | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/BR-480_ACCEPTANCE.json` | `N_MEDIUM` | S5 | json | 1149 | 24 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/BR490_ACCEPTANCE.json` | `N_MEDIUM` | S5 | json | 727 | 20 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/BR500_ACCEPTANCE.json` | `N_MEDIUM` | S5 | json | 58693 | 1257 | HIGH | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/BR500_FINAL_LOCAL_QUALIFICATION.log` | `N_MEDIUM` | S6 | log | 4462 | 101 | MID | log of 4462 bytes (<= 256 KiB) |
| `evidence/BR500_SANITIZERS.log` | `N_LARGE` | S6 | log | 279262 | 342 | VERY_HIGH | log of 279262 bytes (> 256 KiB) |
| `evidence/BR500_SIZE_MEMORY.log` | `N_SMALL` | S6 | log | 3402 | 27 | LOW | log of 3402 bytes (<= 4 KiB) |
| `evidence/BRIM51_4_9.json` | `N_SMALL` | S6 | json | 412 | 18 | LOW | json of 412 bytes (<= 4 KiB) |
| `evidence/BRIM51_5_0.json` | `N_SMALL` | S6 | json | 617 | 19 | LOW | json of 617 bytes (<= 4 KiB) |
| `evidence/CORE61_4_9.json` | `N_SMALL` | S6 | json | 656 | 10 | LOW | json of 656 bytes (<= 4 KiB) |
| `evidence/CORE61_5_0.json` | `N_SMALL` | S6 | json | 861 | 11 | LOW | json of 861 bytes (<= 4 KiB) |
| `evidence/CROSS_PLATFORM_5_0.json` | `N_SMALL` | S6 | json | 2396 | 80 | MID | json of 2396 bytes (<= 4 KiB) |
| `evidence/ENVIRONMENT_5_0.json` | `N_SMALL` | S6 | json | 472 | 13 | LOW | json of 472 bytes (<= 4 KiB) |
| `evidence/MEMORY_4_9.json` | `N_SMALL` | S6 | json | 446 | 18 | LOW | json of 446 bytes (<= 4 KiB) |
| `evidence/MEMORY_5_0.json` | `N_SMALL` | S6 | json | 651 | 19 | LOW | json of 651 bytes (<= 4 KiB) |
| `evidence/PERFORMANCE_4_9.json` | `N_SMALL` | S6 | json | 2432 | 72 | MID | json of 2432 bytes (<= 4 KiB) |
| `evidence/PERFORMANCE_5_0.json` | `N_SMALL` | S6 | json | 2636 | 73 | MID | json of 2636 bytes (<= 4 KiB) |
| `evidence/RELEASE_HASHES_4_9.json` | `N_MEDIUM` | S5 | json | 1117 | 35 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/SIZE.json` | `N_SMALL` | S6 | json | 468 | 11 | LOW | json of 468 bytes (<= 4 KiB) |
| `evidence/SIZE_5_0.json` | `N_SMALL` | S6 | json | 297 | 10 | LOW | json of 297 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-01_audit.md` | `N_SMALL` | S8 | markdown | 310 | 9 | LOW | markdown of 310 bytes (<= 8 KiB): teaching-sized |
| `evidence/br500/BR-500-01_manifest.sha256` | `N_MEDIUM` | S5 | sums | 265 | 3 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/br500/BR-500-01_requirements.json` | `N_SMALL` | S6 | json | 1682 | 41 | LOW | json of 1682 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-01_tests.log` | `N_SMALL` | S6 | log | 1341 | 18 | LOW | log of 1341 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-02_audit.md` | `N_SMALL` | S8 | markdown | 324 | 9 | LOW | markdown of 324 bytes (<= 8 KiB): teaching-sized |
| `evidence/br500/BR-500-02_manifest.sha256` | `N_MEDIUM` | S5 | sums | 265 | 3 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/br500/BR-500-02_requirements.json` | `N_SMALL` | S6 | json | 2269 | 54 | LOW | json of 2269 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-02_tests.log` | `N_SMALL` | S6 | log | 2348 | 32 | LOW | log of 2348 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-03_audit.md` | `N_SMALL` | S8 | markdown | 314 | 9 | LOW | markdown of 314 bytes (<= 8 KiB): teaching-sized |
| `evidence/br500/BR-500-03_manifest.sha256` | `N_MEDIUM` | S5 | sums | 265 | 3 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/br500/BR-500-03_requirements.json` | `N_SMALL` | S6 | json | 2823 | 67 | LOW | json of 2823 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-03_tests.log` | `N_SMALL` | S6 | log | 1500 | 18 | LOW | log of 1500 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-04_audit.md` | `N_SMALL` | S8 | markdown | 315 | 9 | LOW | markdown of 315 bytes (<= 8 KiB): teaching-sized |
| `evidence/br500/BR-500-04_manifest.sha256` | `N_MEDIUM` | S5 | sums | 265 | 3 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/br500/BR-500-04_requirements.json` | `N_SMALL` | S6 | json | 3332 | 80 | MID | json of 3332 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-04_tests.log` | `N_SMALL` | S6 | log | 2163 | 30 | LOW | log of 2163 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-05_audit.md` | `N_SMALL` | S8 | markdown | 330 | 9 | LOW | markdown of 330 bytes (<= 8 KiB): teaching-sized |
| `evidence/br500/BR-500-05_manifest.sha256` | `N_MEDIUM` | S5 | sums | 265 | 3 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/br500/BR-500-05_requirements.json` | `N_SMALL` | S6 | json | 2309 | 54 | LOW | json of 2309 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-05_tests.log` | `N_MEDIUM` | S6 | log | 4354 | 86 | MID | log of 4354 bytes (<= 256 KiB) |
| `evidence/br500/BR-500-06_audit.md` | `N_SMALL` | S8 | markdown | 336 | 9 | LOW | markdown of 336 bytes (<= 8 KiB): teaching-sized |
| `evidence/br500/BR-500-06_manifest.sha256` | `N_MEDIUM` | S5 | sums | 265 | 3 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/br500/BR-500-06_requirements.json` | `N_SMALL` | S6 | json | 2899 | 67 | LOW | json of 2899 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-06_tests.log` | `N_MEDIUM` | S6 | log | 5446 | 98 | MID | log of 5446 bytes (<= 256 KiB) |
| `evidence/br500/BR-500-07_audit.md` | `N_SMALL` | S8 | markdown | 326 | 9 | LOW | markdown of 326 bytes (<= 8 KiB): teaching-sized |
| `evidence/br500/BR-500-07_manifest.sha256` | `N_MEDIUM` | S5 | sums | 265 | 3 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/br500/BR-500-07_requirements.json` | `N_SMALL` | S6 | json | 2263 | 54 | LOW | json of 2263 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-07_tests.log` | `N_SMALL` | S6 | log | 3172 | 74 | LOW | log of 3172 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-08_audit.md` | `N_SMALL` | S8 | markdown | 311 | 9 | LOW | markdown of 311 bytes (<= 8 KiB): teaching-sized |
| `evidence/br500/BR-500-08_manifest.sha256` | `N_MEDIUM` | S5 | sums | 265 | 3 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/br500/BR-500-08_requirements.json` | `N_SMALL` | S6 | json | 2774 | 67 | LOW | json of 2774 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-08_tests.log` | `N_SMALL` | S6 | log | 3051 | 64 | MID | log of 3051 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-09_audit.md` | `N_SMALL` | S8 | markdown | 347 | 9 | LOW | markdown of 347 bytes (<= 8 KiB): teaching-sized |
| `evidence/br500/BR-500-09_manifest.sha256` | `N_MEDIUM` | S5 | sums | 265 | 3 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/br500/BR-500-09_requirements.json` | `N_MEDIUM` | S6 | json | 4100 | 93 | MID | json of 4100 bytes (<= 256 KiB) |
| `evidence/br500/BR-500-09_tests.log` | `N_MEDIUM` | S6 | log | 5035 | 85 | MID | log of 5035 bytes (<= 256 KiB) |
| `evidence/br500/BR-500-10_audit.md` | `N_SMALL` | S8 | markdown | 324 | 9 | LOW | markdown of 324 bytes (<= 8 KiB): teaching-sized |
| `evidence/br500/BR-500-10_manifest.sha256` | `N_MEDIUM` | S5 | sums | 265 | 3 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/br500/BR-500-10_requirements.json` | `N_SMALL` | S6 | json | 2910 | 67 | LOW | json of 2910 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-10_tests.log` | `N_SMALL` | S6 | log | 1096 | 4 | LOW | log of 1096 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-11_audit.md` | `N_SMALL` | S8 | markdown | 335 | 9 | LOW | markdown of 335 bytes (<= 8 KiB): teaching-sized |
| `evidence/br500/BR-500-11_manifest.sha256` | `N_MEDIUM` | S5 | sums | 265 | 3 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/br500/BR-500-11_requirements.json` | `N_SMALL` | S6 | json | 2397 | 54 | LOW | json of 2397 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-11_tests.log` | `N_SMALL` | S6 | log | 2015 | 4 | LOW | log of 2015 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-12_audit.md` | `N_SMALL` | S8 | markdown | 334 | 9 | LOW | markdown of 334 bytes (<= 8 KiB): teaching-sized |
| `evidence/br500/BR-500-12_manifest.sha256` | `N_MEDIUM` | S5 | sums | 265 | 3 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/br500/BR-500-12_requirements.json` | `N_SMALL` | S6 | json | 2957 | 67 | LOW | json of 2957 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-12_tests.log` | `N_MEDIUM` | S6 | log | 55900 | 90 | VERY_HIGH | log of 55900 bytes (<= 256 KiB) |
| `evidence/br500/BR-500-13_audit.md` | `N_SMALL` | S8 | markdown | 236 | 9 | LOW | markdown of 236 bytes (<= 8 KiB): teaching-sized |
| `evidence/br500/BR-500-13_manifest.sha256` | `N_MEDIUM` | S5 | sums | 265 | 3 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/br500/BR-500-13_requirements.json` | `N_SMALL` | S6 | json | 2996 | 67 | LOW | json of 2996 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-13_tests.log` | `N_SMALL` | S6 | log | 2140 | 4 | LOW | log of 2140 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-14_audit.md` | `N_SMALL` | S8 | markdown | 228 | 9 | LOW | markdown of 228 bytes (<= 8 KiB): teaching-sized |
| `evidence/br500/BR-500-14_manifest.sha256` | `N_MEDIUM` | S5 | sums | 265 | 3 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/br500/BR-500-14_requirements.json` | `N_MEDIUM` | S6 | json | 5826 | 132 | MID | json of 5826 bytes (<= 256 KiB) |
| `evidence/br500/BR-500-14_tests.log` | `N_SMALL` | S6 | log | 226 | 3 | LOW | log of 226 bytes (<= 4 KiB) |
| `evidence/br500/BR-500-15_audit.md` | `N_SMALL` | S8 | markdown | 291 | 3 | LOW | markdown of 291 bytes (<= 8 KiB): teaching-sized |
| `evidence/br500/BR-500-15_manifest.sha256` | `N_MEDIUM` | S5 | sums | 265 | 3 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/br500/BR-500-15_requirements.json` | `N_MEDIUM` | S6 | json | 14649 | 314 | MID | json of 14649 bytes (<= 256 KiB) |
| `evidence/br500/BR-500-15_tests.log` | `N_MEDIUM` | S6 | log | 157776 | 88 | VERY_HIGH | log of 157776 bytes (<= 256 KiB) |
| `evidence/verify_br490.py` | `N_XLARGE` | S3 | python | 1547 | 26 | HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `evidence/verify_br500.py` | `N_XLARGE` | S3 | python | 1779 | 31 | HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `examples/boot.lctlc` | `N_MEDIUM` | S0 | lctlc11 | 672 | 12 | LOW | LCTLC/1.1 is the guest dialect of BOTTLE ROCKET 5.0.0 (ISA 4.1) |
| `host/br_bench.c` | `N_LARGE` | S4 | c | 4483 | 117 | HIGH | c belongs with the freestanding C core and its build system |
| `host/br_host.c` | `N_LARGE` | S4 | c | 19929 | 85 | VERY_HIGH | c belongs with the freestanding C core and its build system |
| `host/br_host.h` | `N_LARGE` | S4 | c_header | 1259 | 19 | MID | c_header belongs with the freestanding C core and its build system |
| `host/br_prod_host.c` | `N_LARGE` | S4 | c | 5397 | 7 | HIGH | c belongs with the freestanding C core and its build system |
| `host/br_prod_host.h` | `N_LARGE` | S4 | c_header | 435 | 8 | MID | c_header belongs with the freestanding C core and its build system |
| `host/br_sizes.c` | `N_LARGE` | S4 | c | 704 | 3 | LOW | c belongs with the freestanding C core and its build system |
| `host/bradmin.c` | `N_LARGE` | S4 | c | 12700 | 244 | VERY_HIGH | c belongs with the freestanding C core and its build system |
| `host/brctl.c` | `N_LARGE` | S4 | c | 2190 | 8 | HIGH | c belongs with the freestanding C core and its build system |
| `host/brsign.c` | `N_LARGE` | S4 | c | 4034 | 21 | HIGH | c belongs with the freestanding C core and its build system |
| `host/brsign.h` | `N_LARGE` | S4 | c_header | 371 | 7 | MID | c_header belongs with the freestanding C core and its build system |
| `host/brverify.c` | `N_LARGE` | S4 | c | 6266 | 20 | VERY_HIGH | c belongs with the freestanding C core and its build system |
| `include/brvm_compat_names.h` | `N_LARGE` | S4 | c_header | 3430 | 120 | MID | c_header belongs with the freestanding C core and its build system |
| `independent/brim_ref.py` | `N_XLARGE` | S3 | python | 10463 | 195 | VERY_HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `independent/differential_arithmetic.py` | `N_XLARGE` | S3 | python | 3580 | 67 | HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `independent/fuzz_campaign.py` | `N_XLARGE` | S3 | python | 2396 | 41 | HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `independent/image_attacks.py` | `N_XLARGE` | S3 | python | 3688 | 55 | HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `independent/parser_compare.py` | `N_XLARGE` | S3 | python | 2644 | 50 | MID | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `qualification/ACCEPTANCE_4_8.json` | `N_MEDIUM` | S5 | json | 1038 | 26 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `qualification/ACCEPTANCE_4_9.json` | `N_MEDIUM` | S5 | json | 489 | 14 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `qualification/ACCEPTANCE_5_0.json` | `N_MEDIUM` | S5 | json | 15814 | 608 | HIGH | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `qualification/PERFORMANCE_4_8.json` | `N_SMALL` | S6 | json | 382 | 9 | LOW | json of 382 bytes (<= 4 KiB) |
| `qualification/acceptance_gate.py` | `N_XLARGE` | S3 | python | 1828 | 36 | MID | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `qualification/br490_acceptance.py` | `N_XLARGE` | S3 | python | 1092 | 18 | MID | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `qualification/br490_brim51.py` | `N_XLARGE` | S3 | python | 1662 | 24 | MID | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `qualification/br490_contract_checks.py` | `N_XLARGE` | S3 | python | 3958 | 56 | HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `qualification/br490_core61.py` | `N_XLARGE` | S3 | python | 1499 | 16 | MID | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `qualification/br490_memory.py` | `N_XLARGE` | S3 | python | 1561 | 21 | MID | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `qualification/br490_performance.py` | `N_XLARGE` | S3 | python | 3569 | 43 | MID | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `qualification/br490_release_manifest.py` | `N_XLARGE` | S3 | python | 2044 | 28 | MID | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `qualification/br500_acceptance.py` | `N_XLARGE` | S3 | python | 2683 | 43 | HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `qualification/br500_environment.py` | `N_XLARGE` | S3 | python | 1013 | 21 | MID | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `qualification/br500_evidence.py` | `N_XLARGE` | S3 | python | 5056 | 65 | HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `qualification/br500_release_bundle.py` | `N_XLARGE` | S3 | python | 5542 | 71 | HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `qualification/cross_platform_repro.py` | `N_XLARGE` | S3 | python | 3999 | 55 | HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `qualification/reseal_after_patch.py` | `N_XLARGE` | S3 | python | 8395 | 109 | HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `qualification/run_br490_evidence.py` | `N_XLARGE` | S3 | python | 1168 | 22 | MID | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `qualification/security_review_check.py` | `N_XLARGE` | S3 | python | 770 | 13 | MID | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `release/IMMUTABLE_RELEASE_MANIFEST.json` | `N_MEDIUM` | S5 | json | 2397 | 64 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `release/IMMUTABLE_RELEASE_MANIFEST.sig` | `N_MEDIUM` | S5 | signature | 64 | 0 | LOW | signature named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `release/RELEASE_SIGNING_PUBLIC.pem` | `N_MEDIUM` | S5 | key | 113 | 3 | LOW | key named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `release/artifacts/BOTTLE_ROCKET_5.0.0_COLUMNED_LCTL_VM_QUALIFICATION_CANDIDATE.brimg` | `N_XLARGE` | S2 | image | 272 | 0 | LOW | bulk cargo (image of 272 bytes) needs the roomiest, hosted node |
| `release/artifacts/BOTTLE_ROCKET_5.0.0_COLUMNED_LCTL_VM_QUALIFICATION_CANDIDATE.brir` | `N_SMALL` | S8 | text | 547 | 8 | LOW | text of 547 bytes (<= 8 KiB): teaching-sized |
| `release/artifacts/BOTTLE_ROCKET_5.0.0_COLUMNED_LCTL_VM_QUALIFICATION_CANDIDATE.brsb` | `N_XLARGE` | S2 | image | 688 | 0 | LOW | bulk cargo (image of 688 bytes) needs the roomiest, hosted node |
| `release/bin/brctl` | `N_XLARGE` | S2 | binary | 121800 | 0 | LOW | bulk cargo (binary of 121800 bytes) needs the roomiest, hosted node |
| `release/bin/brverify` | `N_XLARGE` | S2 | binary | 21232 | 0 | LOW | bulk cargo (binary of 21232 bytes) needs the roomiest, hosted node |
| `release/bin/brvm-core.o` | `N_XLARGE` | S2 | binary | 74136 | 0 | LOW | bulk cargo (binary of 74136 bytes) needs the roomiest, hosted node |
| `release/bin/brvm-core61.stripped.o` | `N_XLARGE` | S2 | binary | 48264 | 0 | LOW | bulk cargo (binary of 48264 bytes) needs the roomiest, hosted node |
| `replay/EXPECTED_4_9.json` | `N_SMALL` | S6 | json | 952 | 16 | LOW | json of 952 bytes (<= 4 KiB) |
| `replay/README.md` | `N_SMALL` | S8 | markdown | 578 | 3 | LOW | markdown of 578 bytes (<= 8 KiB): teaching-sized |
| `replay/run.py` | `N_XLARGE` | S3 | python | 2532 | 28 | MID | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `security/ATTACK_SURFACE_4_8.md` | `N_SMALL` | S8 | markdown | 2250 | 18 | LOW | markdown of 2250 bytes (<= 8 KiB): teaching-sized |
| `security/QUALIFICATION_LIMITATIONS_4_8.md` | `N_SMALL` | S8 | markdown | 1232 | 14 | LOW | markdown of 1232 bytes (<= 8 KiB): teaching-sized |
| `security/SECURITY_REVIEW_4_8.md` | `N_SMALL` | S8 | markdown | 4207 | 32 | MID | markdown of 4207 bytes (<= 8 KiB): teaching-sized |
| `security/THREAT_MODEL_4_8.md` | `N_SMALL` | S8 | markdown | 2424 | 30 | LOW | markdown of 2424 bytes (<= 8 KiB): teaching-sized |
| `spec/BR480_QUALIFICATION.json` | `N_SMALL` | S6 | json | 814 | 21 | LOW | json of 814 bytes (<= 4 KiB) |
| `spec/BR_SPEC.json` | `N_SMALL` | S6 | json | 1780 | 1 | MID | json of 1780 bytes (<= 4 KiB) |
| `spec/DEVICE_IO_4_7.md` | `N_SMALL` | S8 | markdown | 3343 | 33 | LOW | markdown of 3343 bytes (<= 8 KiB): teaching-sized |
| `spec/LCTLC_1_1.json` | `N_SMALL` | S6 | json | 669 | 1 | MID | json of 669 bytes (<= 4 KiB) |
| `spec/PERSISTENCE_4_5.md` | `N_SMALL` | S8 | markdown | 1831 | 29 | MID | markdown of 1831 bytes (<= 8 KiB): teaching-sized |
| `spec/PROFILE.md` | `N_SMALL` | S8 | markdown | 895 | 7 | LOW | markdown of 895 bytes (<= 8 KiB): teaching-sized |
| `spec/RELEASE_FREEZE_4_9.json` | `N_MEDIUM` | S5 | json | 1535 | 61 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `spec/RELEASE_FREEZE_5_0.json` | `N_MEDIUM` | S5 | json | 773 | 24 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `spec/RELEASE_PROFILES_4_9.json` | `N_MEDIUM` | S5 | json | 2063 | 66 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `spec/WIDE_STATE_4_6.md` | `N_SMALL` | S8 | markdown | 1795 | 23 | LOW | markdown of 1795 bytes (<= 8 KiB): teaching-sized |
| `src/CORE.lctlc` | `N_MEDIUM` | S0 | lctlc11 | 406 | 8 | LOW | LCTLC/1.1 is the guest dialect of BOTTLE ROCKET 5.0.0 (ISA 4.1) |
| `src/brlctlc.c` | `N_LARGE` | S4 | c | 20283 | 25 | VERY_HIGH | c belongs with the freestanding C core and its build system |
| `src/brlctlc.h` | `N_LARGE` | S4 | c_header | 492 | 10 | MID | c_header belongs with the freestanding C core and its build system |
| `src/brtrust.c` | `N_LARGE` | S4 | c | 6953 | 10 | HIGH | c belongs with the freestanding C core and its build system |
| `src/brtrust.h` | `N_LARGE` | S4 | c_header | 592 | 7 | LOW | c_header belongs with the freestanding C core and its build system |
| `src/brvm.c` | `N_LARGE` | S4 | c | 56396 | 83 | VERY_HIGH | c belongs with the freestanding C core and its build system |
| `src/brvm.h` | `N_LARGE` | S4 | c_header | 9661 | 68 | MID | c_header belongs with the freestanding C core and its build system |
| `tests/apdu_corpus/case_00.bin` | `N_XLARGE` | S2 | binary | 0 | 0 | LOW | bulk cargo (binary of 0 bytes) needs the roomiest, hosted node |
| `tests/apdu_corpus/case_01.bin` | `N_XLARGE` | S2 | binary | 4 | 1 | LOW | bulk cargo (binary of 4 bytes) needs the roomiest, hosted node |
| `tests/apdu_corpus/case_02.bin` | `N_XLARGE` | S2 | binary | 8 | 0 | LOW | bulk cargo (binary of 8 bytes) needs the roomiest, hosted node |
| `tests/apdu_corpus/case_03.bin` | `N_XLARGE` | S2 | binary | 12 | 0 | LOW | bulk cargo (binary of 12 bytes) needs the roomiest, hosted node |
| `tests/apdu_corpus/case_04.bin` | `N_XLARGE` | S2 | binary | 16 | 0 | LOW | bulk cargo (binary of 16 bytes) needs the roomiest, hosted node |
| `tests/apdu_corpus/case_05.bin` | `N_XLARGE` | S2 | binary | 20 | 0 | LOW | bulk cargo (binary of 20 bytes) needs the roomiest, hosted node |
| `tests/apdu_corpus/case_06.bin` | `N_XLARGE` | S2 | binary | 24 | 0 | LOW | bulk cargo (binary of 24 bytes) needs the roomiest, hosted node |
| `tests/apdu_corpus/case_07.bin` | `N_XLARGE` | S2 | binary | 28 | 0 | LOW | bulk cargo (binary of 28 bytes) needs the roomiest, hosted node |
| `tests/apdu_corpus/case_08.bin` | `N_XLARGE` | S2 | binary | 32 | 0 | LOW | bulk cargo (binary of 32 bytes) needs the roomiest, hosted node |
| `tests/apdu_corpus/case_09.bin` | `N_XLARGE` | S2 | binary | 36 | 0 | LOW | bulk cargo (binary of 36 bytes) needs the roomiest, hosted node |
| `tests/apdu_corpus/case_10.bin` | `N_XLARGE` | S2 | binary | 40 | 0 | LOW | bulk cargo (binary of 40 bytes) needs the roomiest, hosted node |
| `tests/apdu_corpus/case_11.bin` | `N_XLARGE` | S2 | binary | 44 | 0 | LOW | bulk cargo (binary of 44 bytes) needs the roomiest, hosted node |
| `tests/apdu_corpus/case_12.bin` | `N_XLARGE` | S2 | binary | 48 | 0 | LOW | bulk cargo (binary of 48 bytes) needs the roomiest, hosted node |
| `tests/apdu_corpus/case_13.bin` | `N_XLARGE` | S2 | binary | 52 | 0 | LOW | bulk cargo (binary of 52 bytes) needs the roomiest, hosted node |
| `tests/apdu_corpus/case_14.bin` | `N_XLARGE` | S2 | binary | 56 | 0 | LOW | bulk cargo (binary of 56 bytes) needs the roomiest, hosted node |
| `tests/apdu_corpus/case_15.bin` | `N_XLARGE` | S2 | binary | 60 | 0 | LOW | bulk cargo (binary of 60 bytes) needs the roomiest, hosted node |
| `tests/br480_fuzz.c` | `N_LARGE` | S4 | c | 3516 | 23 | HIGH | c belongs with the freestanding C core and its build system |
| `tests/br480_math_driver.c` | `N_LARGE` | S4 | c | 1569 | 10 | HIGH | c belongs with the freestanding C core and its build system |
| `tests/br480_opcode_edges.c` | `N_LARGE` | S4 | c | 3048 | 22 | MID | c belongs with the freestanding C core and its build system |
| `tests/br480_property_conformance.c` | `N_LARGE` | S4 | c | 2372 | 17 | MID | c belongs with the freestanding C core and its build system |
| `tests/br480_soak.c` | `N_LARGE` | S4 | c | 1990 | 20 | HIGH | c belongs with the freestanding C core and its build system |
| `tests/constant_fold.sh` | `N_SMALL` | S7 | shell | 702 | 18 | LOW | shell launcher, complexity LOW (score 1.8) |
| `tests/device_boundary_audit.sh` | `N_MEDIUM` | S7 | shell | 1000 | 16 | MID | shell launcher, complexity MID (score 10.6) |
| `tests/device_io_conformance.c` | `N_LARGE` | S4 | c | 10973 | 27 | HIGH | c belongs with the freestanding C core and its build system |
| `tests/isa_abi_conformance.c` | `N_LARGE` | S4 | c | 10328 | 73 | HIGH | c belongs with the freestanding C core and its build system |
| `tests/semantic_tests.sh` | `N_LARGE` | S7 | shell | 10257 | 242 | HIGH | shell launcher, complexity HIGH (score 66.2) |
| `tests/spec_sync.py` | `N_XLARGE` | S3 | python | 3025 | 33 | MID | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `tests/test_main.c` | `N_LARGE` | S4 | c | 279 | 3 | MID | c belongs with the freestanding C core and its build system |
| `tests/wide_state_conformance.c` | `N_LARGE` | S4 | c | 8340 | 32 | MID | c belongs with the freestanding C core and its build system |
| `tools/provenance.py` | `N_XLARGE` | S3 | python | 1382 | 27 | MID | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `workflows/5.0/01_BR-500-01_native_source_authority_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S5 | markdown | 7941 | 107 | MID | markdown named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `workflows/5.0/02_BR-500-02_native_compiler_PROMPT_AND_WORKFLOW.md` | `N_SMALL` | S8 | markdown | 8138 | 108 | MID | markdown of 8138 bytes (<= 8 KiB): teaching-sized |
| `workflows/5.0/03_BR-500-03_native_verifier_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8619 | 113 | MID | markdown of 8619 bytes (<= 128 KiB) |
| `workflows/5.0/04_BR-500-04_production_vm_core_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8874 | 116 | MID | markdown of 8874 bytes (<= 128 KiB) |
| `workflows/5.0/05_BR-500-05_production_loader_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8317 | 110 | MID | markdown of 8317 bytes (<= 128 KiB) |
| `workflows/5.0/06_BR-500-06_production_persistence_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8402 | 107 | MID | markdown of 8402 bytes (<= 128 KiB) |
| `workflows/5.0/07_BR-500-07_production_devices_PROMPT_AND_WORKFLOW.md` | `N_SMALL` | S8 | markdown | 8155 | 108 | MID | markdown of 8155 bytes (<= 8 KiB): teaching-sized |
| `workflows/5.0/08_BR-500-08_production_memory_architecture_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8703 | 113 | MID | markdown of 8703 bytes (<= 128 KiB) |
| `workflows/5.0/09_BR-500-09_security_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9222 | 119 | MID | markdown of 9222 bytes (<= 128 KiB) |
| `workflows/5.0/10_BR-500-10_operational_evidence_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8506 | 113 | MID | markdown of 8506 bytes (<= 128 KiB) |
| `workflows/5.0/11_BR-500-11_reproducibility_PROMPT_AND_WORKFLOW.md` | `N_SMALL` | S8 | markdown | 8174 | 109 | MID | markdown of 8174 bytes (<= 8 KiB): teaching-sized |
| `workflows/5.0/12_BR-500-12_reliability_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8532 | 113 | MID | markdown of 8532 bytes (<= 128 KiB) |
| `workflows/5.0/13_BR-500-13_performance_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8407 | 113 | MID | markdown of 8407 bytes (<= 128 KiB) |
| `workflows/5.0/14_BR-500-14_release_engineering_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S5 | markdown | 9860 | 128 | MID | markdown named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `workflows/5.0/15_BR-500-15_5_0_0_final_operational_gate_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 14369 | 170 | MID | markdown of 14369 bytes (<= 128 KiB) |
| `workflows/5.0/README.md` | `N_SMALL` | S8 | markdown | 1660 | 23 | LOW | markdown of 1660 bytes (<= 8 KiB): teaching-sized |

**Portable storage.** 5 script(s) are stored under an alias (`cargo/_alias/<sha256(path)[:16]><ext>`) because their original path cannot exist on every host (a path that differs only by case from another, or a delivered path over 140 characters -- `Unikernel_Containership/berths/vm_medium/<slot>/cargo/<path>` -- which a Windows extraction would refuse); their identity, bytes, node and rule are unchanged. First few:

* `deploy/BOTTLE_ROCKET_4.7.0_COLUMNED_LCTL_VIRTUAL_DEVICE_IO_SERVICE_ARCHITECTURE.brimg` -> `_alias/d6b0679eaf5c51f9.brimg` -- the delivered path would be 146 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `deploy/BOTTLE_ROCKET_4.7.0_COLUMNED_LCTL_VIRTUAL_DEVICE_IO_SERVICE_ARCHITECTURE.brsb` -> `_alias/6936f1707a70b4db.brsb` -- the delivered path would be 145 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `deploy/BOTTLE_ROCKET_4.7.0_COLUMNED_LCTL_VIRTUAL_DEVICE_IO_SERVICE_ARCHITECTURE.provenance.json` -> `_alias/eb48e9b5ae06190c.json` -- the delivered path would be 152 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `release/artifacts/BOTTLE_ROCKET_5.0.0_COLUMNED_LCTL_VM_QUALIFICATION_CANDIDATE.brimg` -> `_alias/3e918630ffe464b0.brimg` -- the delivered path would be 145 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `release/artifacts/BOTTLE_ROCKET_5.0.0_COLUMNED_LCTL_VM_QUALIFICATION_CANDIDATE.brsb` -> `_alias/28d1059d47a46a16.brsb` -- the delivered path would be 144 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
