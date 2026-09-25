# 04 — Master prompt and workflow

**Goal:** close every checklist component that can honestly be closed inside the archive. Mark the rest UNVERIFIED or PARTIAL with named blockers. Never fabricate provider, `pk_core`, review or approval evidence.

**Rules carried from the checklist:** P0/P1 need executable evidence, not prose. External infrastructure is SKIPPED, never PASS. `[x]` only with reviewed evidence.

**Workflow:** implement to-do 1–14 in order. Each module gets `test_cNN_*` tests (positive and negative). The evidence generator maps tests to components and downgrades any claim that lacks a passing test or whose artifact is missing. Gate PASS requires an independent review record, which the builder cannot supply. Reference brokers stay unchanged (invariants 14/15 in every component). The package stays stdlib-only at runtime; provider clients and `cryptography` are pinned optional extras.

**Merge-revealed changes:** version single-sourcing (VERSION ↔ `__init__` ↔ pyproject ↔ CHANGELOG, enforced by test); `fullmatch` everywhere; conformance redelivery hook per provider; the evidence-generator artifact resolver.
