# INV-20 - HTTP component worlds

**Version:** 4.3.0 (see `CHANGELOG.md`; canonical source `_version.py`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

An HTTP component world is the smallest useful thing a serverless component can be: a world that imports an outgoing-request capability and exports an incoming-request handler, with both bodies as streams and trailers as completions. Because the world is explicit, a component that was never granted outgoing HTTP simply cannot make a call.

## Responsibility

Own the HTTP world definition and its enforcement: the handler export, the outgoing capability import, body streaming, trailer completion, and refusal of any egress the world did not grant.

## Owns

- The incoming-handler export shape
- The outgoing-request capability import
- Request and response bodies as streams
- Trailers as completions
- Egress allow-listing per world

## Explicitly does not own

- TLS termination
- Routing between components
- Transport implementation
- Business logic
- Placement

## Non-goals

- Implementing TLS
- Routing
- Owning the HTTP transport
- Buffering whole bodies in memory

## Interfaces

- `body` - PK_HTTP_BODY/1 - a request or response body as a stream
- `handler` - PK_HTTP_HANDLER/1 - the exported incoming-request function
- `outgoing` - PK_HTTP_OUTGOING/1 - the imported egress capability

## Service-level objectives

- **egress containment** - zero requests to hosts outside the world's allow-list (error budget: no budget)
- **streaming** - no body fully buffered before forwarding (error budget: no budget)
- **handler latency** - p99 handler dispatch under 1ms excluding user code (error budget: 1% may exceed)

## Layout (4.3.0)

| Module | Checklist component | What it enforces |
|---|---|---|
| `runtime.py` | baseline | sync reference world, host canonicalisation, bounded stream, completion |
| `errors.py` | 4 | stable error codes, categories, retryability, bounded details |
| `protocol.py` | 4 | typed method/scheme/authority/path, validated `Fields`, trailer-smuggling guard, status |
| `egress.py` | 5 | allow-list + resolved-address policy, rebinding/mixed-answer/CNAME defence, pinned connect IP, redirects |
| `identity.py` | 6, 10, 21 | principals, identity verification, HMAC capabilities, delegation, revocation, kill switch, quarantine, fail-closed PDP |
| `config.py` | 8 | `INV20_CONFIG/1` schema, secure defaults, narrowing-only overlays, provenance, atomic activate, auto/operator rollback |
| `aio.py` | 3, 11, 14 | async lifecycle state machine, backpressure, deadlines, retry/backoff, circuit breaker, admission/fairness |
| `health.py` | 12 | lifecycle phases, readiness, stall/saturation/drain detection, machine-readable snapshot |
| `observability.py` | 16, 17 | bounded metrics, redacted structured logs, trusted trace propagation, hash-chained signed audit log + verifier |
| `wit/`, `witgen.py`, `_wit_generated.py` | 2 | WIT worlds `service`, `service-with-egress`, `middleware`; validator; freshness check |
| `pk_compat.py` | 1 | pk_core version range, shadowing check, precise BLOCKED reason |
| `evidence_gate.py`, `components.json` | 25, 27 | C001–C100 records, traceability, independent GO/NO_GO/BLOCKED gate |
| `tools/release.py`, `pyproject.toml` | 9, 26 | wheel build, content inspection, SBOM, provenance, clean-room install + tests |
| `fuzz/`, `bench/` | 19, 15 | seeded property fuzzing with oracles; benchmark + regression/SLO gate |
| `docs/` | 7, 13, 20–24 | ADRs, state machine, TLS contract, failure catalog, capacity, observability, runbooks, policy, ownership, threat model |
| `.github/workflows/inv20-ci.yml` | 27 | CI matrix, fuzz nightly, protected release job |

## Verification

```text
python VERIFY.py                      # from inside the package directory, or:
python -m inv20_http_component_worlds.VERIFY
```

Exit **0** = GO, **1** = a check failed or evidence is stale/tampered, **2** = BLOCKED (nothing failed, but
mandatory items — pk_core, upstream WIT pin, signing, owners, drills — cannot be closed here).
Individual suites (run from the directory containing the package):

```text
python -m unittest inv20_http_component_worlds.tests.test_runtime ...   # see VERIFY.SUITES
python -O -m unittest ...                                               # optimized mode
python -m inv20_http_component_worlds.witgen --check
python -m inv20_http_component_worlds.fuzz.fuzz_parsers --iterations 20000 --seed 1
python -m inv20_http_component_worlds.bench.run_bench
python -m inv20_http_component_worlds.tools.release --out dist/
python -m inv20_http_component_worlds.evidence_gate collect && python -m inv20_http_component_worlds.evidence_gate gate
```

With pk_core installed (`pip install .[conformance]`; PK_CORE_PATH injection was removed in 4.3.0):

```text
python -m pk_core run INV-20 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-20 --out conformance/PK_GATE_RESULTS.json
```

## Day-0 / day-1 / day-2

See `docs/ops/RUNBOOKS.md` (bootstrap, deploy, operate, incident), `docs/ops/RELEASE_AND_ROLLBACK.md`
(rings, automatic rollback, egress kill switch `CapabilityStore.revoke_all()`, quarantine) and
`docs/ops/STATE_AND_RECONSTRUCTION.md`.

## Status

See `MISSING_COMPONENTS.md` for the per-component status after this pass, `AUDIT_REPORT.md` for the
audit narrative, and `evidence/traceability.json` for the machine-readable C001–C100 dispositions.
The pinned action SHAs in the CI workflow were written from reference and must be re-verified against
the upstream action repositories before the workflow is enabled.
