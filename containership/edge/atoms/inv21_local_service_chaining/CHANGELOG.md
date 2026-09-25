# Changelog

## 4.3.0 - 2026-09-23

Missing-component remediation pass against INV21_MISSING_COMPONENTS_COMPREHENSIVE_CHECKLIST_4.2.0 (42 gaps).

- Runtime split into stdlib-only modules; pk_core now needed only for the conformance adapter, and its absence FAILS the suite instead of skipping it.
- Added authenticated `CallContext` (HMAC-SHA256 runtime credentials, issuer allow-list, expiry/skew, replay window, key rotation); production mode refuses the 4.x string API.
- Added PK_CAPABILITY/1 decision contract and fail-closed `GuardedProvider` (timeout, malformed, version, correlation, stale revision; bounded TTL cache without negative caching).
- Added leased residency (epochs, sources, watchers, stale/unhealthy suppression, snapshot/restore/reconcile).
- Added deadlines, cancellation, admission control, per-tenant rate limits, circuit breaker, idempotency-aware bounded retry.
- Added async path (`ainvoke`, `Hop.acall`), concrete HTTP/JSON transport with TLS-off-loopback refusal, peer endpoint and `/healthz /readyz /metrics`.
- Added PK_CHAIN_ERROR/1 taxonomy with sanitised envelopes; handler/provider/transport failures normalised.
- Added nine versioned JSON schemas, golden fixtures and a breaking-change detector.
- Added tamper-evident audit chain, bounded metrics with cardinality caps, pseudonymised decision ledger and explain view.
- Added config schema with environment/site overrides, atomic activation with provenance, rollback, lifecycle state machine, emergency quarantine, stall suppression, canary evaluation with automated rollback.
- Added test suites: identity, schema/errors, policy/residency, admission/lifecycle/config, audit/telemetry, async/transport, semantic equivalence (loopback + HTTP), adversarial T1–T12, fuzz/property, concurrency, fault injection, adjacent-contract stand-ins, packaging, rollout, governance.
- Added pyproject/constraints/MANIFEST, reproducible wheel+sdist, SBOM/provenance generator, benchmark harness, traceability generator, release gate, CI workflow, docs, ADRs, alerts, dashboard, governance registers.
- Independent second-pass audit (SP-01..SP-10) and follow-up: 9 defects fixed with regression tests, including a CRITICAL forged-principal cross-tenant execution in production mode; bearer-token replay bounded, not fixed; in-process handler trust recorded as a residual. See AUDIT_REPORT_4.3.0.md §3.
- Defects found and fixed by the new tests during this pass: production API silently stripped whitespace from callee names (`"svc\n"` dispatched to `svc`); deeply nested JSON (`[`×100000) escaped the wire parser as RecursionError and was misreported as a transport failure; iat rounding made freshly issued credentials intermittently "not yet valid"; decision-ledger retention only evicted from the head, so an out-of-order old event survived; the redaction key was a published constant; a concurrently revoked policy decision surfaced as an unexpected thread exception in tests (now asserted as fail-closed `stale_policy`).

## 4.2.0 - 2026-09-23

- Added explicit per-hop capability authorization hook and refusal telemetry.
- Added injectable remote-dispatch handoff while retaining the compatibility sentinel.
- Replaced externally mutable residency authority with synchronized immutable placement records and revision tracking.
- Added atomic unplacement and tenant-ownership enforcement.
- Added stable structured chain error codes/details and routing decision events with duration.
- Bounded trace and decision telemetry to prevent unbounded diagnostic memory growth.
- Hardened input/configuration validation for host, tenant, callee, trace, path, depth, callbacks, and telemetry limits.
- Added standalone runtime tests that execute without `pk_core`, closing the prior all-tests-skipped audit blind spot.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::Residency.place: re-placing an existing name under another tenant silently hijacked it; empty name/tenant or non-callable handler accepted -> CrossTenantChain / ValueError
- component.py::Chainer.call: refused cross-tenant hop was recorded in the trace before the check -> append trace only after the hop is allowed

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
