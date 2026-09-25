# INV-64 application model — 4.3.0 missing-component remediation audit

**Release audited:** 4.3.0 (from 4.2.0 hardened, sha256 `3eaf8d5f…09ed2`)
**Governing checklist:** `source/INV64_v4.2.0_MISSING_COMPONENTS_CHECKLIST.md` (as received sha256 `733fce81…2182`; normalized digest in `provenance/master-source.json`)
**Audit date:** 2026-09-23 · **Work order:** junkyard `_YARDOFFICE/work-orders/inv64_application_model-20260923`

## Disposition

**NO_GO for production** (`evidence/EXIT_GATE.json`). Every item that can be
closed from inside the repository has been implemented with executable
enforcement and positive + negative tests; nothing is claimed complete on the
basis of prose or an external system that the repository bootstrap cannot
reproduce. What remains needs the owner or infrastructure outside the archive.

| Measure | 4.2.0 | 4.3.0 |
|---|---|---|
| Missing components (MC-01..40) COMPLETE | 0 | 0 |
| … IMPLEMENTED_LOCAL / PARTIAL / BLOCKED_EXTERNAL / GOVERNANCE_PENDING | — | 26 / 5 / 2 / 7 |
| Checklist items (750) DONE / PARTIAL / OPEN_EXTERNAL / OPEN_GOVERNANCE | — | 484 / 133 / 65 / 68 |
| INV-64-C### controls verified / partial / missing | 11 / 27 / 62 (SATISFIED/PARTIAL/MISSING) | 77 / 23 / 0 — no row downgraded |
| Tests | 14 standalone | 88 standalone (normal and `-O`) + 4 pk_core integration (fail/skip by design) |

## Method

1. Chop-shop yard check: the yard office on this computer holds only `work-orders/` (no engine, ledger or map), so the standard `ledger recall` / `yard_query` steps could not run (degraded mode, as in the INV-44 and INV-36 work orders). The closest proven parts were the owner's own INV-44 v4.3.0 remediation (same series, same checklist shape): `audit_log.py`, `provenance.py` and the `release_gate.py` structure were adapted (THIRD-PARTY-NOTICES.md). Everything else is build-new.
2. Each MC section was converted into code + tests where it is a runtime control, and into machine-checked records (JSON validated by `tools/governance_check.py`) where it is governance.
3. Every evidence producer writes `PK_APP_*` JSON; the exit gate aggregates them with digests (`tools/run_evidence.py`).
4. The 750 items were classified by `tools/build_ledger.py`: a disclosed keyword rule (owner/approval/drill ⇒ OPEN_GOVERNANCE; pk_core/real systems/runners/managed keys ⇒ OPEN_EXTERNAL; CI-only ⇒ PARTIAL) plus 59 individually reviewed overrides. A random sample of DONE items was re-read against the artifacts before release.

`CHECKLIST.json` itself is left byte-identical (it is the pk_core-consumed requirement list); its 4.3.0 status lives in the generated `evidence/REQUIREMENTS_MATRIX.json` and `REQUIREMENTS_TRACEABILITY.md`.

## Defects found by this pass (all fixed, all with regression tests)

1. Deep JSON nesting raised `RecursionError` from `json.loads` (4.2.0) — escaped the documented `ValueError` contract; any caller catching `ValueError` crashed. Fixed by a linear pre-scan + decoded-depth check (`MAX_DEPTH = 64`).
2. Inline credentials were accepted and became part of the canonical identity (4.2.0).
3. Validation messages echoed credential-like identifiers (found by the new fuzzer, seed 64 case 1304).
4. Audit `audit.loss` marker was skipped when the buffer was full at recovery (fault scenario f07).
5. Submit registered state before its audit record was durable (same class as INV-44 defect 1).
6. Overlay `set`/`unset` of the wrong type raised `TypeError` instead of a typed refusal.
7. Collection ceilings (10,000) are unreachable under the 1 MiB byte ceiling for realistic entries — documented, benchmarks adjusted.

## Component status

Item counts are DONE/PARTIAL/OPEN_EXTERNAL/OPEN_GOVERNANCE. Full lists: `COMPONENTS_STATUS.json`, `evidence/ITEM_LEDGER.json`.

| MC | Sev | Component | Status | Items | First blocker |
|---|---|---|---|---|---|
| MC-01 | High | Restore and govern the original `MASTER.md` master-prompt/workflow sou | **PARTIAL** | 13/2/1/2 | MASTER.md (series v4.0.0 source corpus) not supplied — recorded BLOCKED_EXTERNAL in provenance/master-source.json |
| MC-02 | Critical | Provide a resolvable/bundled `pk_core` dependency and runnable full co | **BLOCKED_EXTERNAL** | 8/3/8/0 | pk_core source, version and digest not supplied: no pin, test_component fails/skips by design |
| MC-03 | High | Add installable package and dependency metadata | **IMPLEMENTED_LOCAL** | 14/2/3/0 | build isolation not exercised (no package index in the build session; tools/build_check.py uses it when present) |
| MC-04 | High | Assign accountable ownership, escalation path, and approved ADR | **GOVERNANCE_PENDING** | 0/4/1/12 | all six accountable roles have assignee=null |
| MC-05 | High | Complete SHALL-level semantic specification | **IMPLEMENTED_LOCAL** | 17/0/0/2 | normative specification not yet approved by architecture-review-board |
| MC-06 | High | Formalize typed contracts for validation/canonical responses and WIT/R | **IMPLEMENTED_LOCAL** | 18/0/1/0 | WIT world is contract-only (no Wasm build); cross-language fixtures N/A until a second implementation exists |
| MC-07 | Critical | Define and enforce authentication at every submit/control-plane/provid | **IMPLEMENTED_LOCAL** | 19/0/0/0 | production issuers, trust roots, mTLS certificates and break-glass identities not provisioned |
| MC-08 | Critical | Implement authorization and explicit least-privilege capability model | **IMPLEMENTED_LOCAL** | 13/1/1/4 | pk_core authority review impossible (pk_core absent) |
| MC-09 | High | Specify timeout, cancellation, retry, idempotency, backpressure, and p | **IMPLEMENTED_LOCAL** | 19/0/0/1 | client guidance published but not yet exercised by a real client |
| MC-10 | Critical | Build adjacent-layer integration harnesses for INV-10, INV-63, INV-65, | **BLOCKED_EXTERNAL** | 14/1/4/0 | real INV-10/INV-63/INV-65/INV-66 implementations not in the archive; only the emulated profile runs |
| MC-11 | High | Pin the exact approved OAM specification/implementation version | **IMPLEMENTED_LOCAL** | 18/0/0/0 | baseline selection needs ADR-0001 approval |
| MC-12 | High | Implement site/environment overlays and configuration provenance | **IMPLEMENTED_LOCAL** | 18/0/0/1 | no network API for overlay submission in this package; author authorization is a caller hook |
| MC-13 | High | Add atomic configuration activation and tested automatic/operator roll | **IMPLEMENTED_LOCAL** | 16/0/2/1 | release-drill on production mechanism not performed (only CI drill) |
| MC-14 | Critical | Enforce secret-material exclusion and diagnostic redaction | **IMPLEMENTED_LOCAL** | 15/2/1/1 | allowlist entries need owner review |
| MC-15 | Critical | Implement artifact signature, digest, provenance, and approved-version | **IMPLEMENTED_LOCAL** | 14/0/1/4 | no managed signer / trust anchors provisioned; policy root keys not issued |
| MC-16 | Critical | Enforce tenant/workload isolation at integration/runtime boundaries | **IMPLEMENTED_LOCAL** | 18/0/0/0 | isolation profile is logical only (REG-005) |
| MC-17 | Critical | Implement transport/storage encryption, managed key rotation, and trus | **IMPLEMENTED_LOCAL** | 14/3/1/1 | KMS/HSM key provider and certificates not provisioned |
| MC-18 | Critical | Add tamper-evident security audit event emitter/ledger | **IMPLEMENTED_LOCAL** | 18/0/1/0 | external WORM anchor store and retention owner not provisioned |
| MC-19 | High | Add fuzzing, property-based, parser-differential, and adversarial reso | **IMPLEMENTED_LOCAL** | 15/2/0/1 | scheduled long campaign defined in CI but not yet run on a runner; no coverage-guided engine (stdlib-only) |
| MC-20 | High | Define complete failure model and prove recovery with fault injection | **IMPLEMENTED_LOCAL** | 16/0/1/2 | recovery objectives need owner approval |
| MC-21 | High | Establish reproducible performance, resource, and power baselines | **PARTIAL** | 11/3/3/2 | reference benchmark environment not designated |
| MC-22 | High | Analyze serialization/copy/hop costs, define capacity model, saturatio | **IMPLEMENTED_LOCAL** | 15/2/0/2 | approved baseline on the reference environment does not exist yet |
| MC-23 | High | Expose health, readiness, version, configuration, dependency, and capa | **IMPLEMENTED_LOCAL** | 17/0/1/0 | no HTTP probe endpoint (library API only); orchestration wiring is the host's |
| MC-24 | High | Implement metrics, structured logs, trace propagation, and safe diagno | **IMPLEMENTED_LOCAL** | 16/3/0/0 | no exporter (OTel/Prometheus endpoint) bundled; exposition text only |
| MC-25 | Medium | Add decision explainability and release-lineage/infrastructure-graph c | **IMPLEMENTED_LOCAL** | 19/0/0/0 | no live infrastructure-graph source; graph_state reported 'unknown' |
| MC-26 | Medium | Define telemetry retention/sampling/privacy/export policy, dashboards, | **GOVERNANCE_PENDING** | 0/16/1/2 | alert routing never tested end-to-end to a real pager |
| MC-27 | High | Create cross-platform/runtime/provider/protocol compatibility matrix a | **PARTIAL** | 10/5/3/1 | only linux-x86_64 / CPython 3.11 executed in this pass; other matrix rows defined, not run |
| MC-28 | High | Add concurrency/race, soak/burst/fleet-scale, and disaster/partition/r | **IMPLEMENTED_LOCAL** | 13/4/2/0 | extended soak/fleet profile scheduled but not run |
| MC-29 | Critical | Create local machine-readable acceptance evidence and formal productio | **IMPLEMENTED_LOCAL** | 14/1/1/3 | gate artifact signed only by ephemeral key; current verdict NO_GO |
| MC-30 | High | Maintain supported-version compatibility matrix | **IMPLEMENTED_LOCAL** | 10/5/3/0 | matrix rows beyond linux-x86_64/py3.11 lack run evidence (MC-27) |
| MC-31 | High | Define vulnerability response, patching, and end-of-life SLAs | **GOVERNANCE_PENDING** | 0/14/3/2 | reporting channel and security contact unassigned |
| MC-32 | Medium | Define backup, restore, migration, and reconstruction applicability/pr | **IMPLEMENTED_LOCAL** | 17/2/0/0 | RPO/RTO targets need owner approval |
| MC-33 | Medium | Create complete day-0, day-1, and day-2 operator runbooks | **GOVERNANCE_PENDING** | 0/12/2/4 | runbooks not yet executed by an operator in a drill |
| MC-34 | High | Define incident severity, paging, escalation, containment, and recover | **GOVERNANCE_PENDING** | 0/9/6/4 | roles unassigned; paging paths and tabletop exercises not performed |
| MC-35 | Medium | Establish recurring access, policy, dependency, configuration, and arc | **GOVERNANCE_PENDING** | 0/12/0/6 | no review performed yet (first due 2026-10-22) |
| MC-36 | Medium | Create exception/waiver/technical-debt/deprecation register | **IMPLEMENTED_LOCAL** | 13/2/0/4 | register entries have owner_role but no named owner |
| MC-37 | High | Add CI workflow for standalone, integration, security, compatibility,  | **PARTIAL** | 8/3/7/1 | workflow never executed on a CI runner; branch protection is a repository setting |
| MC-38 | Medium | Add explicit distribution license, NOTICE, and SPDX metadata | **GOVERNANCE_PENDING** | 0/15/1/2 | distribution license not chosen by the owner |
| MC-39 | High | Generate SBOM, checksums, signatures, and release provenance artifacts | **PARTIAL** | 11/3/5/0 | release signed with an ephemeral key; managed signer required (REG-003) |
| MC-40 | High | Define canary/staged rollout and perform tested rollback drill | **IMPLEMENTED_LOCAL** | 13/2/1/3 | no production fleet drill |

## Verification results (this build container: Linux x86_64, CPython 3.11.15, cryptography 46.0.7)

| Evidence | Result |
|---|---|
| TESTS.json / TESTS_O.json | FAIL by design: 88 standalone pass; `test_component` 1 fail + 3 skips (no pk_core) |
| SOURCE_CHECK.json | PASS (digest, extraction drift, 40/40 clauses mapped, 750/750 items in ledger) |
| PREFLIGHT.json (certification) | FAIL: pk_core absent / unpinned |
| BUILD.json | PASS: wheel + sdist build (PEP 517 hooks, no isolation offline), fresh-venv installs equivalent, `pip check` clean |
| SECRET_SCAN.json | PASS (20 reviewed synthetic-probe suppressions) |
| FUZZ.json | PASS: 3,000 cases + regressions, 0 findings |
| FAULTS.json | PASS 13/13, recovery < 1 s |
| STRESS.json | PASS 7/7 (ci profile) |
| PERF_GATE.json | PASS (absolute thresholds; baseline is this container, not a reference env) |
| INTEGRATION.json | PASS 12/12 (emulated adjacent layers) |
| INTEGRATION_REAL.json | FAIL: real adjacent implementations not available |
| ROLLBACK_DRILL.json | PASS (auto + manual + idempotent) |
| AUDIT_VERIFY.json | PASS (end-to-end smoke ledger sealed and verified) |
| GOVERNANCE.json | FAIL: owners unassigned, ADR-0001 proposed, license pending |
| RELEASE_VERIFY.json | FAIL: signatures verify, but the key is ephemeral (no signer identity) |

## Owner actions that unblock the gate

1. Supply `pk_core` (source or release artifact) → record version + digest in `compatibility.json`; rerun `tools/run_evidence.py` with `PK_CORE_PATH`; pass `pk_core gate` output to the gate.
2. Assign the six roles in `ops/owners.json`; approve or amend ADR-0001; choose the license (LICENSING.md).
3. Provision a managed signer (KMS/HSM/OIDC keyless), trust-policy root keys, issuer keys, WORM audit store.
4. Run `.github/workflows/ci.yml` on real runners; designate the performance reference runner and re-baseline.
5. Provide or point to the real INV-10/63/65/66 implementations for the `real` integration profile.
6. Hold the first access/policy/dependency reviews, a security + availability tabletop, and an operator runbook drill; record them in `ops/REVIEWS.json`.
7. Supply `MASTER.md` if it still exists, or confirm that the governing checklist supersedes it.

---

## Appendix — 4.2.0 audit (unchanged, for history)

### INV-64 application model — post-hardening audit (4.2.0)

**Release audited:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** files present in this archive only. External `pk_core` behavior was not available for inspection or execution.

## Release disposition

The standalone manifest parser/validator/canonicalizer is internally testable and passes its local regression suite. The repository is **not yet a self-contained production release** because the integration framework is absent and multiple checklist controls remain partial or missing. `REQUIREMENTS_TRACEABILITY.md` records all 100 checklist items without treating contract prose as implementation evidence.

## Defects fixed in 4.2.0

1. **False archive claim:** README referenced a verbatim `MASTER.md` corpus that is not present. The claim is removed and the source corpus is now an explicit gap.
2. **False-green integration test behavior:** all conformance tests previously skipped when `pk_core` was missing, allowing an `OK (skipped=3)` result. A non-skipped dependency assertion now exposes the missing integration dependency.
3. **Validator early-exit behavior:** malformed collection sections previously stopped validation at the first section error, contradicting the "report every validation error at once" requirement. Section errors are now aggregated and malformed members are isolated.
4. **Unstructured validation failures:** stable `code/path/message` issues are now available through `ValidationIssue` and cataloged in `ERRORS.md`; the legacy string API is retained.
5. **Unsafe raw JSON ambiguities:** raw parsing now rejects duplicate object keys, non-finite values, invalid UTF-8, and payloads over 1 MiB.
6. **Unbounded decoded collections:** component/provider/link/trait counts now have defensive ceilings, and validation work is capped for already-decoded oversized lists.
7. **Canonicalization of invalid input:** canonical identity now fails closed on semantically invalid manifests rather than hashing them.
8. **Weak canonical byte definition:** canonical JSON now has deterministic UTF-8 encoding, sorted object keys, compact separators, finite-number enforcement, section normalization, and no mutation of caller input.
9. **Core logic coupled to privileged integration:** parser/validator/canonicalization moved to `manifest.py`, and package integration exports are lazy-loaded; the ordinary manifest API now imports without `pk_core` and has no filesystem, network, device, process, or credential dependency.
10. **No formal manifest schema/examples:** `schema/app-v1.schema.json`, `SCHEMA.md`, and valid/invalid fixtures are now included.
11. **No parser security notes:** `SECURITY.md` now records the untrusted-input boundary, implemented defenses, and residual controls.
12. **Version drift:** release metadata and tests are aligned at `4.2.0`.

## Verification performed

- `python tests/test_manifest.py` — **14/14 PASS** on Python 3.13.5.
- `python -m compileall -q .` — **PASS**.
- `python tests/test_component.py` — **FAILS visibly because `pk_core` is absent**; three integration tests are skipped after the dependency failure is recorded. This is intentionally no longer a false-green run.
- JSON Schema artifact parses as JSON and its key constants/limits are regression-tested.

## Missing component catalog

The following are the concrete missing components after the 4.2.0 fixes. Checklist IDs are representative mappings; the full per-item mapping is in `REQUIREMENTS_TRACEABILITY.md`.

| ID | Missing component | Severity | Checklist mapping |
|---|---|---:|---|
| MC-01 | Original `MASTER.md` master-prompt/workflow source corpus | High | provenance of the claimed source set |
| MC-02 | Resolvable/bundled `pk_core` integration dependency and runnable full conformance environment | Critical | C030, C040, C082, C090, C100 |
| MC-03 | Installable package/dependency metadata (`pyproject.toml` or equivalent) defining Python/support/dependency requirements | High | C031, C040, C093 |
| MC-04 | Named accountable owner, escalation path, and approved architecture decision record | High | C009-C010 |
| MC-05 | Complete SHALL-level semantic specification: platform tiers, outcomes, lifecycle, compatibility, quotas, disconnect behavior, and precedence | High | C011-C019 |
| MC-06 | Formal typed contracts for validation/canonical responses and any WIT/RPC/control-plane bindings | High | C021-C022, C026-C028 |
| MC-07 | Authentication model for every submit/control-plane/provider boundary | Critical | C023, C044 |
| MC-08 | Authorization and explicit capability model with least privilege | Critical | C024, C042-C043 |
| MC-09 | Timeout, cancellation, retry, idempotency, backpressure, and peer-version negotiation contract | High | C025, C027, C053 |
| MC-10 | Adjacent-layer integration harness/fixtures for INV-10, INV-63, INV-65, and INV-66 | Critical | C030, C083 |
| MC-11 | Exact approved/pinned OAM/specification or implementation version | High | C031, C093 |
| MC-12 | Site/environment configuration overlay model plus configuration provenance/author/activation metadata | High | C035-C036 |
| MC-13 | Atomic activation/transaction and tested automatic/operator rollback mechanism | High | C037-C038, C092 |
| MC-14 | Secret-material exclusion/redaction policy and enforcement for extension configuration/diagnostics | Critical | C039, C075 |
| MC-15 | Artifact signature, digest, provenance, and approved-version verification pipeline | Critical | C045 |
| MC-16 | Enforced tenant/workload isolation controls at the integration/runtime boundary | Critical | C046 |
| MC-17 | Transport/storage encryption, managed key rotation, and trust-service-outage behavior | Critical | C047-C048 |
| MC-18 | Tamper-evident security audit event emitter/ledger implementation in the deliverable | Critical | C049, C090 |
| MC-19 | Fuzzing/property-based/parser-differential and adversarial security/resource-exhaustion test suites | High | C050, C085, C087 |
| MC-20 | Full failure model, health/stall detection, failover/degraded/restart/replay/split-brain semantics, and fault injection | High | C051-C060 |
| MC-21 | Reproducible performance/resource/power baselines and p50/p95/p99/worst-case thresholds | High | C061-C064, C068 |
| MC-22 | Serialization/copy/hop analysis, capacity model, saturation signals, and measured performance-regression release gate | High | C065-C070 |
| MC-23 | Health/readiness/config/dependency/capability status surface | High | C071 |
| MC-24 | Metrics, structured logs, trace propagation, and safe diagnostics implementations | High | C072-C075 |
| MC-25 | Decision explainability view plus release-lineage/infrastructure-graph correlation | Medium | C076-C078 |
| MC-26 | Telemetry retention/sampling/privacy/export policy, dashboards, and differentiated alerts | Medium | C079-C080 |
| MC-27 | Cross-platform/runtime/provider/protocol compatibility test matrix | High | C084 |
| MC-28 | Concurrency/race, benchmark/soak/burst/fleet-scale, and disaster/partition/reconnect test suites | High | C086, C088-C089 |
| MC-29 | Local machine-readable acceptance evidence and formal production exit-gate artifact | Critical | C090, C100 |
| MC-30 | Supported-version compatibility matrix for the application model and adjacent dependencies | High | C093 |
| MC-31 | Vulnerability response, patching, and end-of-life SLAs | High | C094 |
| MC-32 | Formal state backup/restore/migration/reconstruction applicability procedure | Medium | C095 |
| MC-33 | Full day-0/day-1/day-2 operator runbooks beyond the current outline | Medium | C096 |
| MC-34 | Incident severity/paging/escalation/containment/recovery procedure | High | C097 |
| MC-35 | Recurring access/policy/dependency/configuration/architecture review process | Medium | C098 |
| MC-36 | Exception/waiver/technical-debt/deprecation register with owners and expiry dates | Medium | C099 |
| MC-37 | CI workflow that runs standalone tests plus full integration conformance in an environment where `pk_core` is present | High | C070, C081-C090, C100 |
| MC-38 | Explicit distribution license/NOTICE/SPDX metadata | Medium | release/supply-chain hygiene |
| MC-39 | SBOM/checksum/signature/provenance artifacts for the packaged release | High | C045, C090, supply-chain hygiene |
| MC-40 | Canary/staged rollout procedure and tested rollback drill | High | C092 |

## Residual correctness notes

- `schema/app-v1.schema.json` intentionally cannot express cross-reference constraints such as “link target must be a declared name”; those remain semantic checks in `manifest.py`.
- Unknown extension fields are permitted and are included in canonical identity. A future extension-governance policy should define which extension namespaces are allowed and which values are secret-bearing.
- Defensive limits in `manifest.py` are implementation ceilings, not tenant quotas/fairness policy.
- The archive does not contain enough evidence to substantiate the prior changelog statement that “All 100 requirements [are] satisfied.” The 4.2.0 traceability matrix supersedes that assertion for this standalone archive.
