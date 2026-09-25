# Functional requirements — INV-39 (MC-003)

Status: **Proposed** (owner approval pending). Applicability: **L** = Linux node, **M** = macOS node, **CP** = control plane.

| ID | Requirement | Applies | Verified by |
|---|---|---|---|
| FR-01 | The tier SHALL refuse to exec a workload unless NoNewPrivs=1 and Seccomp=2 are read back from the kernel for that process. | L | test_enforcement_linux.test_kernel_read_back_shows_controls |
| FR-02 | The syscall filter SHALL be default-deny, SHALL kill on foreign architecture and x32 numbers, and SHALL refuse unknown syscall names at compile time. | L | test_backends_and_fuzz.CompilerTest |
| FR-03 | The tier SHALL reduce bounding, permitted, effective, inheritable and ambient capability sets to the profile's retained set and SHALL lock securebits against root regain. | L | test_kernel_read_back_shows_controls, escape probes |
| FR-04 | The tier SHALL enter every namespace the profile lists or refuse to start; the default profile lists pid, mount, net, ipc, uts, user. | L | read-back `namespaces_new` |
| FR-05 | The tier SHALL close all descriptors not on the allow-list and SHALL strip loader/interpreter environment variables. | L | escape probes `inherited_fds`, `ld_preload_env` |
| FR-06 | The tier SHALL apply rlimits (core=0, nofile, nproc, fsize) and SHALL kill the whole pid namespace at timeout, cancellation or host death. | L | timeout / cancellation / host-crash tests |
| FR-07 | Evidence SHALL be signed and bound to node, sandbox, profile digest, config digest, release digest, nonce and issue time; verifiers SHALL reject tamper, replay, rebinding and staleness. | L, M, CP | EvidenceTest |
| FR-08 | Every public payload SHALL validate against its versioned schema; peers SHALL negotiate the highest common version or refuse. | CP | FixtureContractTest, NegotiationTest |
| FR-09 | Every refusal SHALL carry a registered error code with outcome class and retryability, and SHALL be recorded as a reason in the audit chain. | CP | ErrorTaxonomyTest, RefusalPathTest |
| FR-10 | Launch, update, inspect, terminate and quarantine SHALL require an authenticated principal holding a tenant-scoped capability. | CP | AuthTest, AuthzTest |
| FR-11 | Configuration SHALL be validated before activation, activated atomically, recorded with provenance, and rolled back automatically on a failed health check. | CP | ConfigTest |
| FR-12 | When control-plane dependencies are unavailable and `offline_mode=refuse`, the tier SHALL refuse new launches. | CP | RefusalPathTest |
| FR-13 | The tier SHALL NOT be used for untrusted or hostile code; PLN-04 trust classes other than `trusted`/`first-party` SHALL be refused. | CP | InteropTest.test_pln04_trust_classes |
| FR-14 | On macOS the tier SHALL run workloads only under a default-deny Seatbelt profile. | M | BLOCKED — needs macOS runner |
