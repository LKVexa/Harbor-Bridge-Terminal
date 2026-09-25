# Recurring reviews — INV-03 (checklist item 61)

**Status: PROPOSED** — cadence and reviewers are owner decisions.

| Review | Cadence | Evidence |
|---|---|---|
| Waivers (expired / pending / renewal queue) | weekly | `tools/recurring_review.py --ledger …` output archived |
| Access (who holds which role) | quarterly | OWNERSHIP.md diff + directory export |
| Baseline and runtime matrix | monthly | baseline epoch/history + `RuntimeInventory.inventory()` |
| Dependencies / CVEs | weekly | `sbom.cdx.json` against the advisory feed |
| Architecture (ADRs) | half-yearly | ADR status table |
