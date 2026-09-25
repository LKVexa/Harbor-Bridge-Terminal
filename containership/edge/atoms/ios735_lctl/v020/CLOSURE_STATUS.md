# Missing-components closure status — v0.2.0

Executed against `iOS735_LCTL_v0.1.1_MISSING_COMPONENTS_CHECKLIST.md` on 2026-09-23.
Legend: **DONE** = implemented and demonstrated by retained tests/evidence · **BLOCKED** = needs
the owner, credentials, a legal decision, a signing identity or owner infrastructure (see
`docs/OWNER_DECISIONS.md`) · **READY** = the machinery is done and tested, waiting only on a
BLOCKED input.

**Bottom line:** every engineering item that can be done without the owner is done. **No**
component is fully closed under the checklist's Definition of Done, because each one's DoD
includes an owner input (pins, genuine toolchains, licence, security contact, signing key, CI
infrastructure) — except M09, which is closed apart from the `VERIFY/2` evidence it will validate.
`python tools/release.py preflight` shows the live state (currently 6 of 10 gates open — see
`evidence/closure/`).

## Repository invariants

| Invariant | Status |
|---|---|
| `VERSION` / CHANGELOG synchronized (0.2.0) | DONE |
| Deterministic translation contract preserved (`source/`, `canonical/`, `map/` byte-identical to v0.1.1) | DONE — verified by digest comparison |
| unittest suite passes (5 → 48 tests) | DONE |
| 735/735 round trip; 9/9 falsifiers | DONE |
| Manifest regenerated after final changes, verified from fresh extraction | DONE |
| Verifier transactional behaviour not weakened (strengthened: post-run JAR re-hash) | DONE |
| No JAR executed before trust check | DONE — `authenticate()` precedes any `java -jar`; test `test_verifier_fails_closed_before_execution` |
| No secrets in repository | DONE — lock validator rejects credential-like values |

## M01 — Owner toolchain provisioning · HIGH · READY / BLOCKED

| Section | Status | Where |
|---|---|---|
| M01.1 ownership, redistribution, approvers | BLOCKED (owner/legal) | `docs/TOOLCHAIN_PROVISIONING.md` §Redistribution records it as pending |
| M01.2 identity definition (versions, JAR paths, Java ≥21) | DONE; digests BLOCKED | `toolchains/LOCK.json` |
| M01.3 provisioning modes | Manual/offline mode DONE and authoritative until owner decides; bundled/private/public modes BLOCKED on M01.1. Safe atomic archive extraction, spaces-in-paths, absolute path resolution, fail-closed DONE | `tools/toolchain_trust.py` |
| M01.4 artifacts | DONE | provisioning doc, `tools/toolchain_trust.py`, `--json` result |
| M01.5 validation behaviour, stable exit codes 10–16, Java identity capture | DONE | same |
| M01.6 hardening tests (15 listed) | DONE — all 15 covered in `tests/test_release_hardening.py` (Java-version fakes are POSIX-only) |
| M01.7 docs | DONE |
| M01.8 DoD | BLOCKED — needs the genuine toolchains and approved pins |

## M02 — Genuine `VERIFY/2` evidence · HIGH · BLOCKED (READY)

The genuine toolchains are not available to this run, so no genuine `VERIFY/2` exists and none
was fabricated. `evidence/VERIFY.json` stays the historical `VERIFY/1`.

| Section | Status |
|---|---|
| M02.1–M02.2 preconditions, run, metadata capture | READY — `tools/verify.py` now records Java path/vendor/runtime, OS/arch, lock version and digest |
| M02.3–M02.5 envelope, 7 gates × 44, outputs | READY — automated as `tools/evidence_check.py` (schema + semantics + lock correlation) |
| M02.6 drift gate | READY — `evidence_check` + CI verification-only diff check; procedure in `docs/RELEASE_PROCESS.md` |
| M02.7 negative/transactional evidence | DONE with the **test-only simulator**: failures injected at compile, provenance and stats → exit 1, `verdict=FAIL`, `generated_outputs_committed=false`, canonical and all 132 analysis files byte-identical |
| M02.8–M02.9 retention / DoD | BLOCKED |

## M03 — Full owner-toolchain CI gate · HIGH · READY / BLOCKED

| Section | Status |
|---|---|
| M03.1 trust architecture (no PR triggers, protected environment, self-hosted runner) | DONE in YAML; environment/runner/required-check settings BLOCKED (owner repo settings) |
| M03.2 workflow steps | DONE — `.github/workflows/owner-toolchain-verify.yml`; SHA pinning of actions left as owner action |
| M03.3 generated-file policy | DONE — verification-only default, release-generation on tags/dispatch |
| M03.4 platform coverage | Offline matrix kept (Win/Linux × 3.10/3.13) and now also runs the simulator tests; authoritative full-verifier platform BLOCKED on toolchain platform info |
| M03.5 timeouts/concurrency | DONE — 180-min job, per-command timeouts kept, concurrency group, bounded retention |
| M03.6 evidence retention | DONE in YAML |
| M03.7 CI security tests | Fork isolation by construction (no PR triggers); hash-mismatch/missing-toolchain/unit-failure/checker-failure cases DONE locally; live CI tests BLOCKED |
| M03.8 required checks, CODEOWNERS | BLOCKED (needs real owner handles) |
| M03.9 DoD | BLOCKED |

## M04 — Trust lock · HIGH · READY / BLOCKED

| Section | Status |
|---|---|
| M04.1 trust source / approvals | BLOCKED — digests must come from the owner, not from local copies |
| M04.2 lock design (all 13 fields) | DONE — `toolchains/LOCK.json`, entries `PENDING_OWNER_APPROVAL` |
| M04.3 schema/hardening | DONE — `schemas/toolchain-lock-v1.schema.json` + strict Python validation (duplicates, malformed hashes, traversal, unknown roles, unsupported schema, floating versions, credentials) |
| M04.4 verifier integration; lock version + digest in `VERIFY/2` | DONE |
| M04.5 Java policy | DONE (min 21; optional max / vendor allow-list) |
| M04.6 governance | Documented; enforcement via CODEOWNERS BLOCKED |
| M04.7 negative tests (10) | DONE |
| M04.8 DoD | BLOCKED on pins |

## M05 — Licence · HIGH · BLOCKED

No licence text was chosen or written (the checklist forbids inferring one). Done: decision
packet and third-party inventory (`docs/OWNER_DECISIONS.md`); SBOM records `NOASSERTION` until
a `LICENSE` with an SPDX identifier exists; release gate refuses to package without it and
rejects placeholder text; `MANIFEST.sha256` will cover it automatically.

## M06 — Security policy · MEDIUM · BLOCKED

No `SECURITY.md` with an invented contact was created. Done: complete content specification and
incident workflow in `docs/OWNER_DECISIONS.md`; release gate enforces presence and no
placeholders.

## M07 — SBOM · MEDIUM · READY (draft published)

DONE: SPDX 2.3 generator (`tools/sbom.py`), deterministic, from version-controlled metadata,
atomic write, local-path/credential leak check, structural validation, consistency with VERSION,
LICENSE and lock; refuses a release SBOM with unapproved pins. `sbom/iOS735_LCTL-0.2.0.spdx.json`
is published as **DRAFT** (toolchain hashes and licences `NOASSERTION`). Validation against the
official SPDX JSON schema and vulnerability-scanning policy: owner/CI choice (documented).

## M08 — Signing / provenance · MEDIUM · READY / BLOCKED

DONE: deterministic ZIP, in-toto v1 / SLSA v1 provenance binding archive, manifest, lock,
evidence, SBOM and JAR digests; Ed25519 sign/verify; refusal rules (open gate, failed verifier,
candidate, key inside repo, subject mismatch); end-user verification instructions. Proven end to
end with a throwaway key: verify PASS; one-byte archive change, provenance edit and wrong signer
all rejected; two packagings byte-identical. BLOCKED: the owner signing identity and its public
channel.

## M09 — JSON Schemas · LOW–MEDIUM · DONE (pending VERIFY/2 evidence)

DONE: `translation-map-v1`, `verify-v2`, `toolchain-lock-v1` (Draft 2020-12, strict), stdlib
validator with fail-on-unsupported-keyword, `--strict` cross-check with `jsonschema` +
meta-schema (both agree), valid fixture, 15 negative fixtures, compatibility policy,
`schemas/README.md`. The current map validates. The DoD item "current valid artifacts pass"
applies to real `VERIFY/2` once M02 produces it.

## Section 11 acceptance — current

11.1 repository integrity: **PASS** · 11.2 owner-toolchain verification: **BLOCKED** ·
11.3 governance/legal: **BLOCKED** · 11.4 supply chain: lock valid but unpinned, SBOM draft —
**BLOCKED** · 11.5 machine-readable contracts: **PASS** (map) · 11.6 authenticity: machinery
**PASS** (simulated identity), owner identity **BLOCKED**.
