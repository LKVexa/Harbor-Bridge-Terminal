# INV-19 - OS asynchronous analogues

**Version:** 5.0.0 (see `CHANGELOG.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

OS asynchronous analogues are the mapping between the component world's streams and futures and what the host operating system actually offers -- epoll, kqueue, io_uring, IOCP. Each has a different shape (readiness versus completion), and the mapping has to be honest about which, because a readiness API pretending to be a completion API loses errors.

## Responsibility

Own the host-side asynchronous backend: detect the available mechanism, map readiness or completion semantics onto stream credit and future resolution, and degrade to a portable fallback without changing observable behaviour.

## Owns

- Backend detection and selection
- Readiness-to-credit mapping
- Completion-to-future mapping
- The portable fallback backend
- Per-backend error translation into component-world errors

## Explicitly does not own

- Stream and future semantics
- The async ABI
- Guest code
- Scheduling policy
- Kernel behaviour

## Non-goals

- Reimplementing kernel interfaces
- Exposing backend detail to guests
- Choosing scheduling policy
- Pretending a readiness API reports completion errors

## Interfaces

- `arm` - PK_ASYNC_ARM/1 - arm a descriptor for readiness or submit a completion
- `backend` - PK_ASYNC_BACKEND/1 - the selected mechanism and its semantics class
- `reap` - PK_ASYNC_REAP/1 - collect readiness or completion events

## Service-level objectives

- **behavioural identity** - identical component-visible outcomes on every backend (error budget: no budget)
- **fallback availability** - the portable backend is available 100% of the time (error budget: no budget)
- **reap latency** - p99 event reaped within 1 scheduler tick of readiness (error budget: 1% may exceed)

## What is in 5.0.0

| Path | Contents |
|---|---|
| `backend.py` | the 4.x reference state machine (kept, unchanged semantics) |
| `hostio/iouring.py` | native Linux io_uring completion backend: raw `io_uring_setup/enter/register` + mmap via ctypes, opcode probe, CQ-overflow flush, cancellation, fork guard |
| `hostio/readiness.py` | native epoll and kqueue adapters, `selectors`-based portable fallback, idempotent wakeup, `ReadinessIO` (the real syscall after readiness) |
| `hostio/iocp.py` | Windows IOCP adapter (ctypes) — implemented, **not yet executed on Windows** |
| `hostio/capabilities.py` | operational host probes, deterministic selection, reason codes |
| `hostio/driver.py` | `AsyncHost`: authorize → audit → admit → reserve → submit → translate → resolve; health, recovery, quarantine, failover |
| `hostio/errors.py` | `PK_ASYNC_ERROR/1` canonical taxonomy (POSIX, io_uring, Win32, Winsock, NTSTATUS) |
| `hostio/integration.py` | INV-18 futures, INV-17 stream credit, INV-15 waitable sets (reference implementations behind Protocols) |
| `hostio/{config,policy,resources,security,audit,observability,schema,ops}.py` | MC-11..MC-22 machinery |
| `schemas/` | JSON Schema `PK_ASYNC_{BACKEND,ARM,REAP,ERROR}/1`, frozen v1 copies, golden + malformed fixtures |
| `tests/` | unit, contract, native-host, integration, security, fuzz/adversarial suites (run under `python` and `python -O`) |
| `tools/` | `run_gate.py` (evidence bundle + verdict), `pk_core_preflight.py`, `bench.py`, `soak.py`, `certify.py`, `supply_chain.py`, `release_pipeline.sh` |
| `governance/` | ownership, ADRs, requirements, threat model, release/canary/rollback, incident runbook, lifecycle, exceptions, reviews, dashboard |
| `evidence/` | generated: gate result, signed evidence bundle, test results, bench, soak, compat matrix, SBOM, signed manifest, self-test |

## Running it

```
bash tools/release_pipeline.sh            # everything below, in order
python tools/run_gate.py                  # 100-requirement verdict + signed evidence bundle
python tools/run_gate.py --verify         # independent re-verification of the bundle
python tools/run_gate.py --self-test      # the gate must catch tampering and known-bad builds
python tools/pk_core_preflight.py         # MC-01: exits 2 (BLOCKED) until pk_core is pinned
python -m unittest discover -s tests      # stays red on purpose while pk_core is absent
```

## Audit status

See `AUDIT_REPORT.md` and `evidence/gate_result.json`. The verdict is **BLOCKED**, not GO: the remaining blockers are external decisions and platforms (pk_core source, named owners/approvers, Windows/macOS/BSD/arm64 runners, KMS binding, multi-hour soak, authoritative sibling layers), each named in the evidence bundle.
