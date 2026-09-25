# Changelog - GAP-13

## 5.0.0 - 2026-09-22

Missing-components build: applies the *GAP13 Policy Engine Missing Components Professional Checklist v1.0.0* (51 work packages + EXT-01..05) to the 4.2.0 hardened baseline.

### Breaking changes
- `PolicyEngine.load()` no longer accepts a caller-supplied `{"verified": True}` mapping (or any caller assertion). It requires a `VerificationResult` minted by `BundleVerifier`, and the rules/version passed must equal the verified bundle's. New `PolicyEngine.activate(result)`. Rules can no longer be passed to the `PolicyEngine` constructor.
- `Rule.matches()` is type-strict (`True` != `1` != `"1"`).
- Verdicts gain `bundle{bundle_id,generation,digest}`; explanations gain `bundle`, `attributes` per matched rule, `matched_total`, `truncated`.
- `BundleRejected`/`ScopeEscalation` now live in `errors.py` (still `PermissionError` subclasses; re-exported from `engine`).

### Priority 0 — security and correctness (G13-MC-001..010)
- Ed25519 `PK_POLICY_SIGNED_BUNDLE/1` verification with local algorithm allowlist, trust store (issuer, environments, validity, purpose, revocation, compromise), domain separation and TOCTOU-free verified-bytes-are-parsed-bytes.
- Strict bounded canonical `PK_POLICY_BUNDLE/1` parser; JSON Schemas for bundle, envelope, verdict, explanation, error; golden fixtures.
- Trusted context provider + typed attribute allowlist; protected attributes cannot be caller-supplied.
- Stale-policy enforcement (warning/hard thresholds, FAIL_CLOSED / DENY_ONLY / FREEZE_LAST_KNOWN_GOOD, monotonic age, clock-anomaly handling, restart-safe).
- Durable anti-rollback floor, collision and replay detection; corrupt state fails closed.
- Capability-based admin authorization with scope, step-up, separation of duties, rate limiting, token validation (aud/iss/exp/jti replay/revocation).
- Hash-chained tamper-evident audit log with independent verifier.

### Priority 1-2 — service, integration, observability (G13-MC-011..028)
- Distribution controller (file/HTTPS, idempotent, full-jitter backoff, cancellation), persistent LKG cache, rollback manager, RCU atomic swap, `/v1` HTTP/JSON transport, stable error codes, compatibility matrix, configuration model + provenance chain, emergency controls and quarantine.
- Health/readiness/status, Prometheus metrics, structured logs with event IDs, W3C tracing, redaction/privacy policy, release/topology lineage, dashboards and alert rules, runbooks and severity model.

### Priority 3 — performance, resilience, certification (G13-MC-029..040)
- Compiled selectivity-anchored index (p99 evaluation ~0.05 ms at 10 000 rules vs ~6.5 ms linear scan in the reference run), hard limits, admission control, benchmark suite, fault-injection, fuzz/property, concurrency (threads + processes), threat-model security suite, integration contract tests, evidence manifest + verifier, rc/production release gates, CI workflow.

### Priority 4 — governance (G13-MC-041..051)
- OWNERS.yaml role/escalation structure (names UNASSIGNED), ADR-001 (Proposed), SHALL requirements, traceability matrix, deployment matrix, SLOs, security/EOL policy, waiver registry, production-exit gate, MASTER.md formally superseded.

### Honest status
No component is marked DONE (independent acceptance required). BLOCKED: MC-033 (edge hardware), MC-038 (real adjacent builds), MC-041 (named owners), MC-042 (ADR approval). Production-exit gate: NO_GO until resolved.

## 4.2.0 - 2026-09-22

Audit, repair and hardening pass.

### Correctness and API fixes

- Added the documented `PolicyEngine.explain()` interface and `PK_POLICY_EXPLANATION/1` output.
- Moved evaluator primitives into dependency-light `engine.py`; core policy evaluation now works without `pk_core`.
- Package import degrades cleanly when only the optional conformance framework is missing.
- Bundle loading is transactional: invalid candidates never partially replace the active bundle.
- Duplicate rule names are rejected to preserve unambiguous explanations and evidence.
- Loaded rule collections are immutable tuple snapshots, preventing caller-side list mutation from altering active policy.

### Security and validation hardening

- Strict validation for environment, bundle version, timestamps, requests, rule names, match attributes, effects and scopes.
- Scope-escalation checks no longer depend on hashable policy values.
- Tenant-scoped rules must bind an explicit `tenant` attribute, preventing accidental cross-tenant application.
- Match normalization sorts by attribute name only, supporting heterogeneous values safely.
- Clock regression relative to bundle load time is rejected rather than silently producing misleading staleness.

### Tests

- Added standalone unit coverage for deny-by-default, precedence, deterministic ties, explanations, atomic load, duplicate names, scope escalation, unhashable values, immutable snapshots, staleness and invalid inputs.
- Updated conformance version pin to 4.2.0.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::PolicyEngine.evaluate: tie_break only flagged opposite-effect peers, so an equal-specificity tie resolved by rule name went unrecorded (contract: record that a tie was broken) -> flag any other matched rule at the winner's specificity
- component.py::Rule.__post_init__: `match` documented as sorted attribute pairs but never normalised/validated (unsorted input changed nothing but duplicate attributes, empty names, unknown scopes were accepted) -> sort pairs, reject duplicate attributes, empty name and unknown scope with ValueError
- component.py::PolicyEngine.load: truthy non-bool `verified` values (e.g. "no") or non-dict verification passed/crashed; non-Rule entries crashed with AttributeError -> require verified is True in a dict, refuse non-Rule entries with BundleRejected

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
