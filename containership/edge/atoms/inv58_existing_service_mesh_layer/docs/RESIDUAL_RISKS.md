# Residual risks (v4.3.0)

Each needs security/architecture reviewer sign-off (UNASSIGNED) before production; none is waived.

| Id | Risk | Compensating control | Next step |
|---|---|---|---|
| RR-01 | Persisted audit/snapshot files are not encrypted at rest. | 0600 permissions, HMAC integrity, no secrets in content. | Integrate KMS envelope encryption. |
| RR-02 | Operator tokens use a shared HMAC key. | Short TTL, audience, nonce, key via secretref, fail closed on key loss. | Asymmetric (e.g. OIDC/JWKS) verification. |
| RR-03 | Artifact signatures are HMAC, not asymmetric/Sigstore. | Digest + approved-version + revocation checks. | Plug an asymmetric verifier into `Verifier.signature_check`. |
| RR-04 | Bypass detection relies on node agents reporting flows. | Per-tenant audit + metrics; alert on silent nodes. | Cross-check with mesh telemetry (GAP-09). |
| RR-05 | Hash chain cannot see tail truncation by itself. | Head exported in status/audit export for external anchoring. | Periodic external head sealing. |
| RR-06 | Timing side channels not measured. | Identical denial codes for unknown vs forbidden tenant. | Constant-time review of lookup paths. |
| RR-07 | Two-person rule is enforced only by subject name (armer ≠ invoker). | Dedicated role, ≤1 h window, both steps audited. | Bind arming to a distinct approval system. |
| RR-08 | Idempotency cache is not in snapshots. | Fencing refuses stale re-execution after restart. | Persist idempotency results with the snapshot. |
