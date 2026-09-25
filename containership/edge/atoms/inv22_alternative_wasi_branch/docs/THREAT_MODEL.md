# INV-22 threat model (v4.3.0)

Each threat names the control that addresses it and the executable test that proves it. Rows marked **open** have no executable proof yet.

| # | Threat (contract.py) | Control | Test |
|---|---|---|---|
| T1 | Lossy shim produces different behaviour per branch | Shim only for `shimmable` entries with `proof_ref`; exhaustive round-trip; mutation testing | `test_shim.py::ExhaustiveRoundTrip`, `MutationDetection` |
| T2 | Unclassified interface assumed compatible | `INV22.CLASSIFY.UNCLASSIFIED`; completeness gate | `test_contracts.py::MatrixContract::test_completeness_gate` |
| T3 | Component runs on an uncertified branch | Signed cert + site branch + admission | `test_trust_state.py::SiteAndAdmission::test_admission` |
| T4 | Divergence grows unnoticed | Immutable drift history + drift policy | `test_trust_state.py::Governance::test_drift_policy` |
| T5 | Forged or edited certificate | Ed25519 over canonical payload; every field bound | `Certificates::test_every_payload_field_is_bound` |
| T6 | Replay of revoked certificate while offline | Revocation freshness bound | `SiteAndAdmission::test_offline_staleness_bounded` |
| T7 | Stolen issuer key | Key `revoked` flag invalidates history; retirement window | `Certificates::test_rotation_and_compromise` |
| T8 | Translator widens rights (confused deputy) | Rights monotonicity check after every translation | `Service::test_malicious_translator_cannot_escalate` |
| T9 | Credential replay / wrong audience / forged token | Token validation + jti replay cache | `AuthN::*` |
| T10 | Privilege escalation via scope wildcards | Concrete request scopes; default deny | `AuthZ::test_default_deny_and_scopes` |
| T11 | One person publishes matrix and self-certifies | Separation of duties | `AuthZ::test_separation_of_duties`, `OpsFacade` |
| T12 | Audit trail edited to hide an action | Append-only triggers + hash chain | `Store::test_audit_append_only_and_tamper_evident` |
| T13 | Stale controller flips site branch after failover | Epoch fencing token (CAS) | `SiteAndAdmission::test_fencing_race_single_winner` |
| T14 | Resource exhaustion via hostile documents | Size/depth/item limits; bounded concurrency | `Canonical::test_rejections`, `Resilience::test_overload_is_bounded_and_recovers` |
| T15 | Secrets leak via config/logs/errors | Secret refs, redaction, error disclosure levels | `Config::test_secret_refs_and_redaction`, `ErrorModel::test_redaction_and_bounds` |
| T16 | Store corruption trusted | Envelope digest re-checked on read | `Store::test_corruption_detected` |
| T17 | Supply-chain substitution of dependencies | Lock file (hashes pending) | **open** (MC-04, MC-54, MC-55) |
| T18 | Side channels / sandbox escape | Out of scope for this element (runtime-owned) | **open**, documented non-goal |
