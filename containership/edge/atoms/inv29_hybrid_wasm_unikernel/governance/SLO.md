# Production SLOs and support commitments (INV29-MC093) — PROPOSED, awaiting owner ratification

The contract SLOs are invariants with **no error budget**; they are enforced in code and monitored as SEV1 if ever violated.

| SLO | Target | Budget | Measured by |
|---|---|---|---|
| layer count | 0 compositions admitted with fewer layers than required | none | `inv29_compositions_total` + record `layer_count`; alert `INV29SingleLayerAdmitted` |
| import closure | 0 modules admitted with an unsatisfied import | none | property tests + decision stream |
| verification independence | both layers verified separately for every composition | none | record `verification.layers.*.verified` |
| **proposed** admission availability | 99.9 % of well-formed requests answered (admit or refuse) within 25 ms, monthly | 43 min/month | latency histogram |
| **proposed** correctness of refusals | ≥ 99.99 % of refusals carry a stable `INV29-E-*` code | 0.01 % | decision stream |

Support: business-hours owner response, 24×7 on-call for SEV1/SEV2 once the rotation in `OWNERS.md` exists. **Status: OWNER_ACTION** — numbers above are engineering proposals derived from `docs/CAPACITY.md`, not commitments.
