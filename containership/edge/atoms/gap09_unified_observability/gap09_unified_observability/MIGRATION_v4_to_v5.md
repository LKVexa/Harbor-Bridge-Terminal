# Migration - GAP-09 4.1.0 to 5.0.0

Version 5 changes the ingestion trust boundary. The legacy API is retained only to make migration controlled; it is disabled by default.

## Before (4.1.0)

```python
store.submit(
    "node-1",
    samples,
    attested_level="hardware",
    signed=True,
    now=now,
)
```

Those `attested_level` and `signed` arguments were caller assertions, not independently verified evidence.

## After (5.0.0)

1. Implement a `TrustVerifier` adapter backed by GAP-06 device identity/attestation and GAP-07 signature/provenance verification.
2. Have the verifier return a scoped `ReporterAuthority` for the verified reporter.
3. Produce deterministic `PK_SIGNAL_SUBMISSION/2` payload bytes with `SignalStore.canonical_submission_payload(...)` or an implementation conforming to the same signing profile.
4. Call `submit_verified(...)` with a unique submission ID, issued-at timestamp, signature and attestation evidence.

```python
store = SignalStore(trust_verifier=production_verifier)

payload = store.canonical_submission_payload(
    reporter="node-1",
    submission_id=submission_id,
    issued_at=issued_at,
    samples=samples,
)
signature = signer.sign(payload)

store.submit_verified(
    "node-1",
    samples,
    submission_id=submission_id,
    issued_at=issued_at,
    signature=signature,
    attestation=attestation_evidence,
    now=now,
)
```

## Query response additions

`PK_SIGNAL_QUERY/1` is the legacy v4.x response shape. v5 emits `PK_SIGNAL_QUERY/2` because the query contract is intentionally breaking: callers must provide `environment`, and responses now carry `tenant`, `environment`, `site`, `workload`, `sample_at`, `reporter`, `received_at`, and `submission_id` so attribution/provenance survives the ingest boundary.

## Temporary compatibility mode

`SignalStore(allow_legacy_trust=True)` re-enables the old boolean/string trust shim. Use it only for controlled tests while migrating callers. It is not a production authentication or signature-verification mechanism.

## Operational migration checklist

- Deploy the production trust adapter before enabling the v5 ingest path.
- Ensure every reporter has a unique replay-safe submission ID strategy.
- Persist replay state before relying on replay defense across restarts.
- Confirm tenant/environment/site/workload scopes are generated from the authoritative policy source.
- Update consumers for the expanded query response fields.
- Validate wire objects against `schemas/PK_SIGNAL_SUBMISSION_2.schema.json` and `schemas/PK_SIGNAL_QUERY_2.schema.json`. The retained `PK_SIGNAL_QUERY_1.schema.json` documents the legacy response shape for migration testing.
- Run standalone tests, then the full `pk_core` gate with all sibling dependencies installed.
- Remove compatibility mode after all callers have migrated.
