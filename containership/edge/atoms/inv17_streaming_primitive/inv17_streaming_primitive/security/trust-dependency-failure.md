# INV-17 Trust-Service Outage Behaviour

**Controls:** C048
**Owner:** UNASSIGNED — owner to fill

Principle: **fail closed** — when a dependency needed to make a security decision is unavailable,
the decision is "deny", the denial is audited, and the error is distinguishable
(`TrustServiceUnavailable`, code `PK_STREAM_TRUST_UNAVAILABLE`, `details["dependency"]`).

| Dependency | Applies? | Failure signal | Behaviour | Code |
|---|---|---|---|---|
| Key service | Yes | `KeyRing.available = False` | `KeyRing.get` raises `TrustServiceUnavailable(dependency="keys")`; `issue` and `verify` fail; registry denies, audits `trust.unavailable`, records decision "trust service unavailable (fail closed)" | `security::KeyRing.get`, `control::StreamRegistry._authorize` |
| Trusted time | Yes | `TrustedClock.available = False` | `TrustedClock.now` raises `TrustServiceUnavailable(dependency="time")`; expiry cannot be evaluated so verification fails; `issue` fails | `security::TrustedClock.now` |
| Policy service | **N/A** | — | Policy is in-process data (`RIGHTS`, `TenantQuota`, `DataPolicy`, `admins`); there is no remote policy decision point to become unavailable. If a host adds one, it must raise `TrustServiceUnavailable` to reuse this path. | — |
| Attestation service | **N/A** | — | INV-17 does not consume attestation; it runs inside an already-admitted process. Attestation is owned by the host/runtime admitting the process. | — |
| Audit sink | Partial | — | `AuditLedger` is in-memory and cannot be "unavailable"; external export of `export_jsonl()` is the integrator's concern. | `security::AuditLedger` |

## What keeps working during an outage

Already-open `Stream` objects continue to operate (read/write/grant/end) because the data plane
does not re-verify tokens. New `open`, `get`, `write` via registry and `transfer` are denied.
Emergency controls (`_admin`) do not depend on keys/time and remain usable.

## Recovery

Setting `available = True` restores service; no cached denial state persists. Previously issued
tokens remain valid until their `exp`.

## Observability

No metric exists for trust outages; detection is via audit events of kind `trust.unavailable` and
`explain()` decisions. See `observability/dashboards.md`.

## Tests (planned)

`tests/test_security.py`, `tests/test_fault_injection.py`, `tests/test_disaster.py`.
No outage drill has been conducted.
