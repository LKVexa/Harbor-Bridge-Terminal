# INV-43 threat model (4.3.0)

**Controls:** C041, C050, C087. **Status:** drafted by the 4.3.0 pass; independent security review NOT yet performed (remediation item 24 remains open until it is).

## Assets
A1 tenant confidentiality across shared cores · A2 integrity of node posture records · A3 integrity of policy/config · A4 audit chain · A5 collector keys and bearer tokens · A6 availability of placement decisions.

## Trust boundaries
B1 node kernel → collector (sysfs) · B2 collector → registry (network, attested envelope) · B3 scheduler → registry (bearer token, `cotenancy.decide`) · B4 operator → registry (`control.emergency`) · B5 policy/config authors → registry (`config.activate`, sealed policy digest) · B6 build → release artifact (SBOM, digests, signature).

## Actors
Malicious tenant (runs arbitrary code on a shared node) · compromised workload · compromised collector host · hostile network peer · malicious or careless insider (scheduler/operator/policy author) · supply-chain attacker.

## Threats, mitigations, residual risk

| ID | Threat (STRIDE) | Mitigation in 4.3.0 | Test | Residual |
|---|---|---|---|---|
| T1 | Tenant leaks across SMT siblings (I) | SMT-on without attested core scheduling refuses | `test_smt_on_without_core_scheduling…` | Core-scheduling cookie correctness is SCH-01's |
| T2 | Partial mitigation read as full (I) | `Mitigation: … Vulnerable` → inactive | `test_partial_mitigation_refuses` | New kernel wording → `unknown` (safe) |
| T3 | Forged posture from a non-collector (S) | `posture.write` scoped per node + HMAC envelope bound to node | `test_scheduler_cannot_inject_posture`, `test_spoofed_node_identity` | Symmetric keys: registry compromise = key compromise |
| T4 | Replay of old good posture after regression (S/T) | per-key monotonic seq + epoch | `test_replay_of_old_good_posture_after_regression` | — |
| T5 | Collector lies about status (T) | status re-derived from raw kernel string | `test_claimed_status_is_rederived_from_raw` | Compromised collector can forge the raw string itself; needs HW attestation (item 11 BLOCKED) |
| T6 | Cost poisoning to create "active" (T) | non-finite/≤0/bool cost → unknown | `test_cost_poisoning_cannot_create_active` | Plausible fake cost accepted (affects reporting, not safety) |
| T7 | Stale posture during partition (T) | TTL freshness, restart closed | `FaultInjectionTest` | — |
| T8 | Policy weakened by edit (T/E) | policy digest seal + floor check; config tighten-only overrides | `test_tampered_or_weak_policy_refused`, `test_override_may_only_tighten` | An approved policy author can still approve a weak policy |
| T9 | Audit tampering / truncation (R) | HMAC hash chain + externally anchored head | `AuditChainTest` | Head anchoring must be done by release/evidence tooling |
| T10 | Injection via identifiers (T) | control-char/empty rejection; exact-match tenant compare | `test_injection_in_identifiers`, `test_tenant_escape_by_case…` | — |
| T11 | Privilege escalation between roles (E) | deny-by-default capabilities; collector separation of duty; global control needs unscoped operator | `test_privilege_escalation…`, `AuthzTest` | Identity provider integration external |
| T12 | Resource exhaustion (D) | body cap, rate bucket, in-flight limiter, bounded explain/idempotency caches, metric cardinality cap, observation cap | `test_limits_and_malformed`, `test_exhaustion_bounds` | Slowloris mitigated only by socket timeout |
| T13 | Side-channel via explain/metrics (I) | explain requires `decision.explain`; tenant ids pseudonymised in logs | `test_side_channel_misuse…`, `SecretLeakageTest` | Metrics labels carry node names |
| T14 | Secret leakage (I) | keys never in repr/logs/audit/explain; tokens stored hashed | `SecretLeakageTest`, `test_short_secret_refused…` | — |
| T15 | Supply chain (T) | SBOM, per-file SHA-256, provenance statement, signature | `tools/build_release.py` | Signature uses an ephemeral dev key until a release key exists (item 23) |
| T16 | Defect becomes a permit (E) | any unexpected exception → `internal_error` refusal | `test_internal_defect_never_permits` | — |
| T17 | GAP-02/read-back disagreement hidden (T) | contradiction downgrades to unknown | `test_gap02_contradiction_downgrades` | — |

## Assumptions
The node kernel's sysfs report is honest for an uncompromised kernel; the registry host is trusted; clocks are within 30 s (envelope skew bound).
