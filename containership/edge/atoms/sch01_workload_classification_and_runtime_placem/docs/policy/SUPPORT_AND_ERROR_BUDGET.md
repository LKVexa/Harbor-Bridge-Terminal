# Support commitment & error budget (MC-50) — PROPOSED, approver UNASSIGNED
- Support hours: TBD by owner. Paging: SEV1/2 page on-call (UNASSIGNED).
- SLOs (contract.py): soundness zero-budget; p99 < 100 ms @1,000 nodes (1%); determinism zero-budget.
- Budget burn: >2x burn over 1 h -> freeze config rollouts (`operator freeze` for placements only if soundness is at risk); budget exhausted -> feature freeze until recovered.
- Soundness or determinism breach: SEV1, disable scheduler (`operator disable`), preserve journal+audit.
