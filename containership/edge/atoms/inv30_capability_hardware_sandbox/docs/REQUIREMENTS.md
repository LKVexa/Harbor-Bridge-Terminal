# INV-30 formal requirements (INV30-GAP-008 · INV-30-C011)

Normative keywords per RFC 2119. Each REQ is traced in `TRACEABILITY.json` to code, tests and gate evidence.

## Capability invariants (zero error budget, unwaivable)
* **REQ-001** INV-30 SHALL refuse any access whose byte range is not wholly inside the capability's `[base, base+length)`. (`core.Capability.check`; test_capability_core, test_properties P1)
* **REQ-002** INV-30 SHALL refuse any access whose operation is not in the capability's permission set. (P1)
* **REQ-003** Derivation SHALL produce a capability whose bounds and permissions are subsets of the parent's; any widening SHALL be refused with `AMPLIFICATION`. (P2/P3, chains)
* **REQ-004** Invalidation SHALL be permanent; an invalidated capability SHALL refuse access, derivation and revalidation. (P4, concurrency)
* **REQ-005** INV-30 SHALL NOT report `cheri-hardware` enforcement unless a hardware backend performed the check; every success record SHALL carry `enforcement`. (backend, schema access_result, T-04)
* **REQ-006** A workload requiring hardware enforcement SHALL be refused with `HARDWARE_REQUIRED` where hardware is unavailable; it SHALL NOT be downgraded. (T-04, failover test)

## Security
* **REQ-010** Every boundary request SHALL be authenticated (HMAC-SHA256, ≤30 s skew, single-use nonce). (T-06, T-07)
* **REQ-011** Authorization SHALL be deny-by-default per principal × action × tenant; only `mint` holders SHALL mint. (T-05, T-08)
* **REQ-012** Handles SHALL be opaque, 128-bit random, tenant-bound, and backed by a signed root grant verified on every use. (T-01, T-10)
* **REQ-013** Security-relevant events and all refusals of category security/policy SHALL be written to the tamper-evident audit ledger. (T-13)
* **REQ-014** Diagnostics SHALL NOT contain key material, raw handles, raw tenant ids or capability bases. (T-12)
* **REQ-015** Peer/node/artifact trust SHALL require a verified attestation from a registered anchor with an allow-listed measurement. (T-14)

## Interfaces
* **REQ-020** All external payloads SHALL validate against the versioned schemas in `schemas/`; unknown fields SHALL be refused. (test_contracts)
* **REQ-021** Every refusal SHALL be a `PK_FAILURE/1` envelope with code, category, retryable, terminal, correlation id. (test_contracts)
* **REQ-022** Security/policy failures SHALL NOT be marked retryable. (test_contracts)
* **REQ-023** Requests SHALL be bounded by deadlines (≤60 s) and honour cancellation; derive SHALL support idempotency keys. (test_service, test_resilience)
* **REQ-024** Limits in `limits.py` SHALL be enforced at the boundary. (T-11, quota contention)

## Operations
* **REQ-030** Configuration SHALL be validated before activation, activated atomically, recorded with provenance, and rollback-able. (test_config_integrity)
* **REQ-031** Operators SHALL be able to quarantine a tenant, quarantine the service, and emergency-disable (revoking all capabilities). (test_service, test_ops)
* **REQ-032** Health SHALL expose status, readiness, version, enforcement, config digest, dependency status and active capability count. (test_service, schema health)
* **REQ-033** Releases SHALL be certified only by machine-readable evidence bound to the tree digest; skipped mandatory suites SHALL block. (release.py)
* **REQ-034** A performance regression beyond `config/perf_thresholds.json` SHALL block release. (bench.regression)

## Functional requirements per deployment context → `DEPLOYMENT_CONTEXTS.md`. Non-functional → `NFR.md`.
