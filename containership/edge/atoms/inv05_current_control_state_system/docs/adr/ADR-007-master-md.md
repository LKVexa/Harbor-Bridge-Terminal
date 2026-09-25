# ADR-007 — Disposition of the missing MASTER.md corpus

* Status: **Proposed — owner decision required** (EX-002) · Traceability: MC-002, C020

v4.2.0 found that `MASTER.md` was referenced but absent. This package cannot recover it (no source of truth was supplied). Proposed decision: **formally remove MASTER.md from the product contract** for 4.3.x — the normative content it would have held is now carried by `docs/ARCHITECTURE.md`, `docs/REQUIREMENTS.md`, `docs/INTERFACES.md` and the ADRs, and the traceability matrix does not reference it. If the owner instead restores the file, place it at `MASTER.md`, record its SHA-256 and provenance in `traceability/master_md_provenance.json`, and `tools/check_master_md.py` will then enforce the required section schema. CI already fails if any document claims MASTER.md is present while the file is absent.
