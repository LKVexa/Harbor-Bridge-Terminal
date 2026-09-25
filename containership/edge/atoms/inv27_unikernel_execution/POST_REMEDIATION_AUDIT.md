# INV-27 post-remediation audit — v4.3.0

**Date:** 2026-09-23 · **Applied:** `INV27_v4.2.0_Missing_Component_Implementation_Checklist.md` (MC-001…MC-094)
**Baseline:** v4.2.0. That audit found 94 missing components, 9 runtime tests, and 3 conformance tests
that were skipped.

## Verdict

**Production completeness: NOT ESTABLISHED. The release gate returns NO_GO** (`evidence/RELEASE_EVIDENCE.json`).

The core defect v4.2.0 named is closed. v4.2.0 took the image's seal on the caller's word. v4.3.0
works the seal out from the image bytes, checks a signature that binds those exact bytes, and hands
those same bytes to the VMM. What remains open needs environments, hardware or people that this
pass could not supply.

## Numbers (all reproducible from the archive)

| Axis | v4.2.0 | v4.3.0 |
|---|---|---|
| Missing components | 94 missing | 62 verified_local · 21 partial · 11 blocked · 0 unimplemented |
| P0 (27) | 10+ missing | 16 verified_local · 8 partial · 3 blocked |
| Checkboxes (1,883 + 12 global/exit) | 0 | done_local / partial / blocked, per `evidence/MC_STATUS.json` (the rule is in `tools/mc_status.py`) |
| RTM C001–C100 | none | 57 present · 35 partial · 8 blocked (`evidence/RTM.json`) |
| Tests | 9 runtime + 3 skipped | 113 under `python` and `python -O`, 0 undeclared skips. Also passes without `cryptography` (2 declared optional skips). |
| Fuzz | none | 50,000 seeded mutations × 3 seeds, only `UK_PARSE_*`/`UK_SEAL_*` outcomes |
| Coverage (stdlib `trace`) | none | 89.6% of runtime lines (threshold 85%) |
| pk_core conformance | skipped | GO 100/100 under `python` and `-O`. This is declaration conformance; 5 findings are exercised. |
| Admission p99 (9 KB image) | n/a | ≈ 7–9 ms. The SLO is 100 ms. |
| Admission p99 (20k symbols) | n/a | 97–150 ms across runs, at the SLO edge (TD-1) |

## Independent review

An adversarial reviewer (a separate agent, working from reproductions only) found two issues.
Both are fixed and have regression tests.

1. **HIGH.** An `@notype` syscall handler evaded the derived syscall surface, so an image carrying
   `socket` was admitted.
2. **MEDIUM.** The journal chain was unkeyed, so it could be re-chained.

Checked and found to hold:

- provenance canonicalisation and multi-signature handling
- the admit→launch path (no TOCTOU)
- token replay and TTL
- tenant `"*"` scope
- quota and idempotency races
- manifest and isolation escapes

The review is not a human review, and no component is marked reviewed.

## Blocked on (ops/WAIVERS.json, all PROPOSED)

| Waiver | What it needs |
|---|---|
| W-VMM | A real QEMU or Firecracker boot on a reference host. The package mirror refused QEMU here (HTTP 403). |
| W-TOOLCHAIN | Upstream Unikraft and Solo5 golden images. The current fixtures follow those conventions but are built locally. |
| W-KMS | Production trust root, signing service, and KMS or secret store. |
| W-OWNERS | Named holders for the 5 roles and the escalation chain. |
| W-APPROVALS | Approval of ADR-0001, SPEC and thresholds, and a review of each MC. |
| W-LICENSE | The owner's choice of licence. |
| W-CI | Running the declared CI matrix. |
| W-HW | IOMMU and power/thermal hardware. |
| W-PERF | Benchmarks, soak and scale runs on reference hardware. |
| W-FLEET | Failover and residency with PLN-04. |
| W-DRILLS | Rollout, restore and incident drills. |

## Residual technical risk

- **T-11.** Raw inlined `syscall`/`svc` instructions are not detected. The mitigations are the
  toolchain profiles and the VMM seccomp sandbox.
- **TD-1.** The symbol table is materialised eagerly.
- **TD-2.** The Ed25519 implementation is pure Python and not constant-time. The `cryptography`
  backend is selectable.
- The legacy `runtime.verify_seal` remains in the public API.

The previous audit is kept unchanged as `AUDIT_REPORT.md`.
