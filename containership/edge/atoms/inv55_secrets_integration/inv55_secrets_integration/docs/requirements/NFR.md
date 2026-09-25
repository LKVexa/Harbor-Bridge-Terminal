# Non-functional requirements (INV55-NFR-001, DRAFT — thresholds PROPOSED, owner approval pending)

| ID | Dimension | Target (PROPOSED) | Measured in this snapshot | Evidence |
|---|---|---|---|---|
| NFR-LAT-01 | resolve latency, cached | p99 ≤ 5 ms, p50 ≤ 1 ms in-process | see `evidence/bench.json` (reference host, not certified) | `tools/bench.py` |
| NFR-LAT-02 | use latency | p99 ≤ 5 ms in-process | same | `tools/bench.py` |
| NFR-LAT-03 | resolve latency, provider path | p99 ≤ provider RTT + 5 ms | in-memory only; Vault path UNMEASURED | W-006 |
| NFR-AVL-01 | availability of resolve | 99.95 % monthly (excl. provider outage with offline-deny) | not measurable offline | W-006 |
| NFR-DUR-01 | audit durability | every accepted decision fsynced before response | implemented in `AuditLog.append` (file sink) | `Audit` tests |
| NFR-CON-01 | consistency | rotation read-your-writes on the same instance (cache invalidated on rotate); cross-instance staleness ≤ `cache.fresh_s` | implemented | `test_rotation_keeps_old_lease_on_old_version` |
| NFR-ISO-01 | isolation | zero cross-tenant resolutions | enforced in authz + name pattern | `test_T02_cross_tenant` |
| NFR-STA-01 | startup | bootstrap to ready ≤ 10 s | `tools/bootstrap.py` steps 1–5 | bootstrap test |
| NFR-REC-01 | recovery | ready ≤ breaker cooldown + 1 probe after provider recovery | implemented | `test_outage_offline_deny_then_recovery` |
| NFR-WC-01 | worst case | request ≤ `retry.deadline_s` (default 2 s) wall time, never unbounded | Deadline enforced | `test_retry_respects_deadline` |
| NFR-RES-01 | resources | leases ≤ 100 000, cache ≤ 10 000, quota keys ≤ 10 000, metric series ≤ `max_series`, idempotency keys ≤ 10 000, request ≤ 16 KiB | enforced | limits tests |
