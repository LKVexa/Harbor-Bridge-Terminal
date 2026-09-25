# Named Exceptions (deferred items)

Every item here is a known gap in v5.0.0, not a hidden one. Severity: **blocker** = blocks a production GO; **major** = must close or be re-approved before 5.1.0; **minor** = tracked debt.
Review date for all open items: **2026-12-31**. Owner column is open until EXC-001 closes.

| ID | Item | Severity | Rationale | Target | Checklist components |
|---|---|---|---|---|---|
| EXC-001 | Accountable owner, on-call, security contact, and human sign-offs (ADRs, security review, exit approval) not assigned | **blocker** | an automated pass cannot assign people or approve on their behalf | before GO | all "Owner/approval" fields, EXIT-01, EXIT-18, EXIT-20 |
| EXC-002 | Hardware-rooted attestation (TPM 2.0 quote / measured boot) | major | software HMAC attestation shipped; needs platform TPM integration | 5.1.0 | 18, 1 |
| EXC-003 | mTLS / SPIFFE identity for non-local callers | minor | no remote caller in scope (ADR-0003) | 5.2.0 | 7 |
| EXC-004 | wasmtime, Firecracker and unikernel runtime adapters | **blocker** for those runtimes | protocol + process adapter shipped; real adapters need target runtimes | 5.1.0 | 3, 11 |
| EXC-005 | Verification of systemd sandbox/seccomp on real hosts (least-privilege runtime test) | major | unit file written and reviewed statically; not executed under systemd here | 5.0.1 | 16, 28 |
| EXC-006 | Hash-pinned (`--require-hashes`) dev dependency lock | minor | versions pinned; hashes not fetchable in this build environment | 5.0.1 | 41 |
| EXC-007 | Encryption at rest for state dir | minor | delegated to host (LUKS/fscrypt); no secrets stored in state | host policy | 4, 17 |
| EXC-008 | Power/thermal measurement on constrained edge hardware | minor | needs physical far-edge hardware | 5.1.0 | 50 |
| EXC-009 | Multi-arch / multi-Python CI actually executed (aarch64, 3.10, 3.12, 3.13) | major | matrix defined in CI; this build executed x86_64 / 3.11 only | first CI run | 43, 57 |
| EXC-010 | pk_core 100-check conformance gate | major | `pk_core` not available in this build; integration tests skip cleanly | when pk_core available | 53, 60, 63 |
| EXC-011 | License selection | **blocker** for redistribution | only the owner can choose a license | before distribution | 62 |
| EXC-012 | Independent security review / penetration test | **blocker** | threat-model tests are self-authored | before GO | 27, EXIT-18 |
| EXC-013 | OTLP trace exporter and Grafana dashboards | minor | exporter hook and alert rules shipped; exporter/dashboards not | 5.1.0 | 33, 37 |
| EXC-014 | Real multi-node fleet test against a live control plane | major | fleet simulated in-process (tools/soak.py) | 5.1.0 | 47, 49 |
| EXC-015 | Canary/staged rollout exercised on a real fleet; upgrade+rollback exercised on production-representative state | major | procedure documented, migration tested on synthetic v1 state only | first rollout | 39, EXIT-12 |
