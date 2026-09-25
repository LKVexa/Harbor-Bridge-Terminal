# Changelog

## 4.3.0 — 2026-09-23 — missing-component implementation pass

Applied `INV27_v4.2.0_Missing_Component_Implementation_Checklist.md` (MC-001…MC-094) through the chop shop.

**Seal verification from bytes (P0)**

- New: `image/elf.py`, a bounded ELF64 parser with limits and a work budget.
- New: `image/facts.py`, which derives the syscall surface, capabilities and a positive
  single-address-space proof from the binary, using Unikraft- and Solo5-convention profiles.
- New: `image/blob.py`, content-addressed immutable bytes, re-hashed before exec.
- New: `trust/signing.py`, with a DSSE-style Ed25519 envelope, provenance binding, a trust root with
  validity windows and revocation, and staleness checks.
- New: `manifest.py` (strict `PK_UNIKERNEL_SEAL_MANIFEST/1`), `bootcontract.py` and `isolation.py`.
- New: `admission.py`, which runs A0–A13 and writes a decision record for every step.

**Execution**

- `vmm.py` adds QEMU and Firecracker plans and a supervisor. The supervisor handles the ready marker,
  timeout, crash, serial flood and SIGTERM→SIGKILL, and cleans up.
- `service.py` adds authn/authz, quotas, idempotency, fencing, quarantine, disable, the journal,
  reconcile, audit, telemetry, health and explain.

**Platform**

- New modules: `authz.py`, `config.py` (generations, atomic apply, rollback, hash-chained history),
  `lifecycle.py`, `precedence.py`, `sealed_store.py` (AES-256-GCM with rotation, refuses plaintext),
  and `errors.py` (52 stable codes).
- Donor modules from INV-72: `audit.py`, `redaction.py`, `resilience.py` and `telemetry.py`.

**Restored and vendored**

- `MASTER.md` restored verbatim.
- `pk_core` vendored unchanged. The conformance suite runs instead of skipping.

**Fixtures**

- 12 real ELF images built from source (`tests/fixtures/build_fixtures.sh`), with bytes pinned in
  `FIXTURES.json`.

**Governance and evidence**

- Documents: ADR-0001 (Proposed), SPEC, THREAT_MODEL, FORMATS, VERSIONING, CAPACITY, DISCONNECTED,
  INTERFACES, COPY_ANALYSIS and LIFECYCLE.
- Operations: OWNERS, RUNBOOK, INCIDENT, BACKUP_RESTORE, ROLLOUT and BOUNDARIES.
- Registries and policies: waivers, reviews, EOL, telemetry, alerts, dashboards, perf thresholds, the
  compatibility matrix and the identity inventory.
- Repository files: SECURITY, CONTRIBUTING, CODEOWNERS, NOTICE, THIRD-PARTY-NOTICES, pyproject,
  requirements.lock and the CI workflow.
- Tools: `tools/` has rtm, mc_status, release_gate, governance_check, pk_gate, perf_gate, manifest,
  sbom, deps_check, lint, coverage_check, bootstrap and ci.

**Defects found by this pass's own tests and fixed**

1. The per-tenant quota counted only `starting`/`running`, so concurrent runs overcommitted it. The
   concurrency test caught this 1 time in 6 runs. Admitted-but-not-started instances now count.
2. A concurrent identical idempotency key could create two instances. The key is now re-checked
   under the lock.
3. The fuzz harness itself crashed on a buffer truncated to ≤ 8 bytes. That was a harness bug, not a
   parser bug.
4. `.pyc` files leaked into the tree from the `-O` conformance subprocess. It now runs with `-B`, and
   a clean-tree test guards against it.
5. **Found by an independent adversarial review (HIGH):** `derive_syscalls` counted a handler only
   when its ELF symbol type was FUNC. An `@notype` `uk_syscall_r_socket` was left out of the derived
   surface, so an image carrying a forbidden syscall was admitted. Any defined handler now counts.
   The regression fixture is `uk_hidden_notype.elf`, and `FACTS_VERSION` moved to 1.0.1.
6. **Review finding (MEDIUM):** the journal chain was unkeyed. Anyone with write access could
   re-chain it and forge the state reconciled on restart. `Journal` now takes an HMAC key from the
   host secret store (`journal_key`), and a test proves an unkeyed re-chain is rejected.
7. `_cstr` scanned byte-by-byte. Switching to `bytes.find` took the 20k-symbol admission p99 from
   150 ms to about 97–118 ms.

The legacy `runtime.verify_seal` is retained for API compatibility. The admission path never calls it.

# Changelog - INV-27

## 4.2.0 - 2026-09-23

Repository audit, runtime hardening, and verification pass.

### Runtime hardening

- Extracted security-critical seal admission primitives to dependency-free `runtime.py` so they can be tested without `pk_core`.
- Added strict validation for image identity fields, architecture, syscall/feature sets, set members, tenant identity, and `single_address_space`.
- Admission remains case-insensitive for disqualifying features and now fails closed on malformed entries rather than leaking incidental `AttributeError`/sorting failures.
- Seal evidence is now immutable (`MappingProxyType`) and uses immutable syscall tuples, preventing post-admission mutation of the evidence attached to an instance.
- Instance stop is idempotent for normal lifecycle use and detects corrupted/unknown lifecycle state.

### Verification and documentation

- Added dependency-free `tests/test_runtime.py` covering valid admission plus malformed metadata, disqualifying features, drift, syscall policy, architecture mismatch, tenant validation, immutability, and lifecycle behavior.
- Added `verify_repo.py` for offline version/checklist/compile/runtime verification.
- Corrected the README's stale assertion that `MASTER.md` was included; it is absent from the supplied archive and is recorded as a missing source artifact.
- Synchronized `VERSION`, `__version__`, README, and conformance version pin to 4.2.0.

### Residual gap audit

See `AUDIT_REPORT.md`. The repository is a hardened reference component, not yet a complete production unikernel execution subsystem; production integration, artifact cryptographic verification, hypervisor/device execution, observability, performance certification, release engineering, and several governance artifacts remain missing.


## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::verify_seal: disqualifying-feature check was case-sensitive, so features={"DLOPEN"} or {"Exec"} passed the seal -> compare lower-cased feature names
- component.py::verify_seal: non-set syscall/feature fields (e.g. a list) crashed with TypeError mid-check -> refuse with SealInvalid (TypeError for a non-set permitted)
- component.py::run: empty tenant accepted -> ValueError
- component.py::assess_security (items[2]): claimed shell/exec are refused but only dlopen/fork were exercised -> now exercises shell, exec and mixed-case Exec

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
