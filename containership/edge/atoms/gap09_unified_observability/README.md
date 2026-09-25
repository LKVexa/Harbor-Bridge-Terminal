# GAP-09 - Unified observability

**Version:** 5.0.0  
**Group:** 04_Gap_Subsystems  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

Unified observability is the estate's evidence layer. Signals are tenant/environment/site/workload attributed, absence is distinct from numeric zero, and reads expose staleness. Version 5.0.0 hardens the reference data plane so production ingestion must cross a verifier-backed trust boundary rather than accepting caller-supplied `signed=True` / attestation strings as proof.

## Security model in 5.0.0

Production code should call `SignalStore.submit_verified(...)` with a configured `trust_verifier`. The verifier is the adapter point for GAP-06 device identity/attestation and GAP-07 artifact/signature verification and must return a scoped `ReporterAuthority`. Reporter scope is then enforced against tenant, environment, site and workload before any state change.

The old `submit(..., attested_level=..., signed=...)` API remains only as a migration/conformance shim and is **disabled by default**. Enabling `allow_legacy_trust=True` reintroduces caller-asserted trust and is not a production security boundary.

`HMACFixtureVerifier` is deliberately a stdlib test fixture. It provides deterministic signature tests without external crypto packages; it is not a substitute for production asymmetric signatures or hardware attestation.

## Hardened runtime behavior

- Entire batches are validated before mutation.
- Empty and oversized batches are refused.
- Reporter/signal/tenant/environment/site/workload identifiers are non-empty, bounded strings.
- Values must be finite numeric values within binary64 magnitude; booleans, NaN, infinities and pathological huge integers are refused.
- Timestamps are bounded to the non-negative signed-64-bit domain; future-dated samples and query-time regressions fail closed.
- Equal-timestamp conflicting values or conflicting reporters are rejected; exact same-reporter duplicates are idempotent.
- Accepted latest values retain reporter, submission ID and receive-time provenance, and query responses carry tenant/environment/site/workload attribution.
- Late samples never overwrite newer state.
- Verified reporter authority is scoped to tenant/environment/site/workload.
- Submission IDs provide bounded replay detection.
- Cross-tenant reads are refused by the in-process scope check. Production network callers still require an authenticated query-principal adapter; `caller_tenant` must never be accepted directly from an untrusted client.
- Staleness uses the configured store threshold rather than a global constant.
- Signal/reporter cardinality, batch size, rejection history and replay history are bounded.
- Shared state is guarded by a re-entrant lock.
- Structured exceptions expose stable machine-readable error codes.
- Internal counters expose ingestion, rejection, replay-cache, cardinality and isolation-denial state.

## Interfaces

- `submit` — `PK_SIGNAL_SUBMISSION/2`, signed replay-identified batch from one verified reporter.
- `query` — `PK_SIGNAL_QUERY/2`, tenant-scoped latest-value read with staleness.
- `catalogue` — `PK_SIGNAL_CATALOGUE/1`, declared signal names, types, units and descriptions.

Reference JSON Schemas are under `schemas/`. The catalogue schema exists, but a production catalogue service/registry is still missing; see `MISSING_COMPONENTS.md`.

## Scope boundaries

This package is a hardened reference component, **not yet a complete unified telemetry platform**. It does not yet implement end-to-end log, trace, profile, Wasm, microVM, host and network collection/export paths. It also does not bundle `pk_core`, so the 100-item master gate cannot be executed from this archive alone.

## Tests

On Windows, from inside the package folder:

```text
VERIFY.cmd
```

Or from the directory containing `gap09_unified_observability`:

```text
python -m unittest discover -s gap09_unified_observability/tests -v
```

The standalone runtime tests do not require `pk_core`. The `test_component.py` orchestration tests are skipped when `pk_core` is unavailable. A skipped orchestration gate must not be interpreted as production certification.

When `pk_core` is installed or `PK_CORE_PATH` points to it, also run:

```text
python gap09_unified_observability/tests/test_component.py
python -m pk_core run GAP-09 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-09 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

## Day 0 / day 1 / day 2

- **Day 0:** install/wire the real GAP-06/GAP-07 trust adapter; configure bounds; run standalone tests and the `pk_core` gate; archive the evidence head.
- **Day 1:** canary the verified submission path, monitor rejection/replay/isolation counters, and refuse rollout on gate failure.
- **Day 2:** re-run conformance after contract/runtime changes, verify evidence-chain continuity, review trust/key policy, and track the unresolved items in `MISSING_COMPONENTS.md`.

## Included audit artifacts

- `AUDIT_REPORT.md` — findings, applied fixes and verification status.
- `MISSING_COMPONENTS.md` — prioritized gaps remaining before this can reasonably claim production-complete unified observability.
- `SECURITY.md` — trust boundary, hardening rules and known security limitations.
- `MIGRATION_v4_to_v5.md` — migration from caller-asserted trust to the verified v5 submission path.
- `AUDIT_SUMMARY.json` — machine-readable version, test, gap-count and certification-status summary.
- `MANIFEST.sha256` — SHA-256 hashes for every packaged file except the manifest itself.

The original README referenced `MASTER.md`, but that file was not present in the uploaded archive. It remains listed as a missing source artifact.
