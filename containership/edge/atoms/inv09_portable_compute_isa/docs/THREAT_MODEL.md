# INV-09 threat model (M01–M13 C-021 reviews, M26 tenant isolation, M28 side channels)

Status: **authored by the implementation pass; independent security review not yet performed**
(a named security reviewer must sign the table below — see OWNERS.yaml).

| ID | STRIDE | Threat | Control | Evidence | Residual |
|---|---|---|---|---|---|
| T-01 | Tampering | Manifest/header lies about features | Features derived from bytes only (I-2); binding rule | `test_binding_manifest` | none known |
| T-02 | DoS | Vector-count / nesting / body-size bombs | M13 ceilings before allocation; count ≤ remaining bytes; iterative validation | `test_vector_bombs…`, `test_deep_nesting…`, fuzz slowest ≤ ~3 ms | Python-level CPU cost for 4 MiB ≈ 2.4 s (deadline 10 s) |
| T-03 | Spoofing | Forged/foreign attestation | Ed25519, pinned key ids, revocation list | `test_foreign_key_and_revocation_and_expiry` | key custody is deployment-owned |
| T-04 | Replay | Attestation reused for other bytes/profile/engine/config | every binding compared on admit; expiry; nonce | `test_attestation_cannot_be_moved`, `test_stale_config…` | replay within TTL for the *same* binding is by design |
| T-05 | Tampering (TOCTOU) | Bytes swapped between validation and execution | private snapshot; re-hash at `execute` | `test_toctou` | runner must not re-read external storage |
| T-06 | Downgrade | Old bundle re-activated | strictly increasing epoch | `test_stale_config…` | — |
| T-07 | Confused deputy | Module imports host capability it should not have | deny-by-default host contract, per-profile import classes | `HostImportTest`, `test_profile_refusals` | host function *semantics* out of scope (INV-44) |
| T-08 | Info disclosure | Raw bytes/keys in logs, metrics, audit | redaction rules; digests only; bounded label sets | `test_explain_and_no_raw_bytes`, `test_metrics_cardinality` | — |
| T-09 | Tampering | Cache poisoning | cache key covers all inputs; per-process HMAC | `test_cache_corruption_cannot_admit` | attacker with process memory can read MAC key |
| T-10 | Log injection | Control chars in names/details | `errors.sanitize` | `test_sanitize_and_bounds` | — |
| T-11 | EoP | Parser differential vs engine (we accept what engine mis-parses) | M15 differential vs V8; spec-strict parsing | `evidence/differential.json` (0 false accepts) | only one independent reference so far (checklist asks for two) |
| T-12 | Cross-tenant | Tenant A's contract/profile influences tenant B | contract revision + profile + manifest digest in cache key; no shared mutable request state | `CacheTest` | multi-tenant service deployment not yet built (M26) |

## M28 side-channel assessment
* **Timing of validation** depends on module size/structure only (public to the submitter); no secret
  data is processed during validation. Digest comparison uses `hmac.compare_digest`.
* **Cache-hit timing** reveals whether an identical (module, config) pair was validated before. Across
  tenants this is an oracle for "has another tenant submitted this exact module". Mitigation for
  multi-tenant deployments: add the tenant id to the cache key (one line in `Gate.validate`) — **open
  decision**, tracked in ADR-0005.
* **Signing** uses Ed25519 from `cryptography` (constant-time implementation); keys must live in an
  HSM/KMS for production.
* Spectre-class issues in the *engine* are owned by INV-44 (runtime hardening), not this element.
