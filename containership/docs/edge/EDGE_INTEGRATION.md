# Edge-component atoms in UC-2.8.0

UC-2.8.0 is UC-2.7.0 with the 99 supplied edge-component archives combined in. This page says what was installed, how it is tied to the ship, what was measured, and what was deliberately not done.

## What was installed

| | count |
|---|---:|
| archives requested | 99 |
| distinct archives stored byte-for-byte in `edge/source/` | 91 |
| byte-identical duplicates (recorded as aliases, stored once) | 8 |
| elements with a canonical atom in `edge/atoms/` | 86 |
| distinct alternative builds in `edge/variants/` | 4 |
| release-evidence archive (`gap04_v4.3.0_release_evidence.zip`) | 1, under `edge/atoms/gap04_disconnected_operation_controller/_release_evidence/` |
| atoms bound to a PK element in `pk/PK_ATOM_BINDINGS.json` | 85 (every element except the external iOS735 LCTL candidate) |

`edge/EDGE_MANIFEST.json` is the authority: every archive's SHA-256, role (canonical, variant, duplicate, release-evidence), where it was extracted, and the reason a canonical was chosen. The one-shot installer and the exact request list are kept in `provenance/UC280_EDGE_INSTALL.py` and `provenance/UC280_EDGE_REQUESTED.txt`.

### Duplicates

- `pln05_elasticity_plane_v4.2.0_mc_applied.zip` is byte-identical to `pln05_elasticity_plane_v4.2.0_mc_applied_1.zip`
- `inv30_capability_hardware_sandbox_v4.3.0.zip` is byte-identical to `inv30_capability_hardware_sandbox_v4.3.0_1.zip`
- `inv29_hybrid_wasm_unikernel_v4.3.0.zip` is byte-identical to `inv29_hybrid_wasm_unikernel_v4.3.0_1.zip`
- `inv25_microvm_devices_v4.3.0.zip` is byte-identical to `inv25_microvm_devices_v4.3.0_1.zip`
- `inv24_microvm_runtime_v4.3.0.zip` is byte-identical to `inv24_microvm_runtime_v4.3.0_1.zip`
- `inv23_hardware_virtualization_primitive_v5.0.0_remediated.zip` is byte-identical to `inv23_hardware_virtualization_primitive_v5.0.0_remediated_1.zip`
- `inv22_alternative_wasi_branch_v4.3.0_remediated.zip` is byte-identical to `inv22_alternative_wasi_branch_v4.3.0_remediated_1.zip`
- `inv20_http_component_worlds_v4.3.0.zip` is byte-identical to `inv20_http_component_worlds_v4.3.0_1.zip`

### Where one element arrived as more than one distinct build

- **INV-66** — variant `inv66_enterprise_wasm_control_plane_v4.3.0.zip` kept in `edge/variants/inv66_enterprise_wasm_control_plane_v4.3.0/`. Canonical choice: _1 build (202 files, importable package name, 134 tests pass) supersedes the 114-file v4.3.0 archive, retained as a variant.
- **INV-61** — variant `inv61_distributed_wit_rpc_v4.3.0.zip` kept in `edge/variants/inv61_distributed_wit_rpc_v4.3.0/`. Canonical choice: _1 build has the larger green suite (122 pass / 0 fail); the other v4.3.0 archive fails mutual-TLS identity binding and is retained as a variant.
- **INV-55** — variant `inv55_secrets_integration_v4.3.0.zip` kept in `edge/variants/inv55_secrets_integration_v4.3.0/`. Canonical choice: checklist-applied build with an importable package name and a fully green suite; the plain v4.3.0 archive (package dir 'inv55_secrets_integration_v4.3.0', 3 failing tests) is retained as a variant.
- **INV-30** — variant `inv30_capability_hardware_sandbox_v4.2.0_hardened(1).zip` kept in `edge/variants/inv30_capability_hardware_sandbox_v4.2.0_hardened(1)/`. Canonical choice: 4.3.0 full package (128 files, 111 tests pass; the byte-identical v4.3.0 copy is recorded as a duplicate); the 4.2.0_hardened(1) archive is a 15-file remediation-checklist overlay retained as a variant.

## How the atoms are tied to the ship

- **PK bindings.** `pk/PK_ATOM_BINDINGS.json` maps each element id to its atom and to the generated `pk/pk_components/<element>/` package. The generated package, its 100-item checklist and the PK conformance gate are unchanged (`pk/SELFTEST.py` still certifies all 96). The atom is the implementation reference; it answers for itself through its own suite. Ten PK elements have no supplied atom: INV-01, 33, 46, 47, 48, 49, 50, 51, 56, 59.
- **pk_core.** Most atoms declare `pk_core>=4.0` and several ship a lock marked `UNRESOLVED`. UC280 supplies its own `pk/pk_core` (4.0.0) on every atom child's path. Its tree hash is recorded under `pk_core_supplied` in the bindings file so an owner can pin it with each atom's `core_probe.py pin`. The atoms' lock files were not edited.
- **Isolation.** The ship never imports atom code into its own process. `uc edge test` copies the atom into `_runs/edge/work/`, runs its suite in a child interpreter whose import path holds only that atom, its own folders and `pk/`, then deletes the copy. Several suites write benchmark and evidence files into their own trees. The copy keeps those writes out of the sealed atom; before this was added, a run left two shipped files modified, and `edge check --deep` caught it.
- **Integrity.** `uc edge check` verifies every stored archive's SHA-256. `--deep` compares all 11,187 extracted files with their archive members and rejects any unrecorded file or archive. The ship reseal binds `edge/` into `SHA256SUMS.txt` and `MANIFEST.json`.
- **Surfaces.** `uc edge status|list|check [--deep]|show <ID>|test <ID|all> [--jobs N]`, launchers `EDGE.cmd` / `EDGE`, and an `edge_atoms` block in `uc platform status`.

## What was measured

Host: Linux x86_64, Python 3.11.15, runner pytest, 6 parallel suites. Each atom's own suite, unmodified:

**9,833 passed · 41 failed · 0 errors · 46 skipped — 59 suites green, 27 red.**

Every failure is classified in `edge/evidence/EDGE_TEST_RESULTS.json`:

| class | failures | meaning |
|---|---:|---|
| stale-version-pin | 17 | the atom's own conformance test still asserts '4.2.0' while the package declares 4.3.0/5.0.0 -- a defect inside the atom, not an integration fault |
| pk_core-presence-expectation | 11 | tests that expect pk_core to be ABSENT or pinned; UC280 supplies pk_core 4.0.0 on the child path (satisfies every declared 'pk_core>=4.0' requirement) so the 'absent' branch is not taken |
| external-toolchain-absent | 5 | pinned wasm-tools not installed on this host (INV11_WASM_TOOLS) |
| host-performance-slo | 4 | absolute latency/throughput ceilings measured on a shared cloud Linux sandbox under parallel load; not a qualification of the target host |
| atom-internal-unclassified | 4 | remaining atom-internal assertions: INV-16 unsupported-topology fault, INV-21/INV-22 100-requirement answer tables, INV-29 policy-generation version endpoint |

None of these were fixed by editing an atom. An atom archive is kept exactly as supplied, and fixes belong in a new build of that atom.

### Per-atom results

| element | atom | version | verdict | passed | failed | skipped | failure classes |
|---|---|---|---|---:|---:|---:|---|
| `EXT-IOS735-LCTL` | `ios735_lctl` | 0.2.0 | SUITE_GREEN | 49 | 0 | 0 | — |
| `GAP-01` | `gap01_edge_node_supervisor` | 5.0.0 | SUITE_RED | 85 | 1 | 0 | stale-version-pin ×1 |
| `GAP-02` | `gap02_hardware_capability_discovery` | 4.3.0 | SUITE_RED | 154 | 1 | 0 | stale-version-pin ×1 |
| `GAP-03` | `gap03_topology_aware_scheduler` | 4.3.0 | SUITE_GREEN | 264 | 0 | 0 | — |
| `GAP-04` | `gap04_disconnected_operation_controller` | 4.3.0 | SUITE_RED | 142 | 1 | 0 | stale-version-pin ×1 |
| `GAP-05` | `gap05_state_replication_consistency_model` | 4.3.0 | SUITE_GREEN | 129 | 0 | 0 | — |
| `GAP-06` | `gap06_device_identity_and_attestation` | 5.0.0 | SUITE_GREEN | 103 | 0 | 0 | — |
| `GAP-07` | `gap07_artifact_provenance_signing` | 6.0.0 | SUITE_GREEN | 143 | 0 | 0 | — |
| `GAP-08` | `gap08_ota_lifecycle_rollback` | 4.3.0 | SUITE_GREEN | 89 | 0 | 0 | — |
| `GAP-09` | `gap09_unified_observability` | 5.0.0 | SUITE_GREEN | 34 | 0 | 0 | — |
| `GAP-10` | `gap10_power_thermal_aware_scheduling` | 4.3.0 | SUITE_RED | 125 | 1 | 0 | stale-version-pin ×1 |
| `GAP-11` | `gap11_accelerator_scheduling` | 4.2.0 | SUITE_GREEN | 19 | 0 | 0 | — |
| `GAP-12` | `gap12_wan_resilience_and_nat_traversal` | 4.3.0 | SUITE_GREEN | 143 | 0 | 0 | — |
| `GAP-13` | `gap13_policy_engine` | 5.0.0 | SUITE_GREEN | 146 | 0 | 0 | — |
| `GAP-14` | `gap14_data_gravity_manager` | 4.3.0 | SUITE_RED | 169 | 1 | 0 | pk_core-presence-expectation ×1 |
| `GAP-15` | `gap15_runtime_compatibility_certification` | 4.3.0 | SUITE_GREEN | 215 | 0 | 0 | — |
| `INV-02` | `inv02_container_substrate` | 5.0.0 | SUITE_RED | 106 | 1 | 1 | stale-version-pin ×1 |
| `INV-03` | `inv03_container_hardening` | 4.3.0 | SUITE_RED | 83 | 2 | 0 | stale-version-pin ×1, host-performance-slo ×1 |
| `INV-04` | `inv04_current_orchestration` | 4.3.0 | SUITE_GREEN | 106 | 0 | 0 | — |
| `INV-05` | `inv05_current_control_state_system` | 4.3.0 | SUITE_RED | 171 | 1 | 0 | pk_core-presence-expectation ×1 |
| `INV-06` | `inv06_traditional_iac` | 4.3.0 | SUITE_GREEN | 75 | 0 | 0 | — |
| `INV-07` | `inv07_gitops_transition_layer` | 5.0.0 | SUITE_RED | 11 | 1 | 0 | stale-version-pin ×1 |
| `INV-08` | `inv08_dynamic_infrastructure_model` | 4.2.0 | SUITE_GREEN | 11 | 0 | 0 | — |
| `INV-09` | `inv09_portable_compute_isa` | 4.3.0 | SUITE_GREEN | 74 | 0 | 0 | — |
| `INV-10` | `inv10_component_composition_system` | 4.3.0 | SUITE_RED | 70 | 1 | 0 | host-performance-slo ×1 |
| `INV-11` | `inv11_interface_contract_language` | 4.3.0 | SUITE_RED | 81 | 6 | 0 | stale-version-pin ×1, external-toolchain-absent ×5 |
| `INV-12` | `inv12_language_interoperability` | 4.3.0 | SUITE_GREEN | 74 | 0 | 0 | — |
| `INV-13` | `inv13_system_interface` | 4.3.0 | SUITE_GREEN | 124 | 0 | 0 | — |
| `INV-14` | `inv14_previous_asynchronous_model` | 4.3.0 | SUITE_RED | 111 | 1 | 3 | pk_core-presence-expectation ×1 |
| `INV-15` | `inv15_new_asynchronous_abi` | 4.3.0 | SUITE_GREEN | 108 | 0 | 0 | — |
| `INV-16` | `inv16_async_component_functions` | 4.3.0 | SUITE_RED | 107 | 3 | 0 | stale-version-pin ×1, pk_core-presence-expectation ×1, atom-internal-unclassified ×1 |
| `INV-17` | `inv17_streaming_primitive` | 4.3.0 | SUITE_GREEN | 141 | 0 | 0 | — |
| `INV-18` | `inv18_completion_primitive` | 4.3.0 | SUITE_GREEN | 188 | 0 | 5 | — |
| `INV-19` | `inv19_os_asynchronous_analogues` | 5.0.0 | SUITE_RED | 157 | 1 | 10 | pk_core-presence-expectation ×1 |
| `INV-20` | `inv20_http_component_worlds` | 4.3.0 | SUITE_GREEN | 116 | 0 | 3 | — |
| `INV-21` | `inv21_local_service_chaining` | 4.3.0 | SUITE_RED | 126 | 2 | 0 | atom-internal-unclassified ×1, stale-version-pin ×1 |
| `INV-22` | `inv22_alternative_wasi_branch` | 4.3.0 | SUITE_RED | 111 | 4 | 0 | atom-internal-unclassified ×1, pk_core-presence-expectation ×3 |
| `INV-23` | `inv23_hardware_virtualization_primitive` | 5.0.0 | SUITE_GREEN | 86 | 0 | 2 | — |
| `INV-24` | `inv24_microvm_runtime` | 4.3.0 | SUITE_GREEN | 92 | 0 | 6 | — |
| `INV-25` | `inv25_microvm_devices` | 4.3.0 | SUITE_GREEN | 87 | 0 | 0 | — |
| `INV-26` | `inv26_microvm_snapshotting` | 6.0.0 | SUITE_GREEN | 106 | 0 | 0 | — |
| `INV-27` | `inv27_unikernel_execution` | 4.3.0 | SUITE_GREEN | 113 | 0 | 0 | — |
| `INV-28` | `inv28_unikernel_implementations` | 4.3.0 | SUITE_RED | 256 | 1 | 0 | pk_core-presence-expectation ×1 |
| `INV-29` | `inv29_hybrid_wasm_unikernel` | 4.3.0 | SUITE_RED | 116 | 3 | 0 | stale-version-pin ×1, atom-internal-unclassified ×1, host-performance-slo ×1 |
| `INV-30` | `inv30_capability_hardware_sandbox` | 4.3.0 | SUITE_GREEN | 111 | 0 | 2 | — |
| `INV-31` | `inv31_function_execution_architecture` | 4.3.0 | SUITE_GREEN | 82 | 0 | 0 | — |
| `INV-32` | `inv32_elastic_virtualization` | 4.3.0 | SUITE_RED | 131 | 1 | 1 | pk_core-presence-expectation ×1 |
| `INV-34` | `inv34_legacy_cpu_expansion_path` | 5.1.0 | SUITE_GREEN | 70 | 0 | 0 | — |
| `INV-35` | `inv35_high_performance_vm_i_o` | 4.3.0 | SUITE_GREEN | 139 | 0 | 0 | — |
| `INV-36` | `inv36_control_transport` | 5.1.0 | SUITE_GREEN | 171 | 0 | 2 | — |
| `INV-37` | `inv37_bulk_data_plane` | 4.3.0 | SUITE_GREEN | 150 | 0 | 0 | — |
| `INV-38` | `inv38_kernel_bypass_transport` | 4.2.0 | SUITE_GREEN | 138 | 0 | 0 | — |
| `INV-39` | `inv39_process_sandbox_tier` | 5.1.0 | SUITE_GREEN | 103 | 0 | 0 | — |
| `INV-40` | `inv40_full_virtualization_tier` | 4.3.0 | SUITE_RED | 83 | 1 | 1 | stale-version-pin ×1 |
| `INV-41` | `inv41_capability_security` | 4.3.0 | SUITE_GREEN | 106 | 0 | 1 | — |
| `INV-42` | `inv42_capability_descriptors` | 4.3.0 | SUITE_GREEN | 58 | 0 | 0 | — |
| `INV-43` | `inv43_transient_execution_defense` | 4.3.0 | SUITE_GREEN | 125 | 0 | 0 | — |
| `INV-44` | `inv44_wasm_hardening_system` | 4.3.0 | SUITE_GREEN | 50 | 0 | 1 | — |
| `INV-45` | `inv45_sfi_mechanisms` | 4.3.0 | SUITE_GREEN | 156 | 0 | 0 | — |
| `INV-52` | `inv52_messaging_abstraction` | 4.3.0 | SUITE_GREEN | 121 | 0 | 0 | — |
| `INV-53` | `inv53_message_reliability` | 5.1.0 | SUITE_GREEN | 126 | 0 | 0 | — |
| `INV-54` | `inv54_broker_implementations` | 4.3.0 | SUITE_GREEN | 105 | 0 | 0 | — |
| `INV-55` | `inv55_secrets_integration` | 4.3.0 | SUITE_GREEN | 110 | 0 | 0 | — |
| `INV-57` | `inv57_durable_execution` | 4.3.0 | SUITE_GREEN | 79 | 0 | 0 | — |
| `INV-58` | `inv58_existing_service_mesh_layer` | 4.3.0 | SUITE_GREEN | 185 | 0 | 0 | — |
| `INV-60` | `inv60_wasm_application_fabric` | 4.3.0 | SUITE_GREEN | 195 | 0 | 0 | — |
| `INV-61` | `inv61_distributed_wit_rpc` | 4.3.0 | SUITE_GREEN | 122 | 0 | 1 | — |
| `INV-62` | `inv62_edge_topology` | 4.3.0 | SUITE_GREEN | 147 | 0 | 0 | — |
| `INV-63` | `inv63_wasm_deployment_manager` | 4.3.0 | SUITE_GREEN | 110 | 0 | 0 | — |
| `INV-64` | `inv64_application_model` | 4.3.0 | SUITE_RED | 91 | 1 | 0 | stale-version-pin ×1 |
| `INV-65` | `inv65_capability_providers` | 4.3.0 | SUITE_GREEN | 129 | 0 | 1 | — |
| `INV-66` | `inv66_enterprise_wasm_control_plane` | 4.3.0 | SUITE_RED | 134 | 1 | 0 | stale-version-pin ×1 |
| `INV-67` | `inv67_kubernetes_integration_mechanism` | 4.3.0 | SUITE_RED | 116 | 1 | 0 | host-performance-slo ×1 |
| `INV-68` | `inv68_resource_packing` | 4.3.0 | SUITE_GREEN | 79 | 0 | 0 | — |
| `INV-69` | `inv69_agentic_workload_layer` | 4.3.0 | SUITE_GREEN | 133 | 0 | 0 | — |
| `INV-70` | `inv70_fast_agent_sandbox` | 4.3.0 | SUITE_RED | 101 | 1 | 5 | stale-version-pin ×1 |
| `INV-71` | `inv71_heavy_agent_sandbox` | 4.3.0 | SUITE_RED | 132 | 1 | 0 | stale-version-pin ×1 |
| `INV-72` | `inv72_accelerated_workload_requirement` | 4.3.0 | SUITE_GREEN | 163 | 0 | 0 | — |
| `PLN-01` | `pln01_intent_plane` | 4.3.0 | SUITE_GREEN | 68 | 0 | 0 | — |
| `PLN-02` | `pln02_application_plane` | 4.3.0 | SUITE_GREEN | 88 | 0 | 0 | — |
| `PLN-03` | `pln03_distributed_runtime_plane` | 4.3.0 | SUITE_RED | 83 | 1 | 0 | pk_core-presence-expectation ×1 |
| `PLN-04` | `pln04_execution_plane` | 4.3.0 | SUITE_GREEN | 75 | 0 | 1 | — |
| `PLN-05` | `pln05_elasticity_plane` | 4.2.0 | SUITE_GREEN | 188 | 0 | 0 | — |
| `PLN-06` | `pln06_data_plane` | 4.3.0 | SUITE_GREEN | 92 | 0 | 0 | — |
| `PLN-07` | `pln07_security_plane` | 4.3.0 | SUITE_RED | 63 | 1 | 0 | stale-version-pin ×1 |
| `SCH-01` | `sch01_workload_classification_and_runtime_placem` | 4.3.0 | SUITE_GREEN | 109 | 0 | 0 | — |

## What this is not

- A green suite is evidence about that atom on one host. It does not promote any PK checklist item, master-series task or VWS work pack to PASS.
- No atom is wired into berth execution, the hull, VWS control, the TIFF/GIF state path or the 1-bit fabric. The atoms' own services (HTTP endpoints, daemons, systemd units) are not started by the ship.
- Performance ceilings were measured on a shared cloud sandbox under parallel load, not on a target edge host.
- Native Windows execution of the atom suites was not observed here. On Windows with pytest installed, `EDGE.cmd test all` uses pytest automatically. Without pytest it falls back to a file-path unittest driver.
- Not Production GO.
