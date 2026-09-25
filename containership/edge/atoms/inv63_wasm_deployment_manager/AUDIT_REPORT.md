# INV-63 Wasm Deployment Manager — v4.3.0 remediation audit

**Input:** `inv63_wasm_deployment_manager_v4.2.0_COMPREHENSIVE_REMEDIATION_CHECKLIST.md` (92 work packages: 73 MISSING + 19 PARTIAL)
**Audit date:** 2026-09-23 · **Method:** executable: audit.py (tests + refs + approvals); no status is asserted by hand
**Source digest:** `sha256:6b3e4bc5b4fe30185b2143ebeff419c22c5f743e68ab277d6d2bbdd05851dc4f`

## Result

| | v4.2.0 (input) | v4.3.0 (this pass) |
|---|---:|---:|
| SATISFIED | 8 | **72** |
| PARTIAL | 19 | **28** |
| MISSING | 73 | **0** |
| Tests | 16 run / 3 skipped | **110 run, 107 passed, 0 failed, 3 skipped** (skips = `pk_core` absent) |

Transitions: 53 MISSING→SATISFIED, 11 PARTIAL→SATISFIED, 20 MISSING→PARTIAL, 8 PARTIAL stayed PARTIAL (now with the
repository work done). Every one of the 28 PARTIAL items has its in-repo implementation, tests and docs in place. Each
is waiting only on evidence that cannot be produced from inside a repository.

"SATISFIED" here means the requirement is proven by repository/runtime evidence: implementation refs exist, the
C-ID-tagged tests pass and the design docs exist. The gate adds one more condition before promotion: every design
artifact is still DRAFT with owner and approver `UNASSIGNED` until a `revision-signoff` approval binds this source
digest.

## Production exit gate — `BLOCKED`

| Criterion | Name | Status | Detail |
|---|---|---|---|
| G-01 | Full test suite passed, nothing skipped or failed | **SKIPPED** | 3 mandatory tests skipped (skips never count as passes) |
| G-02 | Every C001-C100 SATISFIED in freshly generated audit | **BLOCKED** | 28 requirements await external evidence |
| G-03 | Performance regression gate passed | **BLOCKED** | thresholds met but not yet approved on reference hardware |
| G-04 | Dependencies pinned and approved (pins.json) | **BLOCKED** | unpinned/unapproved: ['python', 'cryptography', 'wadm', 'pk_core'] |
| G-05 | Ownership complete (OWNERS.yaml) | **BLOCKED** | unassigned: ['service_owner', 'engineering_owner', 'oncall_rotation', 'security_contact', 'release_approver', 'architecture_approver', 'review_date'] |
| G-06 | No expired waivers; active waivers visible | **PASS** | 0 active waivers |
| G-07 | Recurring reviews not overdue | **BLOCKED** | no current review for: ['access', 'policy', 'dependency', 'configuration', 'architecture'] |
| G-08 | Evidence bound to this manifest digest and fresh | **PASS** | evidence bound to current source digest |
| G-09 | pk_core conformance executed | **BLOCKED** | pk_core not installed: framework conformance was skipped, which is not a pass |
| G-10 | Verdict signed by gate key | **BLOCKED** | INV63_GATE_SIGNING_KEY not provisioned |

## External evidence still required (owner action)

| Evidence key | Role | Blocks C-IDs |
|---|---|---|
| `arch-review` | architecture-approver | C005, C009, C010 |
| `consensus-lease` | architecture-approver | C058 |
| `edge-hardware` | sre | C068 |
| `external-anchor` | security-contact | C049 |
| `fleet-scale` | sre | C088 |
| `game-day` | sre | C092, C095, C096, C097 |
| `kms` | security-contact | C047 |
| `multi-arch-ci` | sre | C084 |
| `node-attestation` | security-contact | C044 |
| `owner-assignment` | service-owner | C009, C091, C094, C097, C100 |
| `perf-approval` | service-owner | C013, C061, C062, C070 |
| `pk_core` | release-approver | C090, C100 |
| `privacy-review` | security-contact | C079 |
| `review-records` | service-owner | C098 |
| `security-review` | security-contact | C041 |
| `signing-key` | release-approver | C090, C100 |
| `wadm-live` | service-owner | C030, C083, C084 |
| `wadm-pin` | release-approver | C031 |

## Performance (CI container, reference hardware not yet approved)

- `Manager.diff` at 1000 instances, cold: p50 2.34 ms / p99 5.16 ms. Before the heap placement change it was about 29 ms / 46 ms, which failed the contract SLO of p99 < 10 ms.
- No-op diff: p99 3.04 ms. Request path, no-op reconcile: p99 1.08 ms. Throughput: 1820 req/s.
- Replaying 10k journal records: 159 ms. Tracemalloc peak over 10k requests: 14.8 MB. Under overload, admission let 32 requests through and shed 968.

## Defects found and fixed during the pass

1. A secret embedded in a malformed config value was classified as a schema error and could be echoed back. Secrets are now scanned first.
2. The inbound W3C parent span id was discarded, and failed requests recorded no span.
3. A second journal handle could append over a stale view. This is now detected as `INV63-E-CONFLICT`.
4. Operator rollback could act while a workload was frozen, quarantined or under emergency disable.
5. `emergency_disable` and `quarantine_host` accepted a free-text actor with no authorization. They now require a platform-operator principal.
6. `require_encryption_at_rest` was not enforced at runtime. The service now refuses to start without a Sealer.
7. The FAILED and DELETED lifecycle states could not be reached. A failed rollback is now terminal and requires an operator.
8. The offline autonomy window used the wall clock and now uses the monotonic clock. The two config digests are now consistent.
9. Compaction dropped the rollback history. Version history is now carried in the snapshot.
10. The placement hot path was O(count × hosts), which missed the contract SLO. It now uses per-zone heaps, and a 300-case randomized test proves it picks the same hosts as before.

## Known limitations (tracked in `governance/WAIVERS.json` → `debt`)

- DEBT-001: leader fencing is single-host only (file epoch); running multiple nodes needs a consensus lease.
- DEBT-002: the token replay cache is in-process.
- DEBT-003: trace context is not forwarded to the lattice transport.
- DEBT-004: rollout is break-before-make within `max_unavailable`.
- Approval records in `governance/APPROVALS.json` are checked for presence, role, expiry and revision. Their signatures are not cryptographically verified until an approver key registry exists (part of `signing-key`).

## Reproduce

```
python -m unittest discover -s tests && python perf/bench.py --gate --out perf/results.json && python audit.py && python gate.py
```
