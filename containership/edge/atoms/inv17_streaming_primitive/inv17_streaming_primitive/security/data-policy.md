# INV-17 Data Classification / Encryption / Residency Policy

**Controls:** C047
**Owner:** UNASSIGNED — owner to fill
**Machine-readable companion:** `security/data-classification.json` (maintained separately)

## What INV-17 does with payloads

INV-17 treats elements as opaque (contract non-goal: "Defining what the elements mean"). Elements
are held in memory in `stream::Stream.buffer` only; the component never persists, serialises
(outside `adapters::CanonicalCodec`) or transmits them. Telemetry never includes payloads:
`observability::redact` replaces keys `payload`, `element`, `value` with `[<type> omitted]`.

## `security::DataPolicy`

```python
DataPolicy(require_encryption_at="confidential", allowed_regions=frozenset({"any"}))
DataPolicy.check(classification=..., encrypted=..., crosses_boundary=..., region="any")
```

Classifications (`security::CLASSIFICATIONS`, ordered): `public` < `internal` < `confidential` < `restricted`.

`check` raises `DataPolicyViolation` (`PK_STREAM_DATA_POLICY`) when:
1. `classification` is not one of the four levels;
2. `crosses_boundary=True`, classification >= `require_encryption_at`, and `encrypted=False`;
3. `allowed_regions` does not contain `"any"` and `region` is not listed.

Otherwise it returns `None`.

## Where it is enforced

`DataPolicy.check` is **not called automatically** by `Stream`, `StreamRegistry` or any adapter.
It is a policy primitive that the adapter or host placing a stream across a boundary (e.g. the
INV-20 `HttpBody` owner or a transport layer) must call before forwarding data. `AuditLedger.KINDS`
contains `policy.violation` for integrators to record violations; nothing in this package emits it.

## Encryption

INV-17 performs no encryption. The flag `encrypted` is an assertion supplied by the caller.

## Residency

Streams are instance-local (contract boundary "site"); data does not leave the process through
INV-17. Residency matters only where an adjacent layer transports elements.

## Gaps

- No automatic enforcement; integration obligation is on boundary-crossing adapters.
- Tests: `tests/test_security.py` (planned) for `DataPolicy.check` truth table.
