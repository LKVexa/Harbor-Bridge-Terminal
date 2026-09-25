# INV-40 - Full virtualization tier

**Version:** 4.3.0 (see `CHANGELOG.md`; checklist status in `CHECKLIST_STATUS.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Audit source:** `CHECKLIST.json` contains the 100 source requirements. The previously referenced `MASTER.md` is not present in this repository and is therefore not claimed as bundled evidence.

The full virtualization tier is the heavyweight end: a complete machine with its own kernel and a full device model. It is the tier you use when the workload is hostile or the guest OS is not yours, and it costs seconds to boot and hundreds of megabytes to run -- numbers this element states plainly so the tier is chosen on purpose rather than by default.

## Responsibility

Own full-machine virtualization: run a complete guest with its own kernel and full device model, enforce the strongest available isolation boundary, and account honestly for the boot time and memory footprint the tier costs.

## Owns

- Full guest lifecycle with a complete device model
- The strongest-available isolation boundary for a guest
- Boot-time and footprint accounting
- Guest-OS opacity (no host introspection assumptions)
- Refusal to run without the hardware primitive

## Explicitly does not own

- Guest operating systems
- The CPU primitive itself
- Placement
- Capacity targets
- MicroVM device minimalism

## Non-goals

- Minimal device models
- Millisecond boots
- Introspecting the guest OS
- Providing a software fallback when the hardware primitive is missing

## Interfaces

- `create` - PK_FULL_VM/1 - create a full guest with its device model and footprint
- `boot` - PK_FULL_VM_BOOT/1 - boot result with elapsed time and resident footprint
- `stop` / `destroy` - PK_FULL_VM_STATE/1 - explicit lifecycle state results
- operational failures - PK_FULL_VM_ERROR/1 - stable machine-readable failure codes

## Service-level objectives

- **primitive requirement** - zero guests started without the hardware primitive (error budget: no budget)
- **guest device exclusivity** - zero concrete device instances shared between distinct live guests (error budget: no budget)
- **footprint honesty** - 100% of guests accounted at their real resident size (error budget: no budget)

## Running it

```
python -m unittest discover -s inv40_full_virtualization_tier/tests -v
# pk_core integration tests are skipped when pk_core is unavailable; standalone runtime tests still run.
python -m pk_core list
python -m pk_core run INV-40 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-40 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Hardened runtime model

`runtime.py` is intentionally independent of `pk_core`, and package-level integration imports are lazy, so critical behavior can be imported and tested in an isolated checkout. It enforces a complete baseline device model, strict input validation, hardware-virtualization refusal, explicit VM lifecycle states, a resident-footprint ceiling, thread-safe concrete device-instance leases, and machine-readable operational failure codes.

v4.3.0 adds a production-hardening layer (`fvt/`) around the unchanged reference model, including a KVM-only QEMU/QMP provider adapter; that adapter has not yet been exercised on KVM hardware. The post-update evidence audit and every remaining partial/missing production component are recorded in `AUDIT_REPORT.md` and `MISSING_COMPONENTS.md`.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-40`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-40`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.

## v4.3.0 hardening layer (`fvt/`)

Stdlib-only; `runtime.py`, `contract.py` and `component.py` are byte-identical to v4.2.0.

| Module | Purpose |
|---|---|
| `fvt/service.py` | `FullVmService`: schema → authn → authz → fencing → quarantine → admission → breaker → provider → runtime invariants → journal → audit → telemetry |
| `fvt/provider.py` | `HostProbe`, `QemuKvmProvider` (`-accel kvm` only, QMP, VmRSS), `FakeProvider` (non-production lane) |
| `fvt/config.py` | declarative layered config, secure defaults, fail-closed validation, provenance, atomic activation, rollback |
| `fvt/identity.py` | capability tokens (HMAC), replay cache, exact op+tenant scopes, fail-closed trust |
| `fvt/audit.py` · `fvt/journal.py` | hash-chained audit · crash-consistent WAL with backup/restore |
| `fvt/resilience.py` · `fvt/fencing.py` | retry/backoff/jitter, breaker, admission/quotas, deadlines · fencing epochs |
| `fvt/telemetry.py` | metrics, structured logs, W3C trace, decision records + explain |
| `fvt/schema.py` + `schemas/` | versioned typed contracts |
| `fvt/compat.py` · `fvt/gate.py` | pk_core API contract + protocol negotiation · production exit gate |

```
python tools/ci.py            # tests (normal + -O), install check, fuzz, bench, SBOM, manifest, traceability, gate
python tools/bootstrap.py --state-dir /tmp/inv40 --fake-provider
```
`tools/ci.py` exits 3 (INCOMPLETE) while the `pk_core` and `kvm` lanes cannot run, and the gate returns NO_GO while any requirement is unowned.
