# GAP-13 Policy Engine — SHALL-level Requirements Specification

**Document:** REQ-G13 v1.0.0 (engine release 5.0.0) · **Closes:** G13-MC-043 · **Traceability:** `TRACEABILITY.json`

Each requirement is testable; the test IDs named in `TRACEABILITY.json` are the acceptance criteria. Normative keywords per RFC 2119.

## Evaluation semantics (C011–C019)

| ID | Requirement |
|---|---|
| REQ-EVL-001 | The engine SHALL return `deny` for any request that no `allow` rule matches (deny by default). |
| REQ-EVL-002 | The engine SHALL select the matching rule with the greatest number of matched attributes. |
| REQ-EVL-003 | Among equally specific matches the engine SHALL prefer `deny`, then the lexicographically smallest rule name, and SHALL set `tie_break=true`. |
| REQ-EVL-004 | Identical request and active bundle SHALL produce byte-identical verdicts, independent of rule order in the bundle. |
| REQ-EVL-005 | Every verdict SHALL carry `rule`, `version` and `bundle{bundle_id,generation,digest}`. |
| REQ-EVL-006 | Attribute matching SHALL be type-strict (`true` ≠ `1` ≠ `"1"`). |
| REQ-EVL-007 | The compiled matcher SHALL return exactly the same match set as a linear scan. |
| REQ-EVL-008 | Evaluation latency p99 SHALL stay within the SLO in `SLO.md` for bundles up to 10 000 rules. |
| REQ-EVL-009 | Explanations SHALL NOT contain request attribute values; the matched-rule list SHALL require `policy.explain.detailed`. |

## Bundle contract and trust (C021–C029, C041–C050)

| ID | Requirement |
|---|---|
| REQ-BND-001 | Bundles SHALL be accepted only as `PK_POLICY_SIGNED_BUNDLE/1` envelopes whose Ed25519 signature verifies over `"PK_POLICY_BUNDLE/1\0" ‖ payload`. |
| REQ-BND-002 | No API SHALL activate rules on the basis of a caller-supplied verification assertion. |
| REQ-BND-003 | The signing algorithm SHALL be taken from the verifier's local allowlist and SHALL equal the trust-store key's registered algorithm. |
| REQ-BND-004 | Payloads SHALL be canonical JSON (UTF-8, NFC, sorted keys, no whitespace, integers only); non-canonical payloads SHALL be rejected. |
| REQ-BND-005 | The parser SHALL reject duplicate keys, floats, non-finite numbers, invalid UTF-8, unknown top-level fields (outside `extensions.x-*`), and any unsupported schema version before semantic interpretation. |
| REQ-BND-006 | Bundle size, rule count, attributes per rule, string length and nesting depth SHALL be bounded by configuration, checked before full parsing where possible. |
| REQ-BND-007 | Signer key revocation, compromise, validity window, purpose and environment scope SHALL be enforced at verification time. |
| REQ-BND-008 | Bundle issuer and environment SHALL match the signer key's issuer and the verifier's environment. |
| REQ-BND-009 | A bundle whose generation is at or below the durable anti-rollback floor for its namespace SHALL be refused, except through the authorised rollback path to a previously accepted digest. |
| REQ-BND-010 | Two bundles with the same generation and different digests SHALL be refused. |
| REQ-BND-011 | Corrupt or unreadable anti-replay state SHALL fail activation; it SHALL NOT reset to zero. |
| REQ-BND-012 | Tenant-scoped rules SHALL bind `tenant` and SHALL NOT widen an estate deny. |
| REQ-BND-013 | Activation SHALL be atomic: a rejected bundle leaves the previous snapshot active. |

## Request attributes (C011–C019, C041, C050)

| ID | Requirement |
|---|---|
| REQ-ATT-001 | Protected attributes (`tenant`, `workload`, `site`, `environment`, `residency`, `classification`, `identity.*`, `attestation.*`) SHALL come only from the trusted context provider; a caller that supplies one SHALL be refused. |
| REQ-ATT-002 | Attributes SHALL be validated against the declared type system; unknown attributes SHALL be rejected by default. |
| REQ-ATT-003 | String attributes SHALL be NFC-normalised and SHALL NOT contain control/format characters. |
| REQ-ATT-004 | Unavailability of the trusted context provider SHALL fail closed. |

## Staleness and emergency control (C018, C048, C056–C059, C092)

| ID | Requirement |
|---|---|
| REQ-STL-001 | Bundle age SHALL be computed from monotonic time plus persisted age, and SHALL never be reduced by a wall-clock rollback. |
| REQ-STL-002 | Past `staleness_warning_seconds` the service SHALL report degraded health and emit a `stale.warning` audit event. |
| REQ-STL-003 | Past `staleness_hard_seconds` (or bundle `expires_at`) the service SHALL apply the configured mode before rule matching: `FAIL_CLOSED` refuses, `DENY_ONLY` converts allows to deny, `FREEZE_LAST_KNOWN_GOOD` evaluates and flags. |
| REQ-STL-004 | Request fields SHALL NOT influence staleness behaviour. |
| REQ-STL-005 | A restart SHALL NOT reset bundle age. |
| REQ-CTL-001 | The service SHALL support `NORMAL`, `UPDATE_FROZEN`, `DENY_ONLY`, `EVALUATION_DISABLED` and a quarantine list, each transition requiring a capability, reason and change ID. |
| REQ-CTL-002 | Control state SHALL persist across restart; corrupt control state SHALL start in `DENY_ONLY`. |
| REQ-CTL-003 | Configuration reload and bundle arrival SHALL NOT clear emergency state; `EVALUATION_DISABLED` SHALL never auto-expire. |
| REQ-CTL-004 | Quarantining the active bundle SHALL roll back to a non-quarantined last-known-good or enter `DENY_ONLY`. |

## Administration, audit, operations (C023–C024, C036–C040, C049, C052, C061–C080)

| ID | Requirement |
|---|---|
| REQ-ADM-001 | Every privileged operation SHALL require a distinct capability, scoped by environment/site/tenant, and SHALL be denied by default. |
| REQ-ADM-002 | High-impact operations SHALL require step-up authentication (MFA within 300 s) or break-glass identity. |
| REQ-ADM-003 | Service identities SHALL NOT obtain human-only capabilities. |
| REQ-ADM-004 | Tokens SHALL be validated for signature, issuer, audience, expiry, lifetime, replay (jti) and revocation. |
| REQ-ADM-005 | With separation of duties enabled, the principal that stages a bundle SHALL NOT activate it. |
| REQ-AUD-001 | Security-relevant events SHALL be written to a hash-chained, sequence-numbered, append-only audit log whose tampering, deletion, reordering and truncation are detectable by `audit.verify_chain`. |
| REQ-AUD-002 | Audit records SHALL NOT contain secrets or request attribute values. |
| REQ-AUD-003 | When the audit sink is down and the buffer is exhausted, privileged operations SHALL be refused. |
| REQ-OPS-001 | `/v1/ready` SHALL be false with reasons when no bundle is active, the bundle is past hard expiry in `FAIL_CLOSED`, evaluation is disabled, or the audit sink is down. |
| REQ-OPS-002 | Status SHALL expose engine release, bundle identity, age, anti-rollback floor, control state, dependency state and configuration provenance, and SHALL NOT expose key material. |
| REQ-OPS-003 | Metrics SHALL cover verdicts, default denies, rule hits, ties, errors, latency histogram, bundle age/generation, stale refusals, overload sheds and auth denials. |
| REQ-OPS-004 | Logs SHALL use registered event IDs and only allow-listed fields, pseudonymising tenant/workload/subject. |
| REQ-OPS-005 | W3C `traceparent` SHALL be accepted and propagated to the verdict. |
| REQ-OPS-006 | Admission control SHALL shed requests beyond `max_concurrency` with a retryable `G13-E310`. |
| REQ-OPS-007 | All refusals SHALL carry a stable `G13-Exxx` code and `retryable` flag (`PK_POLICY_ERROR/1`). |
| REQ-OPS-008 | Configuration changes SHALL be authorised and recorded with a provenance record chained to the previous configuration. |
| REQ-OPS-009 | Distribution SHALL be idempotent, back off with capped full jitter, refuse non-HTTPS endpoints, and pass every bundle through verification and controls. |
| REQ-OPS-010 | A restart SHALL rebuild the active policy only by re-verifying the cached signed envelope. |

## Governance (C009–C010, C020, C090–C100)

| ID | Requirement |
|---|---|
| REQ-GOV-001 | Every release SHALL produce a certification evidence manifest bound to the exact artifact digests, validated by `certify.verify_manifest`. |
| REQ-GOV-002 | The release gate SHALL block on failed/unknown-skipped tests, performance regression beyond tolerance, fixture drift, version inconsistency, expired waivers, or any Priority-0 component not accepted. |
| REQ-GOV-003 | Documentation claimed as bundled SHALL be present (packaging test). |
