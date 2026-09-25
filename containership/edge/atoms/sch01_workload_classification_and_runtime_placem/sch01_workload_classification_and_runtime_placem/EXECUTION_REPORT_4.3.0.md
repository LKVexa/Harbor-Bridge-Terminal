# SCH-01 4.3.0 — Execution report for the v4.2.0 Missing-Component Implementation Checklist

Applied by the junkyard chop shop, 2026-09-23. Work order `SCH01-v430-missing-components-20260923`.

## Verdict

**Production exit gate: NO_GO** (32 of 77 gate checks fail). This is the honest result, not a shortfall of the build: every
definition of done requires a named accountable owner and approver, and none exists; MASTER.md is absent; eight adjacent
elements are not bundled.

## What the checklist items show

All 1,758 checkboxes stay **unticked** (the checklist's own backlog rule: planning never closes an item). Each item has a state in
`evidence/CHECKLIST_STATUS.json`:

| State | Items |
|---|---:|
| BLOCKED_BY_EXIT_GATE | 10 |
| BLOCKED_EXTERNAL | 120 |
| BLOCKED_HUMAN | 206 |
| BLOCKED_SOURCE | 23 |
| DRAFTED_UNAPPROVED | 72 |
| EVIDENCED_PARTIAL_EXTERNAL_OPEN | 74 |
| EVIDENCED_UNREVIEWED | 479 |
| NOT_EVIDENCED | 774 |
| **Completion claims** | **0** |

`EVIDENCED_UNREVIEWED` is a lower bound: an item only gets it when it shares at least two content words with the test classes
and artifacts actually cited for its component. The 774 `NOT_EVIDENCED` items are mostly generic definition-of-done lines
(D02–D07 repeated per component) and fine-grained tasks the build did not address in words. A human reviewer may find some are met.
The test cannot create a pass.

## Components (registry: `tools/registry.py`)

{'BLOCKED_SOURCE': 1, 'IMPLEMENTED_TESTED': 43, 'DRAFTED_UNAPPROVED': 9, 'BLOCKED_EXTERNAL': 15}

| ID | State | Main artifacts | Still blocking |
|---|---|---|---|
| MC-01 | BLOCKED_SOURCE | `tools/verify_master_provenance.py`, `evidence/master_provenance.json` | canonical MASTER.md not supplied; verifier reports EVIDENCE_GAP; waiver needs an approver |
| MC-02 | IMPLEMENTED_TESTED | `pyproject.toml`, `requirements.lock` | wheel build/sign on a release host not run |
| MC-03 | DRAFTED_UNAPPROVED | `governance/OWNERS.json` | owner, backup, escalation and on-call are UNASSIGNED |
| MC-04 | DRAFTED_UNAPPROVED | `docs/adr/ADR-0001-governed-placement-path.md`, `docs/adr/ADR-0002-fencing-and-journal.md`, `docs/adr/ADR-0003-fail-closed-isolation.md` | ADRs are PROPOSED; approver UNASSIGNED |
| MC-05 | DRAFTED_UNAPPROVED | `governance/SHALL.json` | requirements need owner sign-off |
| MC-06 | IMPLEMENTED_TESTED | `tools/rtm.py`, `evidence/RTM.json` | RTM rows carry owner UNASSIGNED |
| MC-07 | IMPLEMENTED_TESTED | `model.py`, `scheduler.py` | context semantics need owner approval |
| MC-08 | IMPLEMENTED_TESTED | `lifecycle.py` | — |
| MC-09 | IMPLEMENTED_TESTED | `lifecycle.py`, `docs/COMPATIBILITY.md` | support policy unapproved |
| MC-10 | IMPLEMENTED_TESTED | `allocators.py` | quota values are policy decisions; none approved |
| MC-11 | IMPLEMENTED_TESTED | `scheduler.py`, `model.py` | — |
| MC-12 | IMPLEMENTED_TESTED | `scheduler.py` | latency budget value PROPOSED |
| MC-13 | IMPLEMENTED_TESTED | `scheduler.py` | no GAP-03 topology graph (EXT-06); zone-level only |
| MC-14 | IMPLEMENTED_TESTED | `scheduler.py`, `model.py` | jurisdiction policy source not bound |
| MC-15 | IMPLEMENTED_TESTED | `allocators.py` | MIG/partition health from real devices not bound |
| MC-16 | IMPLEMENTED_TESTED | `config.py` | signing key is test-generated; no policy owner |
| MC-17 | IMPLEMENTED_TESTED | `schemas.py`, `schemas/`, `tools/gen_schemas.py` | — |
| MC-18 | IMPLEMENTED_TESTED | `errors.py` | — |
| MC-19 | IMPLEMENTED_TESTED | `security.py` | no real IdP/mTLS; HMAC mechanism only |
| MC-20 | IMPLEMENTED_TESTED | `security.py` | role bindings to real principals absent |
| MC-21 | IMPLEMENTED_TESTED | `resilience.py` | — |
| MC-22 | IMPLEMENTED_TESTED | `config.py` | — |
| MC-23 | IMPLEMENTED_TESTED | `config.py` | — |
| MC-24 | BLOCKED_EXTERNAL | `security.py` | provider interface + fail-closed tested; no KMS/HSM bound |
| MC-25 | BLOCKED_EXTERNAL | `security.py` | HMAC evidence verifier only; TPM/SEV/TDX quote verification is GAP-02/EXT-04 |
| MC-26 | IMPLEMENTED_TESTED | `model.py`, `scheduler.py` | — |
| MC-27 | IMPLEMENTED_TESTED | `audit.py` | sealing key test-generated; external anchoring of head absent |
| MC-28 | IMPLEMENTED_TESTED | `tests/test_security.py` | side channels and escape are out of scope of a decision function; not tested |
| MC-29 | IMPLEMENTED_TESTED | `resilience.py` | thresholds PROPOSED |
| MC-30 | IMPLEMENTED_TESTED | `resilience.py` | failover across instances needs EXT consensus |
| MC-31 | IMPLEMENTED_TESTED | `state.py` | — |
| MC-32 | BLOCKED_EXTERNAL | `state.py` | single-host file fencing tested; multi-host linearizable store not bound |
| MC-33 | IMPLEMENTED_TESTED | `scheduler.py` | — |
| MC-34 | IMPLEMENTED_TESTED | `tests/test_resilience_state.py` | partition/controller loss only simulated in-process |
| MC-35 | IMPLEMENTED_TESTED | `tools/bench.py`, `evidence/bench.json` | power/network/storage not measured |
| MC-36 | IMPLEMENTED_TESTED | `tools/bench.py` | thresholds PROPOSED, no approver |
| MC-37 | IMPLEMENTED_TESTED | `scheduler.py` | — |
| MC-38 | IMPLEMENTED_TESTED | `telemetry.py` | no exporter endpoint bound |
| MC-39 | IMPLEMENTED_TESTED | `telemetry.py` | — |
| MC-40 | IMPLEMENTED_TESTED | `telemetry.py` | no trace backend bound |
| MC-41 | IMPLEMENTED_TESTED | `scheduler.py` | no UI; API only |
| MC-42 | DRAFTED_UNAPPROVED | `telemetry.py`, `docs/TELEMETRY_GOVERNANCE.md` | dashboards/alerts defined as code-free spec; not deployed |
| MC-43 | IMPLEMENTED_TESTED | `tests/test_contracts_integration.py` | — |
| MC-44 | BLOCKED_EXTERNAL | `adapters.py` | fakes only; real PLN/GAP/INV elements absent |
| MC-45 | BLOCKED_EXTERNAL | `ci/ci.sh`, `docs/COMPATIBILITY.md` | one platform executed (Linux x86_64, CPython 3.11); matrix not run |
| MC-46 | IMPLEMENTED_TESTED | `tests/test_contracts_integration.py` | seeded stdlib fuzz; no coverage-guided fuzzer |
| MC-47 | IMPLEMENTED_TESTED | `tests/test_resilience_state.py` | multi-host split-brain not testable here |
| MC-48 | BLOCKED_EXTERNAL | `tools/bench.py` | no soak/burst/fleet-scale environment |
| MC-49 | IMPLEMENTED_TESTED | `tools/evidence_bundle.py`, `evidence/RELEASE_EVIDENCE.json` | bundle unsigned by a release authority |
| MC-50 | DRAFTED_UNAPPROVED | `docs/policy/SUPPORT_AND_ERROR_BUDGET.md` | approver UNASSIGNED |
| MC-51 | IMPLEMENTED_TESTED | `canary.py` | not wired to a real deployment system |
| MC-52 | DRAFTED_UNAPPROVED | `docs/policy/VULNERABILITY_PATCH_EOL.md` | approver UNASSIGNED |
| MC-53 | IMPLEMENTED_TESTED | `state.py`, `docs/runbooks/RB-04-backup-restore.md` | drill on production storage not run |
| MC-54 | DRAFTED_UNAPPROVED | `docs/runbooks/` | drills not executed; commands untested on a real environment |
| MC-55 | DRAFTED_UNAPPROVED | `docs/policy/INCIDENT_RESPONSE.md` | paging tree UNASSIGNED |
| MC-56 | DRAFTED_UNAPPROVED | `governance/REVIEW_PROGRAM.json` | no review has occurred |
| MC-57 | IMPLEMENTED_TESTED | `governance/WAIVERS.json`, `tools/exit_gate.py` | register empty; no waiver approved |
| MC-58 | IMPLEMENTED_TESTED | `tools/exit_gate.py` | gate returns NO_GO by construction until owners/approvals exist |
| MC-59 | IMPLEMENTED_TESTED | `ci/ci.sh`, `ci/github-workflow.yml` | not executed on a hosted CI runner |
| MC-60 | BLOCKED_EXTERNAL | `sbom/sbom.cdx.json`, `RELEASE_SHA256SUMS.txt`, `LICENSE-STATUS.md` | license terms unknown - owner must choose; provenance unsigned |
| EXT-01 | BLOCKED_EXTERNAL | `tests/test_component.py` | pk_core not available; conformance tests skip |
| EXT-02 | BLOCKED_EXTERNAL | `adapters.py` | PLN-02 not bundled |
| EXT-03 | BLOCKED_EXTERNAL | `adapters.py` | PLN-05 not bundled |
| EXT-04 | BLOCKED_EXTERNAL | `adapters.py`, `security.py` | GAP-02 not bundled; hardware attestation absent |
| EXT-05 | BLOCKED_EXTERNAL | `adapters.py` | PLN-04 not bundled; enforcement unproven |
| EXT-06 | BLOCKED_EXTERNAL | `adapters.py` | GAP-03 not bundled |
| EXT-07 | BLOCKED_EXTERNAL | `adapters.py` | GAP-10 not bundled |
| EXT-08 | BLOCKED_EXTERNAL | `adapters.py` | INV-33 not bundled; reclamation unproven end-to-end |

## Build facts

- Python standard library only. No third-party runtime imports; `pk_core` stays optional (EXT-01).
- New modules: `errors, model, security, audit, config, lifecycle, resilience, state, telemetry, allocators, scheduler, schemas, adapters, canary`.
  `engine.py` and `contract.py` are unchanged. `engine.place` stays as the v1 contract.
- Tests: Ran 109 tests (2 pk_core tests skip: EXT-01). CI: all steps PASS on CPython 3.11.15 / Linux x86_64 (this is the only platform run; MC-45 is open).
- Benchmark (seeded, PROPOSED thresholds): engine p99 @1,000 nodes 14.7 ms; governed service path p99 @1,000 nodes
  23.5 ms with a journal fsync per decision. The result is `met_under_proposed_thresholds`, which is not an approved pass.

## Defects found by this pass's own tests (fixed)

1. The first design verified attestation at every decision, so the anti-replay counter refused a node's second placement. Evidence is now
   verified once at ingest and its freshness is re-checked at use (`ATTESTATION_STALE`).
2. The config parent check keyed on the content digest. Activating a document identical to the active one kept the same digest, so two concurrent
   activations with the same parent both won (the concurrency test found 2 winners). The parent is now a per-activation `rev_id`.
3. The adapter reconcile loop reused one single-use credential across calls and hit replay refusal. It now takes a token factory.
4. The checklist-status classifier first read "ownership" / "resource owners" as needing a human decision. Its regex was narrowed, and
   BLOCKED_EXTERNAL components with evidence overlap get their own `EVIDENCED_PARTIAL_EXTERNAL_OPEN` label.

## Falsifier

`tests/test_tooling.py::ExitGateTest::test_gate_is_a_gate_not_a_wall` passes synthetic, non-delivered inputs with every fact real and gets GO.
It then removes one input at a time and gets NO_GO each time, including when the approver is a tool name ("Claude"). The delivered inputs give NO_GO.

## Not done, by name

MASTER.md recovery (MC-01), owner binding (MC-03 and every D01), approvals of ADRs/SHALL/policies, KMS/HSM (MC-24), hardware attestation
(MC-25/EXT-04), multi-host consensus (MC-32), platform matrix execution (MC-45), fleet/soak certification (MC-48), release signing (MC-49/60),
license choice (MC-60), and end-to-end certification of EXT-01..08.
