# INV-31 Ownership, Support and Licence (A08, A09, C009)

| Role | Holder |
|---|---|
| Accountable owner | **UNASSIGNED** |
| Technical maintainer | **UNASSIGNED** |
| Security contact | **UNASSIGNED** |
| On-call / escalation path | **UNASSIGNED** |
| Release approver | **UNASSIGNED** |
| Licence | **NOT CHOSEN** — no LICENSE/NOTICE file; redistribution terms unspecified |

These are human decisions. They were not filled in by the remediation pass because
an owner, an approver or a licence chosen by the tool that built the code is not an
owner, an approver or a licence. `tests/test_remediation.py::RepositoryIntegrityTest`
asserts that these fields stay UNASSIGNED until a person changes this file.

Escalation template to adopt once named: Sev1 page owner + security contact within
15 min; Sev2 owner next business hour; Sev3 ticket. See `docs/RUNBOOKS.md`.
