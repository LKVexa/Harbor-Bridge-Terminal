# INV-27 — Unikernel execution

**Version:** 4.3.0 (see `CHANGELOG.md`) · **Group:** 01_Source_Inventory · **Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements in `CHECKLIST.json`; upstream prompt corpus restored in `MASTER.md`
**Applied package:** `docs/INV27_v4.2.0_Missing_Component_Implementation_Checklist.md` (94 missing components, 1,883 checkboxes)
**Owners:** see [ops/OWNERS.md](ops/OWNERS.md) (holders UNASSIGNED)

Unikernel execution is the single-address-space bet: the application and its kernel are linked into one
image with no shell, no second process and no syscall surface to abuse. The isolation argument only
holds if the image really is sealed.

**v4.3.0 verifies the seal from the image bytes.** It no longer checks caller-supplied metadata.

## What the admission path does (`admission.admit`)

| Step | Check | Code on failure |
|---|---|---|
| A0–A1 | immutable bytes → sha256, compared with the bound digest | `UK_DIGEST_MISMATCH` |
| A2 | Ed25519 DSSE envelope over a provenance statement that binds the digest; approved builder/toolchain; fresh trust root | `UK_SIG_*`, `UK_PROVENANCE_*`, `UK_TRUST_UNAVAILABLE` |
| A3 | strict `PK_UNIKERNEL_SEAL_MANIFEST/1` | `UK_MANIFEST_INVALID` |
| A4 | bounded ELF64 parser (`image/elf.py`) | `UK_PARSE_*` |
| A5–A9 | static linking; toolchain profile; fork/exec/dlopen/debug capabilities; positive single-address-space proof | `UK_SEAL_*` |
| A10–A11 | manifest syscalls == **binary-derived** syscalls ⊆ site permitted; architecture | `UK_SEAL_DRIFT`, `UK_SEAL_SYSCALL_FORBIDDEN`, `UK_SEAL_ARCH` |
| A12 | boot contract: entry, W^X, memory | `UK_BOOT_CONTRACT`, `UK_SEAL_WX` |
| A13 | deny-by-default device/network/storage plan | `UK_ISOLATION_POLICY` |

`service.UnikernelService` wraps admission with the following:

- **Access control:** authn/authz, tenant scope and quotas.
- **Load control:** idempotency, fencing and load shedding.
- **Operator controls:** quarantine and emergency disable.
- **State:** a hash-chained journal with restart reconciliation, and a tamper-evident audit log.
- **Observability:** metrics, logs and trace, a decision record for every automated action, an
  explain view and a health endpoint.

`vmm.Supervisor` launches the admitted bytes through a hardened QEMU (microvm, `-sandbox …spawn=deny`)
or Firecracker plan. Readiness comes from the serial console, with timeout, crash and flood handling
and guaranteed cleanup.

## Running it

```
python -B inv27_unikernel_execution/tools/ci.py                     # every lane: tests (python and -O), lint, deps, coverage, RTM, MC status, manifest
python -B inv27_unikernel_execution/tests/run_all.py                # 111 tests
python -B inv27_unikernel_execution/tools/bootstrap.py              # day-0 install verification
python -B -m inv27_unikernel_execution.tools.release_gate           # formal exit gate (currently NO_GO)
python -B inv27_unikernel_execution/bench/perf_suite.py             # performance baseline
python -B inv27_unikernel_execution/verify_repo.py                  # v4.2.0-compatible dependency-free check
```

The owner's `pk_core` is vendored unchanged under `_vendor/`, so the 100-item conformance suite now runs
(`tools/pk_gate.py`: 100/100 under `python` and `python -O`). That is declaration conformance only.
Implementation status is in `evidence/MC_STATUS.json` and `evidence/RTM.json`.

## Honest status

See `POST_REMEDIATION_AUDIT.md`. Summary:

- **Missing components:** 62 verified locally, 21 partial, 11 blocked.
- **Release gate:** NO_GO.
- **What is still missing:** a real VMM boot (W-VMM), upstream toolchain fixtures (W-TOOLCHAIN),
  named owners and approvals (W-OWNERS, W-APPROVALS), a licence (W-LICENSE), hosted CI (W-CI), and
  hardware/perf/fleet evidence (W-HW, W-PERF, W-FLEET).

## Day-0 / day-1 / day-2

See `ops/RUNBOOK.md` (bootstrap, deploy, operate), `ops/ROLLOUT.md` (canary and emergency disable),
`ops/INCIDENT.md` and `ops/BACKUP_RESTORE.md`.
