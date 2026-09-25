# INV-43 - Transient-execution defense

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`  
**Audit status:** 4.3.0 executed the 52-item missing-component remediation checklist. Local gate verdict: **NO_GO** (`conformance/INV43_LOCAL_GATE.json`) — 21 items LOCAL_IMPLEMENTED, 27 PARTIAL, 4 BLOCKED; see `remediation/STATUS.json`.

Transient-execution defense is the tax every isolation boundary pays after Spectre. Mitigations are not free and not universal, so the component keeps a per-node mitigation posture with measured active overhead and refuses cross-tenant co-tenancy when the required mitigation set is incomplete or when SMT is exposed without core scheduling.

## Responsibility

Own transient-execution mitigation state: record which mitigations are active on each node with their measured cost, expose a versioned status record, and fail closed when mutually distrusting tenants would share a node without the required protection.

## Owns

- Per-node mitigation inventory and status
- Measured cost of each active mitigation
- Co-tenancy rules derived from mitigation state
- Sibling-thread policy
- Refusal of cross-tenant co-location when required mitigations are missing
- Versioned JSON Schemas and example fixtures for the local status/decision/error contracts

## Explicitly does not own

- Microcode or kernel mitigation implementation
- CPU procurement
- Workload placement itself
- Isolation-tier implementation
- Workload placement (SCH-01 calls `placement.filter_nodes`; INV-43 never places)
- Hardware-rooted attestation, identity providers, secret stores (integrated by interface only)

## Security behavior

- Unknown/unrecorded required mitigations fail closed.
- Cross-tenant co-tenancy is rejected when any caller-required mitigation is inactive or unknown.
- Cross-tenant co-tenancy is rejected when SMT is enabled without core scheduling.
- Active mitigations require a finite, positive measured cost; inactive/unknown records require zero cost.
- Node, tenant, and mitigation identifiers must be non-empty strings without control characters.
- Refusals expose stable machine-readable codes through `MitigationMissing.to_dict()`.

The baseline required set is `spectre_v2`, `l1tf`, `mds`, and `mmio_stale_data`. A caller may supply a stricter required set; an unrecorded future mitigation in that set is treated as unknown and therefore blocks cross-tenant co-tenancy.

## 4.3.0 components

| Module | Role (remediation items) |
|---|---|
| `defense.py` | policy core; thread-safe; `not_affected` status; v1/v2 reports (27) |
| `collector.py` | sysfs mitigation/SMT read-back with freshness metadata (09, 10) |
| `attestation.py` | HMAC-signed, node-bound, replay-proof read-back envelopes (11) |
| `authz.py` | deny-by-default capability model (12) |
| `policy.py` + `policy/default_policy.json` | trust class × PLN-04 tier × INV-34 lineage → required set; GAP-02 contradictions (13, 16-18) |
| `config.py` | secure defaults, tighten-only overrides, transactional activation, rollback (14) |
| `registry.py` | fleet posture registry: freshness, epochs, restart-closed, controls, explain, audit, metrics (10, 31, 32, 40) |
| `placement.py` | SCH-01 filter adapter with refusal propagation (15) |
| `service.py` | HTTP/JSON boundary: authn, authz, limits, idempotency, negotiation, TLS rule (19) |
| `negotiation.py` | schema version negotiation + forward-compatible reader (20) |
| `auditlog.py` | HMAC hash-chained append-only audit log (22) |
| `resilience.py` | failure taxonomy, health/stall, retry, admission, circuit breaker (28-30) |
| `telemetry.py` | metrics (Prometheus text), redacted structured logs, W3C trace context (37-39) |
| `rollout.py` | staged canary with automatic rollback (45) |
| `bench/run_bench.py`, `perf/thresholds.json` | benchmark + threshold gate (34-36) |
| `tools/` | governance verifier, release builder (SBOM/sums/provenance/signature/evidence/gate), release verifier (01, 03, 08, 23, 49, 50, 52) |
| `docs/`, `ops/`, `governance/`, `SECURITY.md` | ADRs, threat model, runbook, IR plan, recovery, capacity, compatibility, alerts, dashboard, owners, reviews, exceptions (05-07, 24, 41, 46-51) |

## Interfaces

- `PK_MITIGATIONS/1` - `MitigationState.report()`: per-mitigation status and measured cost, total active cost, SMT/core-scheduling state, and the evaluated required set. Schema: `schemas/PK_MITIGATIONS_1.schema.json`.
- `PK_COTENANCY/1` - `MitigationState.may_cotenant()`: affirmative co-tenancy decision. Schema: `schemas/PK_COTENANCY_1.schema.json`.
- `PK_ERROR/1` - `MitigationMissing.to_dict()`: structured fail-closed refusal. Schema: `schemas/PK_ERROR_1.schema.json`. The code enum grew in 4.3.0; treat unknown codes as refusals.
- `PK_MITIGATIONS/2` (new) - adds `not_affected`. `PK_READBACK/1`, `PK_ATTESTED_READBACK/1`, `INV43_CONFIG/1`, `INV43_POLICY/1` (new). See `docs/COMPATIBILITY.md`.

`defense.py` is standalone. `component.py` and `contract.py` are adapters for the external `pk_core` runtime and are loaded lazily from the package root.

## Verification

From the directory containing this package:

```text
python -B inv43_transient_execution_defense/verify.py
python -B -O inv43_transient_execution_defense/verify.py
python -B inv43_transient_execution_defense/tools/build_release.py     # evidence + gate
python -B inv43_transient_execution_defense/tools/verify_release.py    # integrity check
python -B inv43_transient_execution_defense/tools/verify_governance.py --strict   # exits 1 while blockers remain
```

On Windows, `VERIFY.cmd` runs the same verifier using `py -3` when available and falls back to `python`.

Standalone verification always exercises the policy model, input validation, machine-readable errors, version pins, schemas/fixtures, and the no-bare-assert invariant. The `pk_core` conformance tests run when `pk_core` is importable. Release CI should set `PK_REQUIRE_CORE=1` so a missing `pk_core` dependency becomes a hard failure rather than a skip.

Typical external registry checks remain:

```text
python -m pk_core list
python -m pk_core run INV-43 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-43 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

## Day-0 / day-1 / day-2

- **Day 0:** import and validate the standalone policy model; when the external registry exists, run `pk_core run INV-43` and archive its evidence ledger as the baseline.
- **Day 1:** run the external gate with `PK_REQUIRE_CORE=1`; do not treat skipped registry tests as certification.
- **Day 2:** rerun standalone and external gates on policy, schema, mitigation-baseline, runtime, or dependency changes and retain the evidence chain required by the surrounding platform.

The 4.1.0 README referenced a `MASTER.md` source artifact that was not included in the supplied archive. It is still absent in 4.3.0; `provenance/PROVENANCE.json` declares it `missing` under proposed exception EXC-001, and `tools/verify_governance.py` fails if a file by that name appears without a verified digest. Full day-0/1/2 procedures: `docs/RUNBOOK.md`.
