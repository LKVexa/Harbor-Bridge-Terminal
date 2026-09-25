# Exception / waiver register (C099, MC-28)

Every row needs owner, rationale, compensating control, expiry and approval. `tools/run_gate.py` flags expired rows and rows with an UNASSIGNED owner or approver as blockers.

| ID | Item | Rationale | Compensating control | Owner | Approver | Expires |
|---|---|---|---|---|---|---|
| EX-001 | pk_core unpinned (MC-01) | source not supplied | deterministic BLOCKED preflight; local evidence gate | UNASSIGNED | UNASSIGNED | 2026-10-23 |
| EX-002 | IOCP/kqueue unexecuted (MC-03/05/24) | no Windows/macOS/BSD runner available | cells marked UNVERIFIED; portable fallback selected elsewhere | UNASSIGNED | UNASSIGNED | 2026-10-23 |
| EX-003 | Component licence undeclared | owner decision | SBOM records UNDECLARED | UNASSIGNED | UNASSIGNED | 2026-10-23 |
| EX-004 | Release signing key ephemeral (not KMS-bound) | no KMS reference configured | manifest carries public key; digests verified | UNASSIGNED | UNASSIGNED | 2026-10-23 |
| EX-005 | Soak shorter than 4 h policy | session time limit | shorter soak recorded with leak slopes | UNASSIGNED | UNASSIGNED | 2026-10-23 |
| EX-006 | Authoritative INV-17/18/15/13/SCH-01 not installed | sibling packages not in archive | reference implementations behind Protocols, tested | UNASSIGNED | UNASSIGNED | 2026-10-23 |
