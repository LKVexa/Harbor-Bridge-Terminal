# Changelog - INV-39

## 5.1.0 - 2026-09-22

Execution of `INV39_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST_v5.0.0` (106 components) against the hardened 5.0.0 baseline.

### Enforcement (P0)
- Native Linux backend: seccomp-BPF compiler/installer (arch + x32 kill; exhaustively checked by an in-test cBPF emulator for x86_64 and aarch64), NO_NEW_PRIVS, user-namespace id mapping, securebits lock, full capability-set reduction, pid/mount/net/ipc/uts namespaces, private propagation, fresh /proc, tmpfs, fd closure, env sanitisation, rlimits, optional Landlock.
- Pre-exec gate: the workload blocks after seccomp installation; the host reads the state back from `/proc/<pid>` and releases `execve` only on an exact match. Mismatch → tree killed, `E_NOT_APPLIED`.
- Supervisor with subreaper, signal forwarding, reaping; timeout, cancellation and host-death all kill the whole pid namespace.
- Signed `PK_SANDBOX_APPLIED/2` evidence (node/sandbox/profile/config/release/nonce binding) and a hash-chained audit log.
- 17 adversarial escape probes executed inside the sandbox on every run.

### Control plane, configuration, observability
- Stable error taxonomy + outcome classes; lifecycle state machine; HMAC tokens; tenant-scoped RBAC; idempotency; jittered bounded retry; admission/quotas/circuit breaker; fenced leases; quarantine; version negotiation.
- Validated config with tighten-only overlays, atomic activation, provenance, automatic/operator rollback, secret redaction.
- Metrics, structured logs, W3C trace context, sampled redacted diagnostics, reason records + explain, status surface, alert classes.

### Certification and release
- Schemas for APPLIED/2, ERROR/1, STATUS/1; positive and one-defect negative fixtures; stdlib schema validator.
- Threat model with mechanically derived security suite; fuzzing; concurrency; fault injection; benchmark harness + regression gate.
- Reproducible release build, CycloneDX SBOM, SLSA-style provenance; production exit gate; CI script + workflow; traceability of all 106 components and 100 checks.
- `INV39_CERT_TARGET=1` turns every skipped prerequisite into a failure (no silent skips).

### Honest result
50 IMPLEMENTED · 47 PARTIAL · 9 BLOCKED · 0 ACCEPTED. Exit gate: NO_GO. See `MISSING_COMPONENTS.md`.

## 5.0.0 - 2026-09-22

Repository audit, correctness hardening, and evidence-quality pass.

### Security and correctness

- Split the dependency-free sandbox policy model into `sandbox.py` so its core security semantics are testable even when the external `pk_core` framework is unavailable.
- Changed `Sandbox.start()` to fail closed when no externally supplied applied-state read-back is present. The previous implementation silently substituted the requested state and could therefore claim verification without any enforcement evidence.
- Added strict token canonicalization and validation for profile names, syscalls, capabilities, namespaces, process identifiers, and read-back fields.
- Closed case/whitespace bypasses in forbidden-capability checks (`cap_sys_admin` now canonicalizes to `CAP_SYS_ADMIN`).
- Added explicit lifecycle enforcement: syscall modelling before verified start and duplicate starts now fail.
- Added bounded denial logging (`MAX_DENIAL_LOG`) to prevent an attacker-controlled stream of denied syscall names from growing memory without bound.
- Added a deterministic SHA-256 profile digest to bind applied evidence to the exact requested policy.
- Added explicit `verified`, `verification_scope`, `evidence_source`, `os_enforcement_proven`, and `default_deny` fields so model-level verification cannot be confused with proven OS enforcement.

### Interfaces and tests

- Added JSON Schemas for `PK_SANDBOX_PROFILE/1` and `PK_SANDBOX_APPLIED/1`.
- Added dependency-free unit tests covering canonicalization, unsafe capability rejection, namespace completeness, fail-closed read-back, lifecycle, bounded denial logging, and profile digest stability.
- Updated the `pk_core` conformance version pin to 5.0.0.

### Audit correction

- Corrected the repository's assurance language: the code is a verified policy/read-back model, **not** a production seccomp/bubblewrap/Seatbelt enforcer. Production OS backends and their evidence remain missing and are tracked in `MISSING_COMPONENTS.md`.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- `component.py`: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O`.
- `component.py`: expected-refusal checks fail if the refusal does not occur.
- `tests/test_component.py`: stdlib conformance test added (100 findings, no unexpected partial/blocked, python `-O` parity, version pin).
- `VERSION` file and `__version__` added.

### Defects fixed

- `Sandbox.start`: empty readback dictionaries no longer fall back to the requested profile.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
