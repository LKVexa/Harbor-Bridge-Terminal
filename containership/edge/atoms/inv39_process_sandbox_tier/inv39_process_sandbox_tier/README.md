# INV-39 - Process sandbox tier

**Version:** 5.1.0 (see `CHANGELOG.md`)  
**Group:** 01_Source_Inventory · **Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements in `CHECKLIST.json`; 106 residual components in `docs/INV39_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST_v5.0.0.md`, traced in `TRACEABILITY.json`

INV-39 is the process-level sandbox tier: default-deny seccomp, minimal capabilities, full namespace set, and an honest statement of the shared-kernel residual surface.

## What changed in 5.1.0 — the assurance boundary moved
5.0.0 was a policy model that verified caller-supplied read-back. **5.1.0 enforces on Linux**: `linux/launcher.py` applies every control itself and only calls `execve` after the host has read the state back **from the kernel** (`/proc/<pid>` while the workload is blocked after seccomp is installed). A mismatch kills the tree before any workload instruction runs. Evidence is emitted as signed `PK_SANDBOX_APPLIED/2` with `os_enforcement_proven: true`.

Still **not** production-certified. Exit gate verdict: **NO_GO** (`evidence/exit-gate.json`). Component status: **50 IMPLEMENTED · 47 PARTIAL · 9 BLOCKED · 0 ACCEPTED**. "Implemented" means code plus positive/negative tests pass on the build host — not an acceptance.

## Layout
| Path | Role |
|---|---|
| `sandbox.py` | 5.0.0 policy model (profile canonicalisation, digest, `PK_SANDBOX_APPLIED/1`) — unchanged, deprecated output |
| `linux/seccomp.py` | seccomp-BPF compiler + installer, NO_NEW_PRIVS |
| `linux/primitives.py` | namespaces, id maps, securebits, capabilities, mounts, fresh /proc, rlimits, env, fds |
| `linux/landlock.py` | optional Landlock filesystem policy |
| `linux/launcher.py` | supervisor/workload tree, pre-exec gate, kernel read-back, timeout/cancel/reaping |
| `backends.py` | feature probe (fail closed), bubblewrap adapter, Seatbelt compiler |
| `runtime.py` | `SandboxService`: authn → authz → quarantine → admission → lifecycle → launch → signed evidence → audit |
| `attestation.py` | node identity, evidence signing/verification (nonce, binding, freshness), hash-chained audit log |
| `control.py` | tokens, RBAC, idempotency, retry, admission/quotas/breaker, fenced leases, quarantine, version negotiation |
| `config.py` | validated config, tighten-only overlays, atomic activation, provenance, rollback, redaction |
| `observability.py` | metrics (Prometheus text), structured logs, W3C trace context, diagnostics, reason records, explain |
| `errors.py`, `lifecycle.py`, `schema_check.py`, `integration.py`, `profiles.py` | taxonomy, state machine, schema validator, PLN-04/GAP-13/GAP-09 adapters, profile sources |
| `schemas/`, `fixtures/` | 5 public schemas; valid + one-defect invalid fixtures |
| `tests/` | 103 tests incl. real-kernel escape probes (`tools/escape_probes.c`) |
| `tools/` | bench + gate, reproducible build + SBOM + provenance, exit gate, traceability, bootstrap |
| `docs/` | ownership, ADR, SHALL requirements, NFRs, threat model, compatibility, limits, operating policy, runbooks, exceptions |

## Quick start (Linux)
```sh
sh tools/bootstrap.sh          # probe features, run the suite
sh ci/ci.sh                    # full pipeline incl. bench gate, reproducible build, exit gate
INV39_CERT_TARGET=1 python3 tests/run_all.py   # certification mode: any skip is a failure
```
```python
from inv39_process_sandbox_tier.runtime import SandboxService, LaunchRequest
```

## Owns / does not own
Owns the syscall allow-list per profile, capability dropping, namespace entry, pre-exec verification, residual-surface reporting. Does not own the kernel, hardware isolation, other tiers, image formats or placement. Hostile code is a non-goal: PLN-04 routes it to the microVM/VM tiers.
