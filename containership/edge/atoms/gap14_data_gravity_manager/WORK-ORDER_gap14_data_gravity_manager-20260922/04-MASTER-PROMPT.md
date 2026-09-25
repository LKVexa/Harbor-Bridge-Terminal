# 04 — Master prompt and workflow (contract for stage 05)

**Goal.** Close as much of the 40-component checklist as can be closed inside the package, without fabricating anything that needs the live estate, people or signing infrastructure, and publish an item-level status for all 1,831 items.

**Non-negotiables.**
- Keep `GravityManager.recommend` and `PK_GRAVITY_RECOMMENDATION/1` byte-compatible; prove the new planner reduces to it (property test).
- Stdlib only; zero runtime dependencies.
- Legality before cost, everywhere, including shadow/canary/simulation/DAG.
- Fail closed: no default substitutes for a missing, stale, unsigned, mis-bound or rolled-back input; no decision without an audit record.
- Never report a missing/partial `pk_core` gate as PASS.
- Status honesty: `implemented` needs code + test; things that need the estate, people or signing are `external`, never claimed.

**Workflow.** Execute 03-TODO in order; after each module, run the full suite; after all modules, run bench, release evidence and manifest; have an independent reviewer sample the manifest under a strict rule; fix, add tests or downgrade every finding; regenerate evidence; package.

**Acceptance.** Full suite green (only pk_core skips); manifest covers 1,831/1,831 items; MANIFEST.sha256 matches tree; README/CHANGELOG/AUDIT_REPORT/MISSING_COMPONENTS consistent with the manifest counts.
