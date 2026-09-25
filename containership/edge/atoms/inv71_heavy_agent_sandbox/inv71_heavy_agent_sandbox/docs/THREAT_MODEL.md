# INV-71 threat model

## Security objective

Prevent a hostile or compromised heavyweight agent session from reading another session's data, escaping its isolation boundary, acquiring ambient host/network/device/secret authority, exhausting shared resources, or causing a later session to inherit guest-visible state.

## Trust assumptions

The guest workload is untrusted. Inputs, package contents, browser content, and remote endpoints may be hostile. Production control-plane actors, host images, snapshots, policies, and binaries must be authenticated and integrity-checked before trust. The local Python reference model is not a trust boundary.

## Principal threat classes

| Threat class | Representative attacks | Reference-model coverage | Production controls still required |
|---|---|---|---|
| Malicious tenant/workload | path traversal, quota abuse, forbidden egress, cross-session residue | canonical path rejection, quotas, default-deny allowlist, clean re-instantiation tests | real microVM isolation, host filesystem/device policy, cgroups, kernel hardening, escape testing |
| Compromised dependency/content | malicious package/browser payload, DNS/IP tricks | bare-host canonicalization and exact allowlist matching | DNS resolution policy, rebinding protection, destination IP enforcement, TLS policy, proxy/firewall enforcement |
| Host/control-plane abuse | unauthorized create/attach/teardown, policy tampering | not implemented | workload identity, mTLS/authn, authorization, signed policy, separation of duties, audit export |
| Supply-chain compromise | modified Firecracker/kernel/rootfs/snapshot | not implemented | pinned versions, SBOM, signatures, provenance/SLSA controls, vulnerability response |
| Resource exhaustion | disk/file/log expansion | bounded reference disk/file/history limits | CPU, memory, pids, I/O, network, snapshot, image-cache and fleet admission controls |
| Escape/privilege escalation | hypervisor, kernel, device, jailer or syscall escape | not implemented | jailer/seccomp/device minimization, kernel policy, adversarial escape tests, patch SLAs |
| Replay/spoofing | replayed control commands, forged teardown/egress records | local hash-chain detects in-memory mutation of retained audit entries | authenticated durable event transport, anti-replay tokens/nonces, external timestamping/signing |
| Side channels | timing/cache/speculation/co-tenancy leakage | not implemented | host placement policy, CPU/memory isolation analysis, confidential-compute options where required |
| Residual data | next session receives previous writable state | fresh-base model and teardown tests | block/image discard verification, memory zeroization guarantees, snapshot hygiene, host cache policy |

## Important residual risks

Python objects cannot guarantee secure memory erasure; clearing dictionaries does not prove underlying allocator pages were zeroized. The reference audit chain is process-local and unsigned. Hostname allowlisting does not by itself solve DNS rebinding or enforce the resolved destination. The model has no CPU, memory, process, device, syscall, namespace, hypervisor, or cryptographic identity boundary. These are production-blocking gaps, not optional enhancements.

## v4.3.0: threat → control → executable test (C087)

| Threat ID | Threat | Control | Tests (reference scope) | Real-boundary test |
|---|---|---|---|---|
| TM-01 | cross-session residue | clean base, disjoint owned resources, verified teardown, quarantine on leak | `test_sandbox.SandboxModelTest.test_clean_snapshot_isolation`, `test_control_lifecycle.RuntimePlanTest.test_distinct_sessions_share_nothing`, `test_control_lifecycle.EndToEndTest.test_leaked_resource_blocks_closed` | BLOCKED: memory/disk residue on KVM |
| TM-02 | exfiltration to arbitrary host | DNS-bound capabilities, blocked ranges, CNAME allowlisting, TTL re-check | `test_control_security.EgressBindingTest.*`, `test_control_faults.FaultInjectionTest.test_resolver_flapping_never_serves_stale` | BLOCKED: nftables on a real TAP |
| TM-03 | session consuming the host | cgroup/rlimit plan, admission, fair share, reserve | `test_control_lifecycle.RuntimePlanTest.test_plan_contents`, `test_control_lifecycle.ResilienceTest.test_admission_reserve_quota_fairness` | BLOCKED: fork/memory/IO flood on a VM |
| TM-04 | unauthorized control action | authn matrix, default-deny authz, two-person, tenant binding | `test_control_security.AuthnTest.*`, `test_control_security.AuthzTest.*` | BLOCKED: mTLS/PKI |
| TM-05 | replay/spoofing | single-use nonces, fencing epochs, MAC'd capabilities and audit | `test_control_security.AuthnTest.test_replay`, `test_control_lifecycle.EndToEndTest.test_stale_epoch_rejected`, `test_control_security.EgressBindingTest.test_enforcement_rejects_other_tuple_or_forged` | - |
| TM-06 | supply-chain compromise | signed, pinned, serial-monotonic manifest; revocation | `test_control_security.ArtifactTest.*` | BLOCKED: real signing keys |
| TM-07 | audit tampering / loss | chained, MAC'd, anchored stream; refuse-not-drop | `test_control_security.AuditStreamTest.*`, `test_control_lifecycle.EndToEndTest.test_audit_outage_fails_create_without_committing` | BLOCKED: WORM sink |
| TM-08 | malformed/untrusted input | canonical parsers + fuzzing | `test_control_faults.FuzzAndLimitsTest.*` | coverage-guided fuzzing of the node agent |
| TM-09 | escape / privilege escalation | jailer, seccomp, no devices/mounts, per-session uid | `test_control_lifecycle.RuntimePlanTest.test_refusals`, `test_governance.PlanHygieneTest.*` | BLOCKED: escape testing |
| TM-10 | side channels | SMT off in plan; co-tenancy policy | `test_control_lifecycle.RuntimePlanTest.test_plan_contents` | BLOCKED |
| TM-11 | trust dependency outage used as bypass | fail-closed grace | `test_control_lifecycle.EndToEndTest.test_trust_dependency_outage_fails_closed` | - |
| TM-12 | stale controller / split brain | fencing, never-reissued epochs | `test_control_faults.FaultInjectionTest.test_partition_reconnect`, `test_control_faults.BoundedStateTest.test_stale_epoch_after_release_and_reuse` | - |

Residual risks that remain BLOCKED on a real host are tracked as open items in `evidence/traceability.json`. None is waived.
