# ADR-001: Authenticated call context replaces caller-supplied tenant strings
Status: PROPOSED · Date: 2026-09-23
Context: 4.2 accepted `tenant` and `trace_id` as free strings (GAP-005/040).
Decision: a frozen `CallContext` carrying a `Principal` verified from an HMAC-SHA256 runtime credential (key ids, expiry, skew, optional single-use); production mode refuses the string API and principals from untrusted issuers.
Consequences: callers must obtain credentials from the runtime; 4.x API kept for development only (DEBT-001). Asymmetric signatures / workload attestation deferred (ADR-005).
