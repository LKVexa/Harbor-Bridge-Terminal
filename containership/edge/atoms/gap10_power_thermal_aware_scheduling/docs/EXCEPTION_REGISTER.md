# GAP-10 Exception Register

Every exception is explicit, owned, risk-assessed and time-bounded. An exception never marks a failed requirement as passed; the related checklist items stay open in `evidence/CHECKLIST_EVIDENCE.json`.

| ID | Requirement(s) | Exception | Risk | Compensating control | Owner | Expires |
|---|---|---|---|---|---|---|
| EX-001 | All components: accountable engineering owner, on-call owner, reviewer sign-off | No named humans assigned in the package; roles are defined in `docs/OWNERSHIP.md` | High: evidence is unreviewed | Items remain OPEN-EXTERNAL; production gate cannot pass | *unassigned* | 2026-10-31 |
| EX-002 | 04, 05, 08 multi-host HA | Lease, policy and state backends are in-process / local-file reference implementations | High for multi-host deployments | Single-controller-per-shard deployments only; interfaces fixed for external CAS store | *unassigned* | 2026-11-30 |
| EX-003 | 06, 28, 36 non-repudiation | HMAC-SHA256 instead of asymmetric/HSM signatures | Medium | Scoped keys, rotation, revocation, two-person rule for relaxation | *unassigned* | 2026-12-31 |
| EX-004 | 01, 02, 03, 14, 29 interoperability | Peers exercised through in-repo reference backends, not real GAP-09/GAP-11/SCH-01/PLN-05 builds | High | Protocol classes pin the required methods; compat matrix marks peers `unverified` | *unassigned* | 2026-11-30 |
| EX-005 | 09, 34 hardware classes | No site hardware calibration data supplied | High | Conservative `UNKNOWN_PROFILE` used for every uncalibrated node | *unassigned* | 2026-11-30 |
| EX-006 | 33 fleet-scale | Benchmarks run in the build sandbox only, not on production hardware at target scale | Medium | Budgets encoded in `tools/bench.py`; rerun required per release | *unassigned* | 2026-11-30 |
| EX-007 | 21, 22, 24 | Exporter/logs/alerts produced as artifacts; no live Prometheus/log pipeline or pager wired | Medium | Alert rules validated against metric catalog in tests | *unassigned* | 2026-11-30 |
| EX-008 | CI must fail on skipped mandatory tests | `tests/test_component.py` (pk_core estate conformance) is skipped when `pk_core` is not installed | Medium | Only these estate tests are waivable; any other skip fails `tools/run_all_tests.py` | *unassigned* | 2026-10-31 |
