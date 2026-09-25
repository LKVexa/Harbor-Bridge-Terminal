# Formal production exit gate (C100)

The gate is machine-evaluated by `verify.py`; this page lists its criteria.
A release may be promoted to production only when **all** hold:

| # | Criterion | Evaluated by |
|---|---|---|
| G1 | compileall passes | verify.py |
| G2 | schemas regenerate without drift | tools/gen_schemas.py --check |
| G3 | all suites pass, zero skipped mandatory tests (pk_core conformance included) | verify.py test runner |
| G4 | RTM covers all 100 rows; every `present` row lists existing evidence paths | tools/build_rtm.py --check |
| G5 | performance gate: zero threshold breaches | tests/performance |
| G6 | manifest, SBOM, provenance, Nexus spec manifest generated for the same tree digest | runtime/release.py |
| G7 | all OWNERS roles assigned and accepted | governance_findings |
| G8 | license selected, approved, LICENSE present | governance_findings |
| G9 | all required approvals recorded | governance/APPROVALS.json |
| G10 | no expired or unapproved waiver; no overdue review | governance_findings |
| G11 | every required dependency pinned (pk_core!) | release/dependencies.json |
| G12 | evidence sealed | INV35_EVIDENCE_KEY |
| G13 | canary + rollback exercised on the candidate | evidence/rollout-<ver>.json (manual attestation, sealed) |
