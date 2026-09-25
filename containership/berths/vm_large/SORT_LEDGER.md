# vm_large -- sort ledger

Berth `vm_large` (vm), UC-2.1.3. Source: `Large.zip` (zip, 94b612d849d9990906e8090ae6576cf187a2154349acd2c44a821b43a4da7574). 893 scripts sorted by policy 1.0.1 (rules S0-S9, first match wins; see `reports/SORT_POLICY.md`).

| node | scripts | bytes | rules | kinds |
|---|---:|---:|---|---|
| `N_SMALL` (DF_Small) | 438 | 447377 | S6:271, S7:4, S8:163 | markdown:162, json:156, log:113, shell:4, jsonl:2, text:1 |
| `N_MEDIUM` (DF_Medium) | 359 | 3387916 | S5:177, S6:109, S8:73 | sums:135, json:92, markdown:81, log:49, key:2 |
| `N_LARGE` (DF_Large) | 41 | 235863 | S0:5, S4:36 | c:26, c_header:8, lctlc12:5, make:2 |
| `N_XLARGE` (DF_Xtra_Large) | 55 | 170476 | S2:40, S3:15 | image:32, python:15, binary:8 |

| script | node | rule | kind | bytes | lines | band | why |
|---|---|---|---|---:|---:|---|---|
| `AUDIT_ERRATA.md` | `N_SMALL` | S8 | markdown | 3693 | 51 | MID | markdown of 3693 bytes (<= 8 KiB): teaching-sized |
| `Makefile` | `N_LARGE` | S4 | make | 3539 | 43 | LOW | make belongs with the freestanding C core and its build system |
| `README.md` | `N_SMALL` | S8 | markdown | 4308 | 60 | MID | markdown of 4308 bytes (<= 8 KiB): teaching-sized |
| `RELEASE_CONTENTS.sha256` | `N_MEDIUM` | S5 | sums | 104897 | 892 | HIGH | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `adapters/br_adapters.h` | `N_LARGE` | S4 | c_header | 1092 | 11 | MID | c_header belongs with the freestanding C core and its build system |
| `adapters/br_file_adapter.c` | `N_LARGE` | S4 | c | 4293 | 67 | HIGH | c belongs with the freestanding C core and its build system |
| `adapters/br_memory_adapter.c` | `N_LARGE` | S4 | c | 2866 | 44 | HIGH | c belongs with the freestanding C core and its build system |
| `baseline/4.4.0/BASELINE.sha256` | `N_MEDIUM` | S5 | sums | 136 | 1 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `baseline/4.4.0/BOOT.lctlc` | `N_LARGE` | S0 | lctlc12 | 761 | 12 | LOW | LCTLC/1.2 (columned-lctl/4.3) is the guest dialect of BOTTLE ROCKET 4.7.0 (BR/1.1) |
| `baseline/4.4.0/BOTTLE_ROCKET_SIM_CORE_4.3.0.brir.json` | `N_SMALL` | S6 | json | 1791 | 1 | LOW | json of 1791 bytes (<= 4 KiB) |
| `baseline/4.4.0/BOTTLE_ROCKET_SIM_CORE_4.3.0.provenance.json` | `N_MEDIUM` | S5 | json | 650 | 1 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `baseline/4.5.0/ARCHIVE.sha256` | `N_MEDIUM` | S5 | sums | 149 | 1 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `baseline/4.5.0/br_adapters.h` | `N_LARGE` | S4 | c_header | 1092 | 11 | MID | c_header belongs with the freestanding C core and its build system |
| `baseline/4.5.0/br_bench.c` | `N_LARGE` | S4 | c | 1710 | 14 | MID | c belongs with the freestanding C core and its build system |
| `baseline/4.5.0/br_memory_adapter.c` | `N_LARGE` | S4 | c | 3487 | 23 | HIGH | c belongs with the freestanding C core and its build system |
| `baseline/4.5.0/br_sizes.c` | `N_LARGE` | S4 | c | 1811 | 26 | MID | c belongs with the freestanding C core and its build system |
| `baseline/4.5.0/brvm.c` | `N_LARGE` | S4 | c | 33768 | 79 | VERY_HIGH | c belongs with the freestanding C core and its build system |
| `baseline/4.5.0/brvm.h` | `N_LARGE` | S4 | c_header | 6601 | 38 | MID | c_header belongs with the freestanding C core and its build system |
| `baseline/4.6.0/Makefile` | `N_LARGE` | S4 | make | 2617 | 33 | LOW | make belongs with the freestanding C core and its build system |
| `baseline/4.6.0/README.md` | `N_SMALL` | S8 | markdown | 1869 | 25 | MID | markdown of 1869 bytes (<= 8 KiB): teaching-sized |
| `baseline/4.6.0/adapters/br_adapters.h` | `N_LARGE` | S4 | c_header | 1092 | 11 | MID | c_header belongs with the freestanding C core and its build system |
| `baseline/4.6.0/adapters/br_file_adapter.c` | `N_LARGE` | S4 | c | 4439 | 55 | HIGH | c belongs with the freestanding C core and its build system |
| `baseline/4.6.0/adapters/br_memory_adapter.c` | `N_LARGE` | S4 | c | 2955 | 38 | HIGH | c belongs with the freestanding C core and its build system |
| `baseline/4.6.0/spec/BR_SPEC.json` | `N_SMALL` | S6 | json | 792 | 1 | MID | json of 792 bytes (<= 4 KiB) |
| `baseline/4.6.0/spec/LCTL_SPEC.json` | `N_SMALL` | S6 | json | 146 | 1 | LOW | json of 146 bytes (<= 4 KiB) |
| `baseline/4.6.0/spec/PERSIST_SPEC.json` | `N_SMALL` | S6 | json | 322 | 1 | LOW | json of 322 bytes (<= 4 KiB) |
| `baseline/4.6.0/spec/PROFILE.md` | `N_SMALL` | S8 | markdown | 12 | 2 | LOW | markdown of 12 bytes (<= 8 KiB): teaching-sized |
| `baseline/4.6.0/spec/TRUST_SPEC.json` | `N_SMALL` | S6 | json | 575 | 1 | LOW | json of 575 bytes (<= 4 KiB) |
| `baseline/4.6.0/spec/WIDE_STATE_SPEC.json` | `N_SMALL` | S6 | json | 1239 | 15 | LOW | json of 1239 bytes (<= 4 KiB) |
| `baseline/4.6.0/src/BOOT.lctlc` | `N_LARGE` | S0 | lctlc12 | 264 | 6 | LOW | LCTLC/1.2 (columned-lctl/4.3) is the guest dialect of BOTTLE ROCKET 4.7.0 (BR/1.1) |
| `baseline/4.6.0/src/CORE.lctlc` | `N_LARGE` | S0 | lctlc12 | 92 | 4 | LOW | LCTLC/1.2 (columned-lctl/4.3) is the guest dialect of BOTTLE ROCKET 4.7.0 (BR/1.1) |
| `baseline/4.6.0/src/brtrust.c` | `N_LARGE` | S4 | c | 7873 | 46 | HIGH | c belongs with the freestanding C core and its build system |
| `baseline/4.6.0/src/brtrust.h` | `N_LARGE` | S4 | c_header | 1577 | 9 | LOW | c_header belongs with the freestanding C core and its build system |
| `baseline/4.6.0/src/brvm.c` | `N_LARGE` | S4 | c | 34868 | 139 | VERY_HIGH | c belongs with the freestanding C core and its build system |
| `baseline/4.6.0/src/brvm.h` | `N_LARGE` | S4 | c_header | 7150 | 39 | MID | c_header belongs with the freestanding C core and its build system |
| `deploy/BOTTLE_ROCKET_SECURE_BUNDLE_4.4.0.json` | `N_SMALL` | S6 | json | 438 | 1 | LOW | json of 438 bytes (<= 4 KiB) |
| `deploy/BOTTLE_ROCKET_SIM_CORE_4.0.1.brimg` | `N_XLARGE` | S2 | image | 176 | 0 | LOW | bulk cargo (image of 176 bytes) needs the roomiest, hosted node |
| `deploy/BOTTLE_ROCKET_SIM_CORE_4.1.0.brimg` | `N_XLARGE` | S2 | image | 176 | 0 | LOW | bulk cargo (image of 176 bytes) needs the roomiest, hosted node |
| `deploy/BOTTLE_ROCKET_SIM_CORE_4.2.0.brimg` | `N_XLARGE` | S2 | image | 176 | 0 | LOW | bulk cargo (image of 176 bytes) needs the roomiest, hosted node |
| `deploy/BOTTLE_ROCKET_SIM_CORE_4.2.0.brir.json` | `N_SMALL` | S6 | json | 1788 | 1 | LOW | json of 1788 bytes (<= 4 KiB) |
| `deploy/BOTTLE_ROCKET_SIM_CORE_4.2.0.provenance.json` | `N_MEDIUM` | S5 | json | 647 | 1 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `deploy/BOTTLE_ROCKET_SIM_CORE_4.3.0.brimg` | `N_XLARGE` | S2 | image | 176 | 0 | LOW | bulk cargo (image of 176 bytes) needs the roomiest, hosted node |
| `deploy/BOTTLE_ROCKET_SIM_CORE_4.3.0.brir.json` | `N_SMALL` | S6 | json | 1791 | 1 | LOW | json of 1791 bytes (<= 4 KiB) |
| `deploy/BOTTLE_ROCKET_SIM_CORE_4.3.0.provenance.json` | `N_MEDIUM` | S5 | json | 650 | 1 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `deploy/BOTTLE_ROCKET_SIM_CORE_4.4.0_SIGNED.brimg` | `N_XLARGE` | S2 | image | 240 | 0 | LOW | bulk cargo (image of 240 bytes) needs the roomiest, hosted node |
| `deploy/BOTTLE_ROCKET_SIM_CORE_4.4.0_SIGNED.brmf` | `N_XLARGE` | S2 | image | 216 | 0 | LOW | bulk cargo (image of 216 bytes) needs the roomiest, hosted node |
| `deploy/BOTTLE_ROCKET_SIM_CORE_4.5.0.brimg` | `N_XLARGE` | S2 | image | 112 | 0 | LOW | bulk cargo (image of 112 bytes) needs the roomiest, hosted node |
| `deploy/BOTTLE_ROCKET_SIM_CORE_4.5.0.brir.json` | `N_SMALL` | S6 | json | 791 | 1 | LOW | json of 791 bytes (<= 4 KiB) |
| `deploy/BOTTLE_ROCKET_SIM_CORE_4.5.0.provenance.json` | `N_MEDIUM` | S5 | json | 650 | 1 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `deploy/BOTTLE_ROCKET_SIM_CORE_4.6.0.brimg` | `N_XLARGE` | S2 | image | 112 | 0 | LOW | bulk cargo (image of 112 bytes) needs the roomiest, hosted node |
| `deploy/BOTTLE_ROCKET_SIM_CORE_4.6.0.brir.json` | `N_SMALL` | S6 | json | 791 | 1 | LOW | json of 791 bytes (<= 4 KiB) |
| `deploy/BOTTLE_ROCKET_SIM_CORE_4.6.0.provenance.json` | `N_MEDIUM` | S5 | json | 650 | 1 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `deploy/BOTTLE_ROCKET_SIM_CORE_4.7.0.brimg` | `N_XLARGE` | S2 | image | 112 | 0 | LOW | bulk cargo (image of 112 bytes) needs the roomiest, hosted node |
| `deploy/BOTTLE_ROCKET_SIM_CORE_4.7.0.brir.json` | `N_SMALL` | S6 | json | 791 | 1 | LOW | json of 791 bytes (<= 4 KiB) |
| `deploy/BOTTLE_ROCKET_SIM_CORE_4.7.0.provenance.json` | `N_MEDIUM` | S5 | json | 650 | 1 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `deploy/BOTTLE_ROCKET_TRUST_POLICY_4.4.0.brtp` | `N_XLARGE` | S2 | image | 352 | 0 | LOW | bulk cargo (image of 352 bytes) needs the roomiest, hosted node |
| `docs/4.0.1/BASELINE_4.0.0_RUN.log` | `N_SMALL` | S6 | log | 3227 | 46 | LOW | log of 3227 bytes (<= 4 KiB) |
| `docs/4.0.1/CHANGELOG_4.0.1.md` | `N_SMALL` | S8 | markdown | 2256 | 20 | MID | markdown of 2256 bytes (<= 8 KiB): teaching-sized |
| `docs/4.0.1/REPRODUCE_4.0.1.md` | `N_SMALL` | S8 | markdown | 870 | 31 | LOW | markdown of 870 bytes (<= 8 KiB): teaching-sized |
| `docs/4.1.0/BASELINE_AUTHORITY.json` | `N_MEDIUM` | S5 | json | 494 | 1 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `docs/4.1.0/BASELINE_BEFORE_4.2.0.log` | `N_MEDIUM` | S6 | log | 5565 | 73 | MID | log of 5565 bytes (<= 256 KiB) |
| `docs/4.1.0/README_4.1.0.md` | `N_SMALL` | S8 | markdown | 2743 | 32 | LOW | markdown of 2743 bytes (<= 8 KiB): teaching-sized |
| `docs/ARCHITECTURE_4.1.0.md` | `N_SMALL` | S8 | markdown | 1436 | 11 | LOW | markdown of 1436 bytes (<= 8 KiB): teaching-sized |
| `docs/ARCHITECTURE_4.2.0.md` | `N_SMALL` | S8 | markdown | 2170 | 19 | LOW | markdown of 2170 bytes (<= 8 KiB): teaching-sized |
| `docs/ARCHITECTURE_4.4.0.md` | `N_SMALL` | S8 | markdown | 4803 | 40 | MID | markdown of 4803 bytes (<= 8 KiB): teaching-sized |
| `docs/ARCHITECTURE_4.5.0.md` | `N_SMALL` | S8 | markdown | 2021 | 26 | LOW | markdown of 2021 bytes (<= 8 KiB): teaching-sized |
| `docs/BASELINE_4.0.1_RUN.log` | `N_SMALL` | S6 | log | 3825 | 42 | LOW | log of 3825 bytes (<= 4 KiB) |
| `docs/BASELINE_4.3.0_ARCHIVE.sha256` | `N_MEDIUM` | S5 | sums | 137 | 1 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `docs/CHANGELOG_4.1.0.md` | `N_SMALL` | S8 | markdown | 2441 | 22 | LOW | markdown of 2441 bytes (<= 8 KiB): teaching-sized |
| `docs/CHANGELOG_4.2.0.md` | `N_SMALL` | S8 | markdown | 1060 | 13 | MID | markdown of 1060 bytes (<= 8 KiB): teaching-sized |
| `docs/CHANGELOG_4.3.0.md` | `N_SMALL` | S8 | markdown | 748 | 5 | LOW | markdown of 748 bytes (<= 8 KiB): teaching-sized |
| `docs/CHANGELOG_4.4.0.md` | `N_SMALL` | S8 | markdown | 1287 | 13 | LOW | markdown of 1287 bytes (<= 8 KiB): teaching-sized |
| `docs/CHANGELOG_4.5.0.md` | `N_SMALL` | S8 | markdown | 1202 | 14 | LOW | markdown of 1202 bytes (<= 8 KiB): teaching-sized |
| `docs/CHANGELOG_4.6.0.md` | `N_SMALL` | S8 | markdown | 745 | 10 | LOW | markdown of 745 bytes (<= 8 KiB): teaching-sized |
| `docs/CHANGELOG_4.7.0.md` | `N_SMALL` | S8 | markdown | 1135 | 14 | LOW | markdown of 1135 bytes (<= 8 KiB): teaching-sized |
| `docs/INVARIANTS_4.3.0.md` | `N_SMALL` | S8 | markdown | 756 | 9 | LOW | markdown of 756 bytes (<= 8 KiB): teaching-sized |
| `docs/INVARIANTS_4.4.0.md` | `N_SMALL` | S8 | markdown | 2054 | 17 | LOW | markdown of 2054 bytes (<= 8 KiB): teaching-sized |
| `docs/INVARIANTS_4.5.0.md` | `N_SMALL` | S8 | markdown | 1149 | 14 | LOW | markdown of 1149 bytes (<= 8 KiB): teaching-sized |
| `docs/ISA_ABI_4.3.md` | `N_SMALL` | S8 | markdown | 3358 | 28 | MID | markdown of 3358 bytes (<= 8 KiB): teaching-sized |
| `docs/KEY_CEREMONY_4.4.0.md` | `N_SMALL` | S8 | markdown | 2222 | 23 | MID | markdown of 2222 bytes (<= 8 KiB): teaching-sized |
| `docs/PERFORMANCE_4.3.0.md` | `N_SMALL` | S8 | markdown | 959 | 12 | LOW | markdown of 959 bytes (<= 8 KiB): teaching-sized |
| `docs/PERFORMANCE_4.4.0.md` | `N_SMALL` | S8 | markdown | 897 | 5 | LOW | markdown of 897 bytes (<= 8 KiB): teaching-sized |
| `docs/QUORUM_4.2.0_APPLICATION_REPORT.md` | `N_SMALL` | S8 | markdown | 785 | 5 | LOW | markdown of 785 bytes (<= 8 KiB): teaching-sized |
| `docs/QUORUM_4.4.0_APPLICATION_REPORT.md` | `N_SMALL` | S8 | markdown | 3066 | 43 | MID | markdown of 3066 bytes (<= 8 KiB): teaching-sized |
| `docs/QUORUM_4.5.0_APPLICATION_REPORT.md` | `N_SMALL` | S8 | markdown | 4151 | 56 | LOW | markdown of 4151 bytes (<= 8 KiB): teaching-sized |
| `docs/QUORUM_APPLICATION_REPORT_4.6.0.md` | `N_SMALL` | S8 | markdown | 688 | 5 | LOW | markdown of 688 bytes (<= 8 KiB): teaching-sized |
| `docs/QUORUM_APPLICATION_REPORT_4.7.0.md` | `N_SMALL` | S8 | markdown | 2698 | 52 | LOW | markdown of 2698 bytes (<= 8 KiB): teaching-sized |
| `docs/REPRODUCE.md` | `N_SMALL` | S8 | markdown | 173 | 5 | LOW | markdown of 173 bytes (<= 8 KiB): teaching-sized |
| `docs/REPRODUCE_4.1.0.md` | `N_SMALL` | S8 | markdown | 1227 | 28 | LOW | markdown of 1227 bytes (<= 8 KiB): teaching-sized |
| `docs/REPRODUCE_4.2.0.md` | `N_SMALL` | S8 | markdown | 1111 | 25 | LOW | markdown of 1111 bytes (<= 8 KiB): teaching-sized |
| `docs/REPRODUCE_4.3.0.md` | `N_SMALL` | S8 | markdown | 605 | 13 | LOW | markdown of 605 bytes (<= 8 KiB): teaching-sized |
| `docs/REPRODUCE_4.4.0.md` | `N_SMALL` | S8 | markdown | 765 | 16 | LOW | markdown of 765 bytes (<= 8 KiB): teaching-sized |
| `docs/REPRODUCE_4.5.0.md` | `N_SMALL` | S8 | markdown | 1080 | 17 | LOW | markdown of 1080 bytes (<= 8 KiB): teaching-sized |
| `docs/REPRODUCE_4.6.0.md` | `N_SMALL` | S8 | markdown | 586 | 22 | LOW | markdown of 586 bytes (<= 8 KiB): teaching-sized |
| `docs/REPRODUCE_4.7.0.md` | `N_SMALL` | S8 | markdown | 808 | 27 | LOW | markdown of 808 bytes (<= 8 KiB): teaching-sized |
| `docs/SIZE_BOUNDARY.md` | `N_SMALL` | S8 | markdown | 393 | 3 | LOW | markdown of 393 bytes (<= 8 KiB): teaching-sized |
| `docs/SIZE_BOUNDARY_4.4.0.md` | `N_SMALL` | S8 | markdown | 599 | 5 | LOW | markdown of 599 bytes (<= 8 KiB): teaching-sized |
| `docs/SIZE_BOUNDARY_4.5.0.md` | `N_SMALL` | S8 | markdown | 617 | 12 | LOW | markdown of 617 bytes (<= 8 KiB): teaching-sized |
| `docs/WORKFLOW_APPLIED/01_BR-410-01_create_brvm_core_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9925 | 128 | MID | markdown of 9925 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED/02_BR-410-02_remove_host_assumptions_from_the_core_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9487 | 119 | MID | markdown of 9487 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED/03_BR-410-03_define_host_abstraction_layer_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 11232 | 146 | MID | markdown of 11232 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED/04_BR-410-04_core_lifecycle_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 11622 | 138 | MID | markdown of 11622 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED/05_BR-410-05_execution_context_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9773 | 122 | MID | markdown of 9773 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED/06_BR-410-06_error_model_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9803 | 128 | MID | markdown of 9803 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED/07_BR-410-07_host_adapters_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9080 | 116 | MID | markdown of 9080 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED/08_BR-410-08_sandbox_boundary_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9443 | 122 | MID | markdown of 9443 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED/09_BR-410-09_acceptance_gate_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S5 | markdown | 8664 | 113 | MID | markdown named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `docs/WORKFLOW_APPLIED/README.md` | `N_SMALL` | S8 | markdown | 1084 | 17 | LOW | markdown of 1084 bytes (<= 8 KiB): teaching-sized |
| `docs/WORKFLOW_APPLIED_4.2.0/01_BR-420-01_language_specification_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9504 | 125 | MID | markdown of 9504 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.2.0/02_BR-420-02_native_opcode_semantics_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 10098 | 129 | MID | markdown of 10098 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.2.0/03_BR-420-03_type_system_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9675 | 129 | MID | markdown of 9675 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.2.0/04_BR-420-04_static_verifier_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 10365 | 132 | MID | markdown of 10365 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.2.0/05_BR-420-05_control_flow_verification_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9103 | 115 | MID | markdown of 9103 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.2.0/06_BR-420-06_capability_verification_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9162 | 115 | MID | markdown of 9162 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.2.0/07_BR-420-07_brir_intermediate_representation_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9639 | 123 | MID | markdown of 9639 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.2.0/08_BR-420-08_compilation_pipeline_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 10351 | 132 | MID | markdown of 10351 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.2.0/09_BR-420-09_source_to_binary_provenance_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S5 | markdown | 9156 | 120 | MID | markdown named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `docs/WORKFLOW_APPLIED_4.2.0/10_BR-420-10_specification_synchronization_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9507 | 123 | MID | markdown of 9507 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.2.0/11_BR-420-11_round_trip_tools_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8799 | 114 | MID | markdown of 8799 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.2.0/12_BR-420-12_acceptance_gate_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S5 | markdown | 8841 | 113 | MID | markdown named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `docs/WORKFLOW_APPLIED_4.2.0/README.md` | `N_SMALL` | S8 | markdown | 1489 | 20 | LOW | markdown of 1489 bytes (<= 8 KiB): teaching-sized |
| `docs/WORKFLOW_APPLIED_4.3.0/01_BR-430-01_isa_versioning_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8588 | 112 | MID | markdown of 8588 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.3.0/02_BR-430-02_arithmetic_instructions_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9877 | 129 | HIGH | markdown of 9877 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.3.0/03_BR-430-03_logical_instructions_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8684 | 114 | MID | markdown of 8684 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.3.0/04_BR-430-04_shift_rotation_semantics_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8972 | 119 | MID | markdown of 8972 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.3.0/05_BR-430-05_register_movement_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8235 | 111 | MID | markdown of 8235 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.3.0/06_BR-430-06_memory_operations_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9324 | 122 | MID | markdown of 9324 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.3.0/07_BR-430-07_control_flow_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9058 | 120 | HIGH | markdown of 9058 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.3.0/08_BR-430-08_stack_operations_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8780 | 115 | MID | markdown of 8780 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.3.0/09_BR-430-09_system_instructions_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8940 | 120 | MID | markdown of 8940 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.3.0/10_BR-430-10_arithmetic_modes_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9196 | 120 | HIGH | markdown of 9196 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.3.0/11_BR-430-11_trap_table_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 11076 | 141 | MID | markdown of 11076 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.3.0/12_BR-430-12_abi_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9525 | 126 | MID | markdown of 9525 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.3.0/13_BR-430-13_service_abi_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9296 | 123 | MID | markdown of 9296 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.3.0/14_BR-430-14_isa_conformance_corpus_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9139 | 120 | HIGH | markdown of 9139 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.3.0/15_BR-430-15_acceptance_gate_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S5 | markdown | 8497 | 113 | MID | markdown named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `docs/WORKFLOW_APPLIED_4.3.0/README.md` | `N_SMALL` | S8 | markdown | 1606 | 23 | LOW | markdown of 1606 bytes (<= 8 KiB): teaching-sized |
| `docs/WORKFLOW_APPLIED_4.4.0/01_BR-440-01_trust_root_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8488 | 109 | MID | markdown of 8488 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.4.0/02_BR-440-02_image_signing_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 10169 | 130 | MID | markdown of 10169 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.4.0/03_BR-440-03_verification_path_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 10165 | 132 | MID | markdown of 10165 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.4.0/04_BR-440-04_production_loader_policy_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9103 | 117 | MID | markdown of 9103 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.4.0/05_BR-440-05_key_hierarchy_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8676 | 117 | MID | markdown of 8676 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.4.0/06_BR-440-06_key_rotation_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8616 | 113 | MID | markdown of 8616 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.4.0/07_BR-440-07_revocation_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8501 | 114 | MID | markdown of 8501 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.4.0/08_BR-440-08_rollback_protection_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9041 | 116 | MID | markdown of 9041 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.4.0/09_BR-440-09_secure_startup_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9671 | 126 | MID | markdown of 9671 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.4.0/10_BR-440-10_security_logging_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9157 | 120 | MID | markdown of 9157 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.4.0/11_BR-440-11_acceptance_gate_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S5 | markdown | 8649 | 113 | MID | markdown named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `docs/WORKFLOW_APPLIED_4.4.0/README.md` | `N_SMALL` | S8 | markdown | 1216 | 19 | LOW | markdown of 1216 bytes (<= 8 KiB): teaching-sized |
| `docs/WORKFLOW_APPLIED_4.5.0/01_BR-450-01_storage_abstraction_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8816 | 115 | MID | markdown of 8816 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.5.0/02_BR-450-02_dual_slot_image_store_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9419 | 120 | MID | markdown of 9419 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.5.0/03_BR-450-03_control_record_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9542 | 126 | MID | markdown of 9542 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.5.0/04_BR-450-04_state_authentication_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8608 | 110 | HIGH | markdown of 8608 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.5.0/05_BR-450-05_atomic_update_sequence_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 10133 | 128 | MID | markdown of 10133 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.5.0/06_BR-450-06_power_loss_injection_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9890 | 123 | MID | markdown of 9890 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.5.0/07_BR-450-07_recovery_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8958 | 114 | MID | markdown of 8958 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.5.0/08_BR-450-08_concurrency_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8741 | 112 | MID | markdown of 8741 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.5.0/09_BR-450-09_filesystem_hardening_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8980 | 116 | MID | markdown of 8980 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.5.0/10_BR-450-10_persistent_vm_data_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8826 | 114 | MID | markdown of 8826 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.5.0/11_BR-450-11_acceptance_gate_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S5 | markdown | 8327 | 107 | MID | markdown named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `docs/WORKFLOW_APPLIED_4.5.0/README.md` | `N_SMALL` | S8 | markdown | 1280 | 19 | LOW | markdown of 1280 bytes (<= 8 KiB): teaching-sized |
| `docs/WORKFLOW_APPLIED_4.6.0/01_BR-460-01_word_representation_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9239 | 116 | MID | markdown of 9239 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.6.0/02_BR-460-02_lazy_allocation_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8476 | 111 | MID | markdown of 8476 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.6.0/03_BR-460-03_register_bank_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8702 | 112 | MID | markdown of 8702 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.6.0/04_BR-460-04_stack_redesign_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8743 | 114 | MID | markdown of 8743 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.6.0/05_BR-460-05_constant_pool_PROMPT_AND_WORKFLOW.md` | `N_SMALL` | S8 | markdown | 8163 | 105 | MID | markdown of 8163 bytes (<= 8 KiB): teaching-sized |
| `docs/WORKFLOW_APPLIED_4.6.0/06_BR-460-06_scratch_allocator_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8612 | 111 | MID | markdown of 8612 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.6.0/07_BR-460-07_arithmetic_algorithms_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9102 | 114 | MID | markdown of 9102 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.6.0/08_BR-460-08_memory_quotas_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8795 | 117 | MID | markdown of 8795 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.6.0/09_BR-460-09_resource_traps_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8265 | 111 | MID | markdown of 8265 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.6.0/10_BR-460-10_performance_optimization_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9149 | 114 | MID | markdown of 9149 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.6.0/11_BR-460-11_determinism_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8419 | 111 | MID | markdown of 8419 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.6.0/12_BR-460-12_acceptance_gate_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S5 | markdown | 8556 | 110 | MID | markdown named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `docs/WORKFLOW_APPLIED_4.6.0/README.md` | `N_SMALL` | S8 | markdown | 1360 | 20 | LOW | markdown of 1360 bytes (<= 8 KiB): teaching-sized |
| `docs/WORKFLOW_APPLIED_4.7.0/01_BR-470-01_device_abi_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 9217 | 120 | MID | markdown of 9217 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.7.0/02_BR-470-02_console_device_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8540 | 113 | MID | markdown of 8540 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.7.0/03_BR-470-03_persistent_block_device_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8497 | 109 | MID | markdown of 8497 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.7.0/04_BR-470-04_monotonic_device_PROMPT_AND_WORKFLOW.md` | `N_SMALL` | S8 | markdown | 8054 | 108 | MID | markdown of 8054 bytes (<= 8 KiB): teaching-sized |
| `docs/WORKFLOW_APPLIED_4.7.0/05_BR-470-05_entropy_device_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8377 | 109 | MID | markdown of 8377 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.7.0/06_BR-470-06_clock_device_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8396 | 111 | MID | markdown of 8396 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.7.0/07_BR-470-07_mailbox_device_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8623 | 113 | MID | markdown of 8623 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.7.0/08_BR-470-08_apdu_service_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8902 | 117 | MID | markdown of 8902 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.7.0/09_BR-470-09_diagnostic_device_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8802 | 117 | MID | markdown of 8802 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.7.0/10_BR-470-10_network_policy_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8974 | 117 | MID | markdown of 8974 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.7.0/11_BR-470-11_device_discovery_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8431 | 110 | MID | markdown of 8431 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.7.0/12_BR-470-12_device_quotas_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S8 | markdown | 8561 | 114 | MID | markdown of 8561 bytes (<= 128 KiB) |
| `docs/WORKFLOW_APPLIED_4.7.0/13_BR-470-13_acceptance_gate_PROMPT_AND_WORKFLOW.md` | `N_MEDIUM` | S5 | markdown | 8429 | 110 | MID | markdown named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `docs/WORKFLOW_APPLIED_4.7.0/README.md` | `N_SMALL` | S8 | markdown | 1407 | 21 | LOW | markdown of 1407 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-01_audit.md` | `N_SMALL` | S8 | markdown | 366 | 7 | LOW | markdown of 366 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-01_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1895 | 22 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-01_requirements.json` | `N_MEDIUM` | S6 | json | 5871 | 136 | MID | json of 5871 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-01_tests.log` | `N_MEDIUM` | S6 | log | 31272 | 404 | HIGH | log of 31272 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-02_audit.md` | `N_SMALL` | S8 | markdown | 368 | 7 | LOW | markdown of 368 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-02_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1895 | 22 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-02_requirements.json` | `N_MEDIUM` | S6 | json | 9351 | 214 | MID | json of 9351 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-02_tests.log` | `N_MEDIUM` | S6 | log | 31272 | 404 | HIGH | log of 31272 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-03_audit.md` | `N_SMALL` | S8 | markdown | 367 | 7 | LOW | markdown of 367 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-03_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1895 | 22 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-03_requirements.json` | `N_MEDIUM` | S6 | json | 4177 | 97 | MID | json of 4177 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-03_tests.log` | `N_MEDIUM` | S6 | log | 31272 | 404 | HIGH | log of 31272 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-04_audit.md` | `N_SMALL` | S8 | markdown | 373 | 7 | LOW | markdown of 373 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-04_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1895 | 22 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-04_requirements.json` | `N_MEDIUM` | S6 | json | 5953 | 136 | MID | json of 5953 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-04_tests.log` | `N_MEDIUM` | S6 | log | 31272 | 404 | HIGH | log of 31272 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-05_audit.md` | `N_SMALL` | S8 | markdown | 377 | 7 | LOW | markdown of 377 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-05_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1895 | 22 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-05_requirements.json` | `N_MEDIUM` | S6 | json | 5988 | 136 | MID | json of 5988 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-05_tests.log` | `N_MEDIUM` | S6 | log | 31272 | 404 | HIGH | log of 31272 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-06_audit.md` | `N_SMALL` | S8 | markdown | 375 | 7 | LOW | markdown of 375 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-06_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1895 | 22 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-06_requirements.json` | `N_MEDIUM` | S6 | json | 7093 | 162 | MID | json of 7093 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-06_tests.log` | `N_MEDIUM` | S6 | log | 31272 | 404 | HIGH | log of 31272 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-07_audit.md` | `N_SMALL` | S8 | markdown | 379 | 7 | LOW | markdown of 379 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-07_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1895 | 22 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-07_requirements.json` | `N_MEDIUM` | S6 | json | 6556 | 149 | MID | json of 6556 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-07_tests.log` | `N_MEDIUM` | S6 | log | 31272 | 404 | HIGH | log of 31272 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-08_audit.md` | `N_SMALL` | S8 | markdown | 375 | 7 | LOW | markdown of 375 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-08_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1895 | 22 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-08_requirements.json` | `N_MEDIUM` | S6 | json | 6455 | 149 | MID | json of 6455 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-08_tests.log` | `N_MEDIUM` | S6 | log | 31272 | 404 | HIGH | log of 31272 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-09_audit.md` | `N_SMALL` | S8 | markdown | 374 | 7 | LOW | markdown of 374 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-09_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1895 | 22 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-09_requirements.json` | `N_MEDIUM` | S6 | json | 4242 | 97 | MID | json of 4242 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-09_tests.log` | `N_MEDIUM` | S6 | log | 31272 | 404 | HIGH | log of 31272 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/LCTL_VERIFICATION.json` | `N_SMALL` | S6 | json | 794 | 33 | LOW | json of 794 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/MANIFEST.sha256` | `N_MEDIUM` | S5 | sums | 5881 | 63 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/MEMORY.json` | `N_SMALL` | S6 | json | 2858 | 109 | MID | json of 2858 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/OPERATIONAL_LEDGER.json` | `N_MEDIUM` | S5 | json | 45001 | 1239 | HIGH | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/PERFORMANCE.json` | `N_SMALL` | S6 | json | 850 | 29 | LOW | json of 850 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/QUALIFICATION.json` | `N_MEDIUM` | S6 | json | 41687 | 674 | HIGH | json of 41687 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/REPRODUCIBILITY.json` | `N_SMALL` | S6 | json | 1137 | 25 | LOW | json of 1137 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/SIZE.json` | `N_SMALL` | S6 | json | 652 | 17 | LOW | json of 652 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/TOOLCHAIN.json` | `N_SMALL` | S6 | json | 302 | 9 | LOW | json of 302 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/ACCEPTANCE.json` | `N_MEDIUM` | S5 | json | 901 | 25 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/ARCHITECTURE.json` | `N_SMALL` | S6 | json | 2296 | 93 | MID | json of 2296 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-01_audit.md` | `N_SMALL` | S8 | markdown | 567 | 8 | LOW | markdown of 567 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-01_manifest.sha256` | `N_MEDIUM` | S5 | sums | 4195 | 42 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-01_requirements.json` | `N_MEDIUM` | S6 | json | 5096 | 138 | MID | json of 5096 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-01_tests.log` | `N_MEDIUM` | S6 | log | 8235 | 153 | MID | log of 8235 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-02_audit.md` | `N_SMALL` | S8 | markdown | 587 | 8 | LOW | markdown of 587 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-02_manifest.sha256` | `N_MEDIUM` | S5 | sums | 4203 | 42 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-02_requirements.json` | `N_SMALL` | S6 | json | 3762 | 99 | MID | json of 3762 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-02_tests.log` | `N_MEDIUM` | S6 | log | 8235 | 153 | MID | log of 8235 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-03_audit.md` | `N_SMALL` | S8 | markdown | 580 | 8 | LOW | markdown of 580 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-03_manifest.sha256` | `N_MEDIUM` | S5 | sums | 4203 | 42 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-03_requirements.json` | `N_MEDIUM` | S6 | json | 8155 | 216 | MID | json of 8155 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-03_tests.log` | `N_MEDIUM` | S6 | log | 8235 | 153 | MID | log of 8235 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-04_audit.md` | `N_SMALL` | S8 | markdown | 565 | 8 | LOW | markdown of 565 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-04_manifest.sha256` | `N_MEDIUM` | S5 | sums | 4195 | 42 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-04_requirements.json` | `N_MEDIUM` | S6 | json | 7488 | 203 | MID | json of 7488 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-04_tests.log` | `N_MEDIUM` | S6 | log | 8235 | 153 | MID | log of 8235 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-05_audit.md` | `N_SMALL` | S8 | markdown | 567 | 8 | LOW | markdown of 567 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-05_manifest.sha256` | `N_MEDIUM` | S5 | sums | 4195 | 42 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-05_requirements.json` | `N_MEDIUM` | S6 | json | 4155 | 112 | MID | json of 4155 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-05_tests.log` | `N_MEDIUM` | S6 | log | 8235 | 153 | MID | log of 8235 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-06_audit.md` | `N_SMALL` | S8 | markdown | 562 | 8 | LOW | markdown of 562 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-06_manifest.sha256` | `N_MEDIUM` | S5 | sums | 4195 | 42 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-06_requirements.json` | `N_MEDIUM` | S6 | json | 5127 | 138 | MID | json of 5127 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-06_tests.log` | `N_MEDIUM` | S6 | log | 8235 | 153 | MID | log of 8235 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-07_audit.md` | `N_SMALL` | S8 | markdown | 563 | 8 | LOW | markdown of 563 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-07_manifest.sha256` | `N_MEDIUM` | S5 | sums | 4195 | 42 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-07_requirements.json` | `N_SMALL` | S6 | json | 3310 | 86 | MID | json of 3310 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-07_tests.log` | `N_MEDIUM` | S6 | log | 8235 | 153 | MID | log of 8235 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-08_audit.md` | `N_SMALL` | S8 | markdown | 566 | 8 | LOW | markdown of 566 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-08_manifest.sha256` | `N_MEDIUM` | S5 | sums | 4195 | 42 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-08_requirements.json` | `N_MEDIUM` | S6 | json | 4125 | 112 | MID | json of 4125 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-08_tests.log` | `N_MEDIUM` | S6 | log | 8235 | 153 | MID | log of 8235 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-09_audit.md` | `N_SMALL` | S8 | markdown | 565 | 8 | LOW | markdown of 565 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-09_manifest.sha256` | `N_MEDIUM` | S5 | sums | 4201 | 42 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-09_requirements.json` | `N_SMALL` | S6 | json | 2731 | 73 | LOW | json of 2731 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/BR-410-09_tests.log` | `N_MEDIUM` | S6 | log | 8235 | 153 | MID | log of 8235 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/DELTA.json` | `N_SMALL` | S6 | json | 1302 | 31 | LOW | json of 1302 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/LCTL_VERIFICATION.json` | `N_SMALL` | S6 | json | 846 | 35 | LOW | json of 846 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/MANIFEST.sha256` | `N_MEDIUM` | S5 | sums | 13711 | 133 | MID | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/MEMORY.json` | `N_SMALL` | S6 | json | 688 | 23 | LOW | json of 688 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/OPERATIONAL_LEDGER.json` | `N_MEDIUM` | S5 | json | 42940 | 1197 | HIGH | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/4.1.0-baseline/PERFORMANCE.json` | `N_SMALL` | S6 | json | 284 | 9 | LOW | json of 284 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/QUALIFICATION.json` | `N_SMALL` | S6 | json | 3123 | 72 | LOW | json of 3123 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/REPRODUCIBILITY.json` | `N_SMALL` | S6 | json | 1235 | 25 | LOW | json of 1235 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/SIZE.json` | `N_SMALL` | S6 | json | 603 | 14 | LOW | json of 603 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/TEST.json` | `N_MEDIUM` | S6 | json | 9258 | 54 | LOW | json of 9258 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/4.1.0-baseline/TOOLCHAIN.json` | `N_SMALL` | S6 | json | 508 | 12 | LOW | json of 508 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/ACCEPTANCE.json` | `N_MEDIUM` | S5 | json | 954 | 25 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/BR-420-01_audit.md` | `N_SMALL` | S8 | markdown | 419 | 7 | LOW | markdown of 419 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/BR-420-01_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1135 | 12 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/BR-420-01_requirements.json` | `N_MEDIUM` | S6 | json | 5157 | 124 | MID | json of 5157 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/BR-420-01_tests.log` | `N_SMALL` | S6 | log | 212 | 12 | LOW | log of 212 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/BR-420-02_audit.md` | `N_SMALL` | S8 | markdown | 421 | 7 | LOW | markdown of 421 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/BR-420-02_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1135 | 12 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/BR-420-02_requirements.json` | `N_MEDIUM` | S6 | json | 5764 | 137 | MID | json of 5764 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/BR-420-02_tests.log` | `N_SMALL` | S6 | log | 302 | 14 | LOW | log of 302 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/BR-420-03_audit.md` | `N_SMALL` | S8 | markdown | 409 | 7 | LOW | markdown of 409 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/BR-420-03_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1135 | 12 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/BR-420-03_requirements.json` | `N_MEDIUM` | S6 | json | 5738 | 137 | MID | json of 5738 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/BR-420-03_tests.log` | `N_SMALL` | S6 | log | 237 | 12 | LOW | log of 237 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/BR-420-04_audit.md` | `N_SMALL` | S8 | markdown | 413 | 7 | LOW | markdown of 413 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/BR-420-04_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1135 | 12 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/BR-420-04_requirements.json` | `N_MEDIUM` | S6 | json | 6230 | 150 | MID | json of 6230 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/BR-420-04_tests.log` | `N_SMALL` | S6 | log | 424 | 19 | LOW | log of 424 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/BR-420-05_audit.md` | `N_SMALL` | S8 | markdown | 422 | 7 | LOW | markdown of 422 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/BR-420-05_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1135 | 12 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/BR-420-05_requirements.json` | `N_SMALL` | S6 | json | 4076 | 98 | MID | json of 4076 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/BR-420-05_tests.log` | `N_SMALL` | S6 | log | 322 | 14 | LOW | log of 322 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/BR-420-06_audit.md` | `N_SMALL` | S8 | markdown | 420 | 7 | LOW | markdown of 420 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/BR-420-06_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1135 | 12 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/BR-420-06_requirements.json` | `N_SMALL` | S6 | json | 3620 | 85 | MID | json of 3620 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/BR-420-06_tests.log` | `N_SMALL` | S6 | log | 342 | 14 | LOW | log of 342 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/BR-420-07_audit.md` | `N_SMALL` | S8 | markdown | 429 | 7 | LOW | markdown of 429 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/BR-420-07_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1135 | 12 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/BR-420-07_requirements.json` | `N_MEDIUM` | S6 | json | 4690 | 111 | MID | json of 4690 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/BR-420-07_tests.log` | `N_SMALL` | S6 | log | 318 | 14 | LOW | log of 318 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/BR-420-08_audit.md` | `N_SMALL` | S8 | markdown | 418 | 7 | LOW | markdown of 418 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/BR-420-08_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1135 | 12 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/BR-420-08_requirements.json` | `N_MEDIUM` | S6 | json | 6431 | 150 | MID | json of 6431 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/BR-420-08_tests.log` | `N_SMALL` | S6 | log | 255 | 12 | LOW | log of 255 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/BR-420-09_audit.md` | `N_SMALL` | S8 | markdown | 424 | 7 | LOW | markdown of 424 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/BR-420-09_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1135 | 12 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/BR-420-09_requirements.json` | `N_SMALL` | S6 | json | 4095 | 98 | MID | json of 4095 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/BR-420-09_tests.log` | `N_SMALL` | S6 | log | 196 | 11 | LOW | log of 196 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/BR-420-10_audit.md` | `N_SMALL` | S8 | markdown | 426 | 7 | LOW | markdown of 426 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/BR-420-10_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1135 | 12 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/BR-420-10_requirements.json` | `N_MEDIUM` | S6 | json | 4587 | 111 | MID | json of 4587 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/BR-420-10_tests.log` | `N_SMALL` | S6 | log | 271 | 14 | LOW | log of 271 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/BR-420-11_audit.md` | `N_SMALL` | S8 | markdown | 413 | 7 | LOW | markdown of 413 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/BR-420-11_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1135 | 12 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/BR-420-11_requirements.json` | `N_SMALL` | S6 | json | 2989 | 72 | LOW | json of 2989 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/BR-420-11_tests.log` | `N_SMALL` | S6 | log | 233 | 12 | LOW | log of 233 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/BR-420-12_audit.md` | `N_SMALL` | S8 | markdown | 412 | 7 | LOW | markdown of 412 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.2.0-baseline/BR-420-12_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1135 | 12 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/BR-420-12_requirements.json` | `N_SMALL` | S6 | json | 3106 | 72 | LOW | json of 3106 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/BR-420-12_tests.log` | `N_SMALL` | S6 | log | 326 | 13 | LOW | log of 326 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/DELTA.json` | `N_SMALL` | S6 | json | 736 | 26 | LOW | json of 736 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/LCTL_VERIFICATION.json` | `N_SMALL` | S6 | json | 587 | 21 | LOW | json of 587 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/MANIFEST.sha256` | `N_MEDIUM` | S5 | sums | 16877 | 153 | MID | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/MEMORY.json` | `N_SMALL` | S6 | json | 688 | 23 | LOW | json of 688 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/OPERATIONAL_LEDGER.json` | `N_MEDIUM` | S5 | json | 53017 | 1365 | HIGH | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/PERFORMANCE.json` | `N_SMALL` | S6 | json | 283 | 9 | LOW | json of 283 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/PROVENANCE.json` | `N_MEDIUM` | S5 | json | 1832 | 60 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/QUALIFICATION.json` | `N_SMALL` | S6 | json | 3070 | 68 | LOW | json of 3070 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/QUALIFICATION_COMMANDS.log` | `N_MEDIUM` | S6 | log | 30303 | 343 | HIGH | log of 30303 bytes (<= 256 KiB) |
| `evidence/4.2.0-baseline/REPRODUCIBILITY.json` | `N_SMALL` | S6 | json | 1383 | 20 | LOW | json of 1383 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/SEMANTIC_AUTHORITY.json` | `N_MEDIUM` | S5 | json | 433 | 13 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.2.0-baseline/SIZE.json` | `N_SMALL` | S6 | json | 480 | 15 | LOW | json of 480 bytes (<= 4 KiB) |
| `evidence/4.2.0-baseline/TOOLCHAIN.json` | `N_SMALL` | S6 | json | 319 | 10 | LOW | json of 319 bytes (<= 4 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-01_audit.md` | `N_SMALL` | S8 | markdown | 366 | 7 | LOW | markdown of 366 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-01_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1895 | 22 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-01_requirements.json` | `N_MEDIUM` | S6 | json | 5871 | 136 | MID | json of 5871 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-01_tests.log` | `N_MEDIUM` | S6 | log | 31272 | 404 | HIGH | log of 31272 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-02_audit.md` | `N_SMALL` | S8 | markdown | 368 | 7 | LOW | markdown of 368 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-02_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1895 | 22 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-02_requirements.json` | `N_MEDIUM` | S6 | json | 9351 | 214 | MID | json of 9351 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-02_tests.log` | `N_MEDIUM` | S6 | log | 31272 | 404 | HIGH | log of 31272 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-03_audit.md` | `N_SMALL` | S8 | markdown | 367 | 7 | LOW | markdown of 367 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-03_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1895 | 22 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-03_requirements.json` | `N_MEDIUM` | S6 | json | 4177 | 97 | MID | json of 4177 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-03_tests.log` | `N_MEDIUM` | S6 | log | 31272 | 404 | HIGH | log of 31272 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-04_audit.md` | `N_SMALL` | S8 | markdown | 373 | 7 | LOW | markdown of 373 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-04_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1895 | 22 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-04_requirements.json` | `N_MEDIUM` | S6 | json | 5953 | 136 | MID | json of 5953 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-04_tests.log` | `N_MEDIUM` | S6 | log | 31272 | 404 | HIGH | log of 31272 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-05_audit.md` | `N_SMALL` | S8 | markdown | 377 | 7 | LOW | markdown of 377 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-05_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1895 | 22 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-05_requirements.json` | `N_MEDIUM` | S6 | json | 5988 | 136 | MID | json of 5988 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-05_tests.log` | `N_MEDIUM` | S6 | log | 31272 | 404 | HIGH | log of 31272 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-06_audit.md` | `N_SMALL` | S8 | markdown | 375 | 7 | LOW | markdown of 375 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-06_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1895 | 22 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-06_requirements.json` | `N_MEDIUM` | S6 | json | 7093 | 162 | MID | json of 7093 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-06_tests.log` | `N_MEDIUM` | S6 | log | 31272 | 404 | HIGH | log of 31272 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-07_audit.md` | `N_SMALL` | S8 | markdown | 379 | 7 | LOW | markdown of 379 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-07_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1895 | 22 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-07_requirements.json` | `N_MEDIUM` | S6 | json | 6556 | 149 | MID | json of 6556 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-07_tests.log` | `N_MEDIUM` | S6 | log | 31272 | 404 | HIGH | log of 31272 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-08_audit.md` | `N_SMALL` | S8 | markdown | 375 | 7 | LOW | markdown of 375 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-08_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1895 | 22 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-08_requirements.json` | `N_MEDIUM` | S6 | json | 6455 | 149 | MID | json of 6455 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-08_tests.log` | `N_MEDIUM` | S6 | log | 31272 | 404 | HIGH | log of 31272 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-09_audit.md` | `N_SMALL` | S8 | markdown | 374 | 7 | LOW | markdown of 374 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-09_manifest.sha256` | `N_MEDIUM` | S5 | sums | 1895 | 22 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-09_requirements.json` | `N_MEDIUM` | S6 | json | 4242 | 97 | MID | json of 4242 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/BR-401-09_tests.log` | `N_MEDIUM` | S6 | log | 31272 | 404 | HIGH | log of 31272 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/LCTL_VERIFICATION.json` | `N_SMALL` | S6 | json | 794 | 33 | LOW | json of 794 bytes (<= 4 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/MANIFEST.sha256` | `N_MEDIUM` | S5 | sums | 5881 | 63 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/MEMORY.json` | `N_SMALL` | S6 | json | 2858 | 109 | MID | json of 2858 bytes (<= 4 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/OPERATIONAL_LEDGER.json` | `N_MEDIUM` | S5 | json | 45001 | 1239 | HIGH | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/PERFORMANCE.json` | `N_SMALL` | S6 | json | 850 | 29 | LOW | json of 850 bytes (<= 4 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/QUALIFICATION.json` | `N_MEDIUM` | S6 | json | 41687 | 674 | HIGH | json of 41687 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/REPRODUCIBILITY.json` | `N_SMALL` | S6 | json | 1137 | 25 | LOW | json of 1137 bytes (<= 4 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/SIZE.json` | `N_SMALL` | S6 | json | 652 | 17 | LOW | json of 652 bytes (<= 4 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/4.0.1-baseline/TOOLCHAIN.json` | `N_SMALL` | S6 | json | 302 | 9 | LOW | json of 302 bytes (<= 4 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/ACCEPTANCE.json` | `N_MEDIUM` | S5 | json | 901 | 25 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/ARCHITECTURE.json` | `N_SMALL` | S6 | json | 2296 | 93 | MID | json of 2296 bytes (<= 4 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/BR-410-01_audit.md` | `N_SMALL` | S8 | markdown | 567 | 8 | LOW | markdown of 567 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/BR-410-01_manifest.sha256` | `N_MEDIUM` | S5 | sums | 4195 | 42 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/BR-410-01_requirements.json` | `N_MEDIUM` | S6 | json | 5096 | 138 | MID | json of 5096 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/BR-410-01_tests.log` | `N_MEDIUM` | S6 | log | 8235 | 153 | MID | log of 8235 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/BR-410-02_audit.md` | `N_SMALL` | S8 | markdown | 587 | 8 | LOW | markdown of 587 bytes (<= 8 KiB): teaching-sized |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/BR-410-02_manifest.sha256` | `N_MEDIUM` | S5 | sums | 4203 | 42 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/BR-410-02_requirements.json` | `N_SMALL` | S6 | json | 3762 | 99 | MID | json of 3762 bytes (<= 4 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/BR-410-02_tests.log` | `N_MEDIUM` | S6 | log | 8235 | 153 | MID | log of 8235 bytes (<= 256 KiB) |
| `evidence/4.3.0-baseline/4.2.0-baseline/4.1.0-baseline/BR-410-03_audit.md` | `N_SMALL` | S8 | markdown | 580 | 8 | LOW | markdown of 580 bytes (<= 8 KiB): teaching-sized |
| ... 493 more in SORT_LEDGER.json | | | | | | | |

**Portable storage.** 58 script(s) are stored under an alias (`cargo/_alias/<sha256(path)[:16]><ext>`) because their original path cannot exist on every host (a path that differs only by case from another, or a delivered path over 140 characters -- `Unikernel_Containership/berths/vm_large/<slot>/cargo/<path>` -- which a Windows extraction would refuse); their identity, bytes, node and rule are unchanged. First few:

* `docs/WORKFLOW_APPLIED/02_BR-410-02_remove_host_assumptions_from_the_core_PROMPT_AND_WORKFLOW.md` -> `_alias/1764322ea8ba9958.md` -- the delivered path would be 151 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `docs/WORKFLOW_APPLIED/03_BR-410-03_define_host_abstraction_layer_PROMPT_AND_WORKFLOW.md` -> `_alias/403a30990fefa281.md` -- the delivered path would be 143 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `docs/WORKFLOW_APPLIED_4.2.0/01_BR-420-01_language_specification_PROMPT_AND_WORKFLOW.md` -> `_alias/4bc0549c01af154f.md` -- the delivered path would be 142 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `docs/WORKFLOW_APPLIED_4.2.0/02_BR-420-02_native_opcode_semantics_PROMPT_AND_WORKFLOW.md` -> `_alias/ee708e6fbdca6fe2.md` -- the delivered path would be 143 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `docs/WORKFLOW_APPLIED_4.2.0/05_BR-420-05_control_flow_verification_PROMPT_AND_WORKFLOW.md` -> `_alias/dd57af59df3a5ab4.md` -- the delivered path would be 145 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `docs/WORKFLOW_APPLIED_4.2.0/06_BR-420-06_capability_verification_PROMPT_AND_WORKFLOW.md` -> `_alias/3a8e76dcb848d257.md` -- the delivered path would be 143 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `docs/WORKFLOW_APPLIED_4.2.0/07_BR-420-07_brir_intermediate_representation_PROMPT_AND_WORKFLOW.md` -> `_alias/d5ff2cebf997f7a6.md` -- the delivered path would be 152 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `docs/WORKFLOW_APPLIED_4.2.0/09_BR-420-09_source_to_binary_provenance_PROMPT_AND_WORKFLOW.md` -> `_alias/a38e68fbc42a51ac.md` -- the delivered path would be 147 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `docs/WORKFLOW_APPLIED_4.2.0/10_BR-420-10_specification_synchronization_PROMPT_AND_WORKFLOW.md` -> `_alias/f93b2ccae60747f0.md` -- the delivered path would be 149 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `docs/WORKFLOW_APPLIED_4.3.0/02_BR-430-02_arithmetic_instructions_PROMPT_AND_WORKFLOW.md` -> `_alias/fe0ff3a685a4b35f.md` -- the delivered path would be 143 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `docs/WORKFLOW_APPLIED_4.3.0/04_BR-430-04_shift_rotation_semantics_PROMPT_AND_WORKFLOW.md` -> `_alias/3f313655a8de1bfd.md` -- the delivered path would be 144 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `docs/WORKFLOW_APPLIED_4.3.0/14_BR-430-14_isa_conformance_corpus_PROMPT_AND_WORKFLOW.md` -> `_alias/7630fc451c1b06eb.md` -- the delivered path would be 142 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* ... 46 more in SORT_LEDGER.json (`portable_storage.aliased`)
