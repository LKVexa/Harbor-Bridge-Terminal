# INV-25 4.3.0 — execution status of the missing-components checklist

Source: `INV25_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md`, executed 2026-09-23 against
`inv25_microvm_devices_v4.2.0_hardened.zip`. Following the checklist's certification rule, an item is
**Done** only where an executable control, test or reproducible artifact now exists in this repository.
Nothing here fabricates an approval, an owner, a peer result, a signing key or the historical `MASTER.md`.

**Headline:** 87 tests pass (normal and `python -O`; 3 pk_core tests skipped because pk_core is not available).
RTM covers C001–C100 with zero linkage errors. The standalone gate is reproducible and verifies, and its
honest verdict is **NO_GO**: 82 PASS / 11 BLOCKED / 4 EXTERNAL / 3 N/A, with 18 rows needing human or
external input.

| # | Work item | Status | Delivered | Still needed (owner input) |
|---|---|---|---|---|
| 0 | Program-wide rules | Partial | Machine-readable results (gate, evidence, bench, manifest), `python -O` runs, no local paths (checked by release tool), raw log + summary, digests | Work-item IDs/dates/owners in a tracker; independent reviewers |
| 1 | pk_core | **Blocked** | `pk_bootstrap.py` (import + symbol + version checks, PK_CORE_PATH dev-only, machine-readable exit 3), lazy package import, `[pk]` extra, CI `pk-integration` job | pk_core source, exact version + digest; confirm the proposed `>=4.0,<5.0` range |
| 2 | MASTER.md | Blocked (decision) | `docs/master-corpus.md`: proposed archival-only; no code reads it; README corrected | Owner approves classification (W-0007) or supplies the authentic file |
| 3 | Gate evidence | Done (standalone) | `tools/gate.py run/verify`: 100 chained records, file digests, source-tree digest, stale-gate detection, schema-validated, optional HMAC signature | pk_core-produced evidence; org signing key |
| 4 | Manifest / packaging | Done | `pyproject.toml`, `requirements.lock`, `tools/release.py`: reproducible archive (built twice, byte-identical), version-sync check, manifest; wheel built and installed in a clean venv | Built with local setuptools 68 because the package index could not be reached; re-check with the pinned 75.8.0 |
| 5 | CI / release | Done (unexercised) | `.github/workflows/ci.yml`: 4 Pythons × {normal, -O}, RTM, pk job, scheduled fuzz + pip-audit, protected release job (build → gate `--require-go` → verify → provenance attestation) | Check the pinned action SHAs; set up branch protection, release environment and secrets; first run |
| 6 | Ownership / escalation | Partial | `docs/ownership.md`, `CODEOWNERS`, `docs/incident-response.md` (role-based) | Named holders, on-call rota, channels (W-0001) |
| 7 | ADR | Partial | `ADR/ADR-0001` (VIRTIO 1.2 §5.1/§5.2, register semantics, rejected alternatives) — status *Proposed* | Architecture + security approval (W-0002) |
| 8 | RTM | Done | `governance/RTM.json/.md`, `tools/rtm.py` checks IDs, paths, symbols and test discoverability; the gate fails on linkage errors | Approver names for exemptions |
| 9 | Authentication | Done (reference) | `authz.Verifier` + 7 negative-test classes, anti-replay, clock fail-closed | Swap in the estate identity provider behind the same interface |
| 10 | Authorization | Done | 10 capabilities, deny-by-default, env scoping, widen capability, proposer≠approver, break-glass | — |
| 11 | Error contract | Done | `errors.py`, schema, a test for every code, redaction | — |
| 12 | Compatibility | Partial | `compat.negotiate` (fail closed, security floor), matrix, pk_core startup gate | Pin peer versions; mixed-version tests with real peers |
| 13 | Ceilings | Done | Enforced limits with boundary tests (limit−1 / limit / limit+1), payload pre-parse bound, rate limit, queue cap | Owner sign-off on the values |
| 14 | Integration tests | External | Pinned contract fixtures + 8 scenarios (accept, reject, missing backend, policy narrowing and outage, disable, snapshot drift, optional INV-43) | Peers run the same scenarios against their real implementations (W-0008) |
| 15 | virtio pins | Partial | VIRTIO 1.2 declared in ADR; surface-change rules | VMM/backend/kernel versions, image digests |
| 16 | Activation provenance | Done | `PK_DEVICE_CONFIG_ACTIVATION/1`, canonical digest, append-only history, `explain()` | — |
| 17 | Atomic txn / rollback | Done | CAS, fsync + atomic replace, crash injection at 3 points, idempotent replay, rollback only to known-good digests | Automatic rollback triggers belong to the deployment tooling |
| 18 | Artifact verification | Done (reference) | `provenance.TrustPolicy` (digest before parse, binding, approved versions, revocation, scheme fail-closed), audited | Organisational asymmetric signer (W-0005) |
| 19 | Audit | Done | Hash chain, edit/delete/insert/reorder detection, O_APPEND sink, secret-field refusal, sink-down ⇒ mutations refused | WORM sink and retention in production |
| 20 | Fuzz / adversarial | Done | Deterministic 4-seed fuzz (3k in CI, 40k run this pass, 200k scheduled) plus a 9-case regression corpus | Coverage-guided fuzzing (e.g. atheris) as an option |
| 21 | Fault injection | Done | Covers audit/dependency/clock/disk/crash/tampered state, with a failure model doc | Remote partition mode doesn't exist yet |
| 22 | Performance | Partial | `bench.py`: raw samples, host profile, p50–p99, memory, enforcement; baseline recorded | Approve thresholds on a pinned host (W-0003) |
| 23 | Telemetry | Partial | health/ready, metrics, error counts, correlation IDs, explain, policy doc, dashboards and alerts specified | Wire up the exporter and monitoring stack (C080) |
| 24 | Cross-arch matrix | Blocked | Matrix + policy; linux/x86_64 exercised | arm64 / hypervisor hardware evidence |
| 25 | Concurrency | Done | Model documented; one-winner CAS, torn-read check, nonce race | Multi-process store is out of scope |
| 26 | Acceptance / exit gate | Partial | Policy doc + gate with GO/CONDITIONAL_GO/NO_GO rules, approvals register, previous-gate link, stale-gate check | Approvals, signing, pk_core |
| 27 | Rollout / disable | Partial | Rollback + emergency disable tested, stage model | Deployment tooling that consumes the gate |
| 28A | Vuln / EOL | Done (policy) | `SECURITY.md`, `docs/vulnerability-eol.md`, scheduled pip-audit | Contact channel; approve the targets |
| 28B | Recurring review | Partial | Cadence doc + register + overdue check | Hold and record the first review |
| 28C | Waiver register | Done | 9 proposed waivers, and the gate only honours approved, unexpired ones | Approvers |
| 28D | License / SBOM | Partial | CycloneDX SBOM, manifest digests, THIRD-PARTY-NOTICES | **Choose a licence** (not invented); provenance attestation runs in CI |
| A1–A7 | External peers | External | Boundaries and fixtures defined in `conformance/integration/peer_contracts.py` | Each peer's own readiness checklist |
| C | Final exit checklist | Not met | — | Everything marked Blocked/Partial above |

## Defect found and fixed during implementation
The first version of the commit path could let memory and disk disagree after a late failure. Now the atomic
durable replace is the only commit point, and any failure after the audit event is followed by a
`config.activation_failed` event. Regression coverage: `PersistenceAndFaultTest.test_crash_points_leave_old_state`.
