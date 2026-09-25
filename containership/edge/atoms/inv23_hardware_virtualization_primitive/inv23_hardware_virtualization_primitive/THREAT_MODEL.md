# INV-23 threat model

Scope: INV-23 5.0.0 probe, claim, ownership, schemas, telemetry, evidence. Reviewed 2026-09-23 by the owner-role (single-owner project; independent review is open item SEC-1).

## Trust boundaries

| Boundary | Trust |
|---|---|
| Host kernel | trusted for /dev/kvm, /proc, ioctl results |
| Firmware | trusted, but its setting is observed not assumed |
| Hypervisor (when we are a guest) | untrusted for bare-metal claims (T02/T03) |
| Local administrative user | trusted (can defeat all local controls) |
| Unprivileged local user | untrusted (T11, T13) |
| INV-23 process | trusted; holds tokens in memory only |
| Native probe helper | none shipped; OS DLLs via ctypes only (T14) |
| pk_core | trusted after SHA-256 pin verification (T18) |
| Adjacent components | must use admission.py (T15) |
| Evidence storage | tamper-evident, not tamper-proof (T17) |
| Telemetry destination | untrusted for secrets (T16) |

## Threats

| ID | Threat | Asset | Attacker / trust | Surface | Preconditions | Mitigation | Residual risk | Detection | Validation |
|---|---|---|---|---|---|---|---|---|---|
| T01 | False-positive `usable` | admission decision | any/bug | backend classification | backend bug or unexpected OS state | ProbeResult refuses usable without facility_usable; schema semantic check; admission re-validates | new OS facility semantics | probe_failures by reason; evidence in report | test_backends: usable_requires_positive_evidence; BackendFuzz |
| T02 | CPUID spoofing | bare-metal verdict | malicious L1 hypervisor | cpuinfo flags | hypervisor controls CPUID | usable needs /dev/kvm open + KVM_GET_API_VERSION; CPUID never proof | hypervisor that also hides `hypervisor` bit and passes KVM through | nesting gauge; evidence cpu_flags | test_backends guest tests; tests/hardware (lab) |
| T03 | Nested guest impersonating bare metal | nesting honesty SLO | guest workload | report.bare_metal | hypervisor bit exposed | guest => depth null, bare_metal false; schema forbids virtualized+depth0 | hypervisor hiding the hypervisor bit (see T02) | nesting_depth gauge | test_guest_never_bare_metal; invalid_probe_virtualized_depth0 |
| T04 | Firmware virtualization disabled | report soundness | operator/firmware | firmware | VT-x off in BIOS | no /dev/kvm => present-disabled/device_absent; Windows PF flag | Linux cannot distinguish module-unloaded vs BIOS-off | reason code device_absent | test_device_absent; lab firmware toggle (MC-11 open) |
| T05 | Permission/config failure misread as absence | report soundness | local config | /dev/kvm ACL | user not in kvm group | EACCES => present-disabled/permission_denied, distinct from absent | — | reason permission_denied | test_permission_denied_is_not_absent |
| T06 | Cross-process claim race | exclusivity | concurrent VMMs | claim provider | simultaneous acquire | flock critical section around read-modify-write; single winner | NFS/network FS locks unsupported | claim_conflicts_total | test_exactly_one_winner_per_round (12 procs x 25 rounds) |
| T07 | Claim spoofing via holder strings | ownership | other local process | release() | knows holder name | 256-bit token; only SHA-256 persisted; holder is display-only | token theft from process memory | INV23-E006 release_rejected | test_exclusive_and_token_authority |
| T08 | PID reuse | ownership liveness | time | pid | owner dies, PID recycled | record binds pid + /proc starttime (Linux) / creation FILETIME (Windows) | macOS: no start identity -> lease governs | stale_owner_recoveries (pid_reused) | test_dead_owner_pid_reuse_and_reboot |
| T09 | Stale ownership after crash | availability | crash | record | owner killed | liveness + lease expiry => takeover with new generation | remote-host owners wait full lease | INV23-E007 | test_sigkill_owner_is_recovered_and_fenced |
| T10 | Split brain after recovery | exclusivity | paused owner | downstream ops | owner resumes after takeover | fencing generation; validate()/renew() reject old generation | downstream that never calls fence() | fencing_rejections_total | test_lease_expiry_takeover_and_fencing |
| T11 | Symlink/path attack on ownership files | integrity | unprivileged local user | state dir | writable parent | 0700 dir owned by uid, lstat checks, O_NOFOLLOW, O_EXCL temp files | root attacker | InsecureStateDir error | test_state_dir_permissions_and_symlink_refused; test_symlinked_record_not_followed |
| T12 | Lock-file deletion/replacement | exclusivity | user with dir access | *.lock | same uid | lock only guards critical sections; record+gen file authoritative; gen floor check | same-uid attacker can delete record (fail-closed on corrupt, not on delete) | ownership_corrupt; audit history | test_lock_file_tampering |
| T13 | Untrusted local-user DoS | availability | unprivileged user | shared state dir | group-shared dir | per-user default namespace; group dirs are operator-provisioned; lease bounds hold time | group member can hold slot for lease duration | claim_conflicts_total | ops review |
| T14 | Malicious native helper substitution | probe integrity | local attacker | native helper | n/a | no native helper shipped: probes use stdlib os/fcntl/ctypes on OS DLLs only | ctypes loads system WinHvPlatform.dll/libc via OS search path | — | n/a (documented) |
| T15 | Schema downgrade/confusion | interface | peer component | report.schema | consumer accepts /1 | admission accepts only /2; version mismatch rejected | consumers not using admission.py | NotAdmitted(schema_version_rejected) | test_schema_version_checked_at_boundary |
| T16 | Telemetry secret leakage | token secrecy | log reader | events/spans/metrics | token in fields | redaction of token/token_sha256; bounded label vocab; Claim.__repr__ hides token | custom sinks bypassing Telemetry | test coverage only | test_claim_signals_and_redaction; test_unbounded_labels_rejected |
| T17 | Evidence-ledger tampering | certification | anyone with repo write | evidence/*.jsonl | write access | hash-chained ledgers; checksums.sha256; tools/verify_evidence.py | no signatures yet (WVR-004) | verify fails | tools/verify_evidence.py; test_repository |
| T18 | Dependency/supply-chain compromise | build | upstream | pk_core, dev tools | tampered vendor copy | vendored pk_core SHA-256 pinned and verified before import; runtime stdlib-only; SBOM | dev tools from PyPI in CI | vendor integrity diagnostic | test_pkcore_compat; SBOM |
| T19 | TOCTOU between probe and claim | admission | environment change | claim() | device removed after probe | ClaimManager re-probes uncached immediately before acquire | change after acquisition until next probe | INV23-E002 | test_device_disappears_between_probe_and_claim |
| T20 | Capability changes after probe | report soundness | firmware update/driver unload | cache | long-lived cache | TTL cache (5 s default) + invalidate(); VirtPrimitive re-evaluates | window up to TTL | probe gauge | test_cache_ttl_and_invalidation |
