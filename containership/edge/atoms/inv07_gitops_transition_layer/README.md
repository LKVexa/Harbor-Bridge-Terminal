# INV-07 - GitOps transition layer

> **5.0.0 production overlay.** `components/` contains a stdlib-only production controller built against the
> 54-component professional checklist: real Git transport, Ed25519/OpenPGP commit trust, DSSE provenance, fenced
> journalled reconciliation, policy, tenancy, observability and an operator API. Status of all 2,160 checks is in
> `components/evidence/CHECKLIST_STATUS.json` (summary in `components/STATUS.md`). **Production certification: NOT
> CERTIFIED** -- no owner/reviewer is assigned and several items need a Git server, a Kubernetes cluster, a KMS or
> owner decisions. Run everything with `python -B inv07_gitops_transition_layer/components/run_all.py`.

**Version:** 5.0.0 (see `CHANGELOG.md`)  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`  
**Audit:** `AUDIT_REPORT.md`  
**Known production gaps:** `MISSING_COMPONENTS.md`

The GitOps transition layer makes a Git repository the source of desired state: a controller follows an approved revision, verifies provenance, converges live state toward the declared state, detects out-of-band drift, and records rollback/reconciliation history.

The bundled `gitops_model.py` is a **dependency-free reference model for conformance testing**, not a production Git/Argo CD/Flux implementation. Production adapters and operational controls are tracked in `MISSING_COMPONENTS.md`.

## Responsibility

Own git-driven reconciliation: signed-commit verification, sync from commit to live state, detection/reversion/reporting of out-of-band changes, and rollback by revert.

## Owns

- Signed-commit verification semantics
- Sync from commit to live state
- Out-of-band change detection and reconciliation
- Rollback-by-revert semantics
- Applied revision history

## Explicitly does not own

- Git hosting
- Code review tooling
- The live control store
- Image building
- Secrets storage

## Non-goals

- Hosting Git
- Running code review
- Building images

## Interfaces named by the architecture contract

- `drift` - `PK_GITOPS_DRIFT/1` - out-of-band changes found
- `sync` - `PK_GITOPS_SYNC/1` - commit to live state
- `verify` - `PK_GITOPS_VERIFY/1` - commit signature check

The standalone archive does not yet bundle typed schemas for these interfaces; that is tracked as a production gap.

## Service-level objectives declared by the contract

- **provenance** - zero unsigned commits applied (error budget: no budget)
- **convergence** - live state matches head within one sync interval (error budget: 1% may exceed)
- **drift reporting** - every reverted change reported (error budget: no budget)

## Test the dependency-free reference model

```text
python inv07_gitops_transition_layer/tests/test_gitops_model.py
python -O inv07_gitops_transition_layer/tests/test_gitops_model.py
```

These tests do not require `pk_core` and exercise canonical signing, signature refusal, immutable commit snapshots, drift reconciliation, safe rollback, SHA-256 commit IDs, basic concurrent appends, and secret-free status output.

## Run the full architecture conformance gate

When this component is placed beside the matching `pk_core` implementation:

```text
python inv07_gitops_transition_layer/tests/test_component.py
python -m pk_core list
python -m pk_core run INV-07 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-07 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

If `pk_core` is absent, `tests/test_component.py` deliberately skips its three conformance tests. A skipped suite is **not** proof that all 100 requirements passed.

## Day-0 / day-1 / day-2 intent

- **Day 0 (bootstrap):** import the parent package, run `pk_core run INV-07`, and archive the emitted evidence ledger as a baseline.
- **Day 1 (deployment):** run `pk_core gate INV-07`; a `NO_GO` verdict blocks rollout and any conditional gate must be explicitly accepted and recorded.
- **Day 2 (operation):** re-run the gate on each contract or implementation change and verify that new evidence chains to the previous trusted head.

The originally referenced `MASTER.md` is **not present in the uploaded archive**. Its absence, plus the missing evidence/traceability artifacts, is tracked in `MISSING_COMPONENTS.md`.
