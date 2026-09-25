# INV-66 verification strategy (MC-037, MC-043, MC-044, MC-055 – MC-060)

| Suite | File | What it proves | Environment |
|---|---|---|---|
| Legacy engine regression | `tests/test_control_plane.py` | v4.2 in-process engine unchanged | local |
| Service E2E (in-process deps) | `tests/test_service.py` | admission, RBAC, provenance, policy, idempotency, quota, freeze, lifecycle, config activate/rollback, explain, inventory, audit, logs, traces, metrics | local |
| Contract | `tests/test_contracts.py` + `tests/fixtures/` | schemas valid; bundled validator agrees with reference `jsonschema`; error catalog backward compatible; golden fixtures; protocol negotiation | local |
| Security / fuzz | `tests/test_security.py` | token attacks, RBAC hierarchy, signature replay, registry confusion, tenant isolation, parser bombs, 1 500-case seeded mutation fuzz | local |
| Durability / fault injection / DR | `tests/test_durability.py` | restart replay equality, torn-tail recovery, mid-journal corruption refusal, disk-full fail-closed, crash mid-delivery resume, compaction/retention/legal hold, full-chain-rewrite detection by anchors, backup/restore/tamper refusal | local FS |
| HA / races | `tests/test_ha.py` | lease exclusivity, fencing of stale leader, 4-process contention never forks the chain | local multi-process |
| Integration over HTTP | `tests/test_integration.py` | real HTTP server; HTTP GAP-13 and INV-63 adapters against live fake servers (traceparent, idempotency key, version pin); GitOps; breaker/retry/bulkhead | local sockets |
| pk_core conformance | `tests/test_component.py` | 100-item Post-Kubernetes checklist | **requires external pk_core** (skipped locally; CI job fails if absent) |
| Benchmark / load / soak gate | `tools/bench.py` | latency/throughput/overload/replay/RSS/journal thresholds + baseline regression | local; reference host for release |

Rules: skipped tests are non-evidence (`tools/no_unapproved_skips.py` allows only the pk_core skips, which are covered by waiver W-003). `python -O` run is required (no assert-dependent checks).

**Not covered in this archive (waived, see governance/WAIVERS.json):** real IdP, real GAP-13/GAP-07/INV-63 services, real wasmCloud lattice (W-004); multi-node over a network + replicated storage partition tests (W-006); hosted CI matrix execution (W-010).
