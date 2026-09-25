# ADR-0002 — MASTER.md / per-item master prompt corpus (component 80)

- **Status:** Proposed. **The owner must decide.**
- **Date:** 2026-09-22

## Context

Before v4.2.0, the README referenced a `MASTER.md` and per-item master prompt/workflow artifacts. The v4.2.0 archive does not contain them, and v4.2.0 removed the false reference. No authoritative copy of that corpus is in this archive or the v4.3.0 work order. Checklist item IMPL-80.16 forbids inventing historical text.

## Options

1. **Restore:** the owner supplies the authoritative prior corpus. It is then added under `master/` with a manifest, stable IDs mapped to CHECKLIST.json C001–C100, and a CI completeness check.
2. **Formally remove:** record here that the distribution contract does not require the corpus, then drop the requirement from the series checklist.

## Recommendation

Choose option 2 unless the Post-Kubernetes Master Series distribution contract names the per-component MASTER.md as a normative deliverable. The v4.3.0 evidence chain (COMPONENT_STATUS.json, TRACEABILITY.md, the tests) replaces the corpus's role as the executable definition of done.

## Consequences until decided

Component 80 stays `OPEN_GOVERNANCE`. No MASTER.md content has been fabricated.
