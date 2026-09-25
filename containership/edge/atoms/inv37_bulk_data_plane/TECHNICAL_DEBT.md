# Technical debt and production blockers — INV-37 v4.3.0

Owner column names accountable **roles** from `governance/OWNERS.json`; no person is invented. Items close only with evidence accepted by that role. Gate column = production-gate criterion that stays BLOCKED until closed.

| ID | Debt / blocker | Owner role | Gate criterion | Status |
|---|---|---|---|---|
| TD-001 | Host↔guest zero-copy (virtio/vhost-user or equivalent) — phase-2 ADR, implementation, pins | architecture_approver | host_guest_zero_copy, adr_approved | open (intra-host shm done in 4.3.0) |
| TD-002 | mTLS/SPIFFE/workload identity, node attestation, KMS/HSM key custody | security_owner | mtls_or_workload_identity | open (HMAC capability tokens done) |
| TD-003 | Approved, pinned AEAD provider; encryption in transit/at rest with rotation | security_owner | encryption_provider_pinned | open (fail-closed guard done) |
| TD-004 | Integration with INV-36/GAP-14/PLN-06/INV-38 on VM/container topology | service_owner | vm_topology_integration | open |
| TD-005 | Multi-arch / multi-runtime / hypervisor CI matrix | service_owner | multi_arch_runtime_matrix | open |
| TD-006 | Production-hardware baselines, soak, fleet scale; power/thermal on edge | architecture_approver | soak_burst_fleet_scale, power_thermal_edge | open (sandbox baseline + harness done) |
| TD-007 | Partition / disaster / multi-node failover drills | sre_owner | partition_disaster_drill | open |
| TD-008 | Restore, canary and rollback drills | sre_owner | restore_drill, canary_rollback_drill | open |
| TD-009 | Deploy dashboards/alerts; validate under failure/load | sre_owner | dashboards_alerts_deployed | open (definitions done) |
| TD-010 | Assign people to 5 roles; tabletop; approve SLOs/SLAs/thresholds | service_owner | governance_metadata, escalation_tabletop | open |
| TD-011 | Signed release artifact and attestation | service_owner | sbom_signed_artifact | open (SBOM + pins done) |
| TD-012 | Independent penetration test incl. side channels | security_owner | independent_penetration_test | open |
| TD-013 | Trace propagation into adjacent layers; live infra graph correlation | sre_owner | vm_topology_integration | open |
| TD-014 | `PK_BULK_MANIFEST/1` object digest does not bind size/chunk metadata cryptographically (geometry checks compensate); design `/2` signed by control plane | architecture_approver | — | open, carried from 4.2.0 |
| TD-015 | `pk_core` adapter unpinned; conformance tests not executed here | service_owner | — | open |
