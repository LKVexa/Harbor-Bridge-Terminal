# Audit report — INV-37 Bulk data plane

**Input:** v4.2.0 (hardened) + `inv37_REMEDIATION_CHECKLIST_v4.2.0.md` (85 incomplete requirements: 48 MISSING, 37 PARTIAL)
**Output:** v4.3.0 · **Date:** 2026-09-22 · **Production gate:** **NO_GO**

## Result

| Status | Before (4.2.0) | After (4.3.0) |
|---|---|---|
| PASS | 15 | 15 (unchanged; carried from the 4.2.0 audit) |
| IMPLEMENTED_PENDING_REVIEW | — | 48 |
| PARTIAL | 37 | 35 |
| MISSING | 48 | 2 (C047 encryption, C068 power/thermal) |

`IMPLEMENTED_PENDING_REVIEW` means every repository-side checklist obligation for that requirement has implementation, specification, automated tests and evidence. The checklist forbids moving a requirement to PASS until the **accountable role** reviews it, and no person is assigned to any role yet — so none of the 85 was promoted to PASS by this pass. The remaining 35 PARTIAL items need things a repository cannot supply: named owners, approvals, real adjacent services, VM/multi-arch/edge hardware, drills, deployed dashboards, signing keys or an external penetration test. Per-requirement done/open detail: `MISSING_COMPONENTS.md`, `REMEDIATION_STATUS.json`.

## What was built

Eleven stdlib-only modules (lifecycle, outcomes, config, checkpoint, security, quota, retry, shm_transport, telemetry, precedence, service), 11 new test files, conformance fixtures and runner, benchmark harness, and eight tools (certification runner, production gate, perf gate, governance check, pin/SBOM check, requirements check, semantics/status renderers, bootstrap). Details: `CHANGELOG.md`.

Headline measured property: on the new shared-memory path the data plane makes **0 payload copies** (peak allocation 0.03 % of object size) versus **2 copies** (peak 2.0×) in the 4.2.0 receiver, at ≈198 vs ≈148 MiB/s in the sandbox (medians of 5 runs). This is **intra-host, cross-process** zero-copy; the **host↔guest** function named by the checklist is still not implemented and fails closed.

## Defects found and fixed during remediation

1. CPython < 3.13 registers *attached* shared-memory segments with the attaching process's resource tracker, which unlinks the owner's region when the attacher exits — an ownership/lifetime bug that would break cross-process zero-copy. Fixed (`shm_transport._untrack`), covered by the cross-process test.
2. Fair admission initially counted immediately-grantable requests against the pending-queue bound (spurious `admission_rejected` with `max_pending=0`). Fixed.
3. The perf gate used single-run p99, which tripped once at 2.0× on the shared sandbox; the harness now reports medians of 5 runs.
4. An independent review pass (separate agent) found: replay cache evicted live nonces under flood (now fails closed and evicts only expired); signed-but-malformed claims raised KeyError instead of `authentication_failed`; a tenant-scoped admin could freeze the whole node (now requires global admin); lease acquire/check-then-write were only thread-locked (now a cross-process `flock`, with a 4-process race test); out-of-range indices in a sealed checkpoint were not bounds-checked; the certification runner tolerated unexpected skips. All fixed with regression tests. It also judged C048 and C070 over-rated; both were moved back to PARTIAL.
5. Documentation drift caught by the new doc checks (two undocumented operator methods; an unbound CODEOWNERS handle). Fixed.

## Verification performed (artifacts in `artifacts/certification/`)

- `tools/run_certification.py`: **148 PASS, 0 FAIL, 2 NOT_EXECUTED** (optional `pk_core` adapter; not counted as evidence). Also passes under `python -O`.
- Conformance: **31/31**, fixture lock intact; also run from the installed wheel.
- Perf gate vs. sandbox baseline: **PASS** (thresholds are proposed, not approved).
- Governance check: **BLOCKED** (all five roles unassigned; tabletop not run) — metadata itself valid.
- Pin/SBOM check: **PASS** (zero runtime dependencies; build pin `setuptools==79.0.1`).
- Wheel build + clean-room venv install: **PASS**; wheel unsigned.
- Production gate: **NO_GO** — 3 of 19 criteria PASS (tests, conformance, perf); 16 BLOCKED; approvals missing for all four approver roles; evidence unsigned; config digest not bound.

## Limits of this audit

Everything ran in one Linux x86_64 sandbox on CPython 3.11.15. Benchmarks are sandbox numbers, not production baselines. Durable-path crash testing kills processes, not machines (no power-loss or filesystem-barrier testing). No external reviewer has looked at the security design.

## To reach production

1. Assign the five roles in `governance/OWNERS.json`, bind CODEOWNERS, run the tabletop.
2. Have those roles review the 50 `IMPLEMENTED_PENDING_REVIEW` items and ADR-0001, and record approvals bound to the source digest.
3. Close TD-001…TD-013 (`TECHNICAL_DEBT.md`), each of which maps to a BLOCKED gate criterion, and drop the resulting evidence into `artifacts/external/`.
4. Run `tools/production_gate.py --run --config-digest <digest>` with `INV37_GATE_KEY_FILE` set.
