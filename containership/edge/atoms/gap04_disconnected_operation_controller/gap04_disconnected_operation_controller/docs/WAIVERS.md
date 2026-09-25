# Exception / Waiver / Debt Register (C54)

Machine-readable source: `evidence/waivers.json` (consumed by `runtime/gate.py`). All entries are **proposed**: no approving authority is assigned (W-001), so none counts as an accepted exception and every `blocks_production` entry keeps the gate at NO_GO. P0 waivers may not be indefinite; each has a hard expiry and review date.

| ID | Title | Controls | Blocks GO | Expires | Status |
|---|---|---|---|---|---|
| W-001 | Named owners, approvers and reviewers are not assigned | C47, C48-011, C49-016, C50-018, C54-008… | yes | 2026-12-31 | proposed |
| W-002 | Adjacent layers exercised only via in-package reference implementations | C09, C10, C11, C12, C13… | yes | 2026-12-31 | proposed |
| W-003 | pk_core not supplied; conformance adapter suite skipped | C37, C44-006 | yes | 2026-12-31 | proposed |
| W-004 | Dependency lock lacks wheel hashes | C45-007, C45-020, C46-007 | yes | 2026-12-31 | proposed |
| W-005 | No TPM/HSM/KMS key custody; not FIPS-validated | C04-008, C15-009, C15-010, C15-020, C01-019 | yes | 2026-12-31 | proposed |
| W-006 | Release signing uses a locally generated key without HSM custody or CI builder identity | C46-009, C46-012, C55-013 | yes | 2026-12-31 | proposed |
| W-007 | No release CI; evidence is from local runs | *-023, C31-018, C34-018, C37-019, C38-016 | yes | 2026-12-31 | proposed |
| W-008 | Single-platform qualification (Linux x86_64, CPython 3.11) | C02-005, C03-005, C31-015, C38-012, C45-013 | yes | 2026-12-31 | proposed |
| W-009 | No independent security review, penetration test, or vulnerability scan | *-024, C35-016, C45-018, C46-013 | yes | 2026-12-31 | proposed |
| W-010 | Performance measured on a container, not representative edge hardware; power not measured | C38-012, C38-019, C38-020, C39-016 | yes | 2026-12-31 | proposed |
| W-011 | Fencing is single-host (OS lock + persisted generation) | C16-007, C16-010, C16-012, C16-020 | yes | 2026-12-31 | proposed |
| W-012 | Trusted-time anti-rollback is software-only (no TPM NV counter) | C02-007, C02-009, C02-020, C17-010 | yes | 2026-12-31 | proposed |
| W-013 | Per-site decision quota configured but not enforced | C21-006, C30-007 | no | 2026-12-31 | proposed |

Each record also carries risk statement, rationale, compensating controls, owner/approver (unassigned), and review date. Closed or expired waivers are retained; reopening requires a new ID and approval.
