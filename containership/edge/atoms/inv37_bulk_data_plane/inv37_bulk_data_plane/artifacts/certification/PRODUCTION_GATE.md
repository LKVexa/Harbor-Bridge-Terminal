# INV-37 production gate — NO_GO

- Artifact: `4.3.0` `sha256:b10fcef314b630ecc6e170600580c79691b568087c022af23388edcd72bba9f1`
- Config digest: `None`
- Generated: 2026-09-23T03:31:55.233101+00:00
- Signature: `None`

| Criterion | Domain | Requirements | Status | Reason |
|---|---|---|---|---|
| unit_contract_security_tests | testing | C081, C082, C086, C087 | **PASS** | repository evidence current |
| conformance_fixtures | interfaces | C029, C016, C027 | **PASS** | repository evidence current |
| perf_regression_gate | performance | C062, C070 | **PASS** | repository evidence current |
| governance_metadata | ownership | C009, C098, C099 | **BLOCKED** | evidence status BLOCKED |
| adr_approved | architecture | C010, C031 | **BLOCKED** | ADR not approved |
| host_guest_zero_copy | architecture | C010, C011, C066 | **BLOCKED** | external evidence not supplied |
| vm_topology_integration | testing | C030, C083 | **BLOCKED** | external evidence not supplied |
| multi_arch_runtime_matrix | testing | C084, C093 | **BLOCKED** | external evidence not supplied |
| mtls_or_workload_identity | security | C023, C044 | **BLOCKED** | external evidence not supplied |
| encryption_provider_pinned | security | C047 | **BLOCKED** | external evidence not supplied |
| independent_penetration_test | security | C041, C050, C087 | **BLOCKED** | external evidence not supplied |
| soak_burst_fleet_scale | performance | C063, C088 | **BLOCKED** | external evidence not supplied |
| power_thermal_edge | performance | C068 | **BLOCKED** | external evidence not supplied |
| partition_disaster_drill | resilience | C055, C060, C089 | **BLOCKED** | external evidence not supplied |
| restore_drill | operations | C095 | **BLOCKED** | external evidence not supplied |
| canary_rollback_drill | operations | C038, C092 | **BLOCKED** | external evidence not supplied |
| dashboards_alerts_deployed | observability | C080, C074 | **BLOCKED** | external evidence not supplied |
| escalation_tabletop | ownership | C009, C097 | **BLOCKED** | external evidence not supplied |
| sbom_signed_artifact | implementation | C031, C045 | **BLOCKED** | external evidence not supplied |

## Blockers

- governance_metadata
- adr_approved
- host_guest_zero_copy
- vm_topology_integration
- multi_arch_runtime_matrix
- mtls_or_workload_identity
- encryption_provider_pinned
- independent_penetration_test
- soak_burst_fleet_scale
- power_thermal_edge
- partition_disaster_drill
- restore_drill
- canary_rollback_drill
- dashboards_alerts_deployed
- escalation_tabletop
- sbom_signed_artifact
- approvals_missing:architecture_approver,security_owner,service_owner,sre_owner
- config_digest_not_bound
- evidence_unsigned
