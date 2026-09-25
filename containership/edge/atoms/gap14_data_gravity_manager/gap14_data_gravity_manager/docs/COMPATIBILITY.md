# GAP-14 Compatibility Matrix (G14-P1-25)

| Surface | v4.2.0 | v4.3.0 | Notes |
|---|---|---|---|
| Python | 3.11 (tested) | **3.11 tested**; declared `>=3.11,<3.14` | 3.12/3.13 must be run in CI before certification (not available in this build env) |
| `GravityManager.recommend` → `PK_GRAVITY_RECOMMENDATION/1` | ✔ | ✔ unchanged | property test proves planner ≡ engine without profile |
| `PK_DATASET/1`, `PK_MOVE_COST/1` | ✔ | ✔ unchanged | |
| `PK_GRAVITY_DECISION_REQUEST/1` → `PK_GRAVITY_DECISION/2` | — | new | service path |
| `PK_POLICY_REQUEST/1`, `PK_POLICY_VERDICT/1` (GAP-13) | — | new | GAP-13 must implement |
| `PK_TOPOLOGY_SNAPSHOT/1` (GAP-03) | — | new | GAP-03 must implement |
| `PK_CONVERGENCE_PROOF/1` (GAP-05) | — | new | GAP-05 must implement |
| `PK_PLACEMENT_SNAPSHOT/1` (SCH-01) | — | new | SCH-01 must implement |
| `PK_DATA_MOVE_HANDOFF/1`, `PK_DATA_MOVE_ACK/1` (PLN-06) | — | new | PLN-06 must implement |
| `PK_CAPABILITY_TOKEN/1` | — | new | identity service must implement |
| `PK_AUDIT_RECORD/1` | — | new | stable across 4.x |
| `PK_GAP14_CONFIG/1` | — | new | |
| `pk_core` | untested | `>=1.0.0,<2.0.0`, schema `PK_CHECKLIST/1`, digest pin pending | handshake refuses outside range |

Tested combinations in this release: CPython 3.11.15 / Linux x86_64 / fixtures for all five estate services. **Not tested:** Windows (checklist E04), Python 3.12/3.13, real `pk_core`, live estate services.

Schema-evolution rule: strict unknown-field rejection means any producer change is a new schema version; GAP-14 will accept `/N` and `/N+1` in parallel during migrations (add the new tag to the adapter's accepted set; never widen field acceptance silently).
