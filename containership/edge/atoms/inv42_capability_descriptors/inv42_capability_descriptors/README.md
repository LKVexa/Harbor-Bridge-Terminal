# INV-42 — Capability descriptors

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

Capability descriptors are typed serialized bearer handles for resources crossing an ABI boundary. Version 4.2.0 upgrades the runtime to the authenticated `PK_DESCRIPTOR/2` wire format: the issuing table binds schema, table identity, descriptor number, and resource type with a per-table HMAC key, so knowing or guessing a number is not authority.

## Responsibility

The component owns per-workload descriptor tables, monotonic allocation, permanent close, authenticated serialization/import, type-safe resolution, bounded capacity, and explicit table destruction. It does not own the underlying resources, transport confidentiality, remote policy authorship, placement, or cross-site descriptor portability.

## Security invariants

- only the issuing table can mint an accepted descriptor;
- table identity, number, type, and schema are authenticated;
- foreign tables, tampered descriptors, stale closed descriptors, and type confusion fail closed;
- descriptor numbers are never reused within a session;
- live descriptors and total session allocations are bounded;
- process-fork clones are rejected;
- `destroy()` revokes live authority and best-effort zeroizes the table key;
- authentication tags are redacted from `repr` and omitted from status telemetry.

See `SECURITY.md`, `COMPATIBILITY.md`, `OPERATIONS.md`, and `docs/ADR-0001-authenticated-descriptors.md`.

## Public runtime surface

- `DescriptorTable.open(resource_type, resource)` → authenticated `Descriptor` (`PK_DESCRIPTOR/2`)
- `Descriptor.to_wire()` → canonical v2 dictionary
- `DescriptorTable.from_wire(payload)` → strict parse/authentication of a live v2 descriptor
- `DescriptorTable.resolve(descriptor, expect=...)` → underlying resource or typed failure
- `DescriptorTable.close(descriptor)` → `PK_DESCRIPTOR_CLOSE/2` receipt; number is never reusable
- `DescriptorTable.status()` → `PK_DESCRIPTOR_TABLE_STATUS/1` bounded, non-secret counters
- `DescriptorTable.destroy()` → revoke table and best-effort zeroize key

Normative structural schemas are in `schemas/`.

## Limits

- `TABLE_LIMIT = 1024` live descriptors per table.
- `SESSION_ALLOCATION_LIMIT = 1_048_576` total allocations per table session.
- Resource type and owner strings are length-bounded and reject control characters.
- Complete wire descriptors are bearer authority and must not be logged.

## 4.3.0 modules

| Module | Purpose |
|---|---|
| `descriptors.py` | The runtime. Adds `observer=`, `key_provider=`, `fingerprint`, and emergency disable. |
| `outcomes.py` | Classifies each outcome as success, terminal, retryable or degraded, and holds the retry policy. |
| `audit.py` | Tamper-evident audit chain: `AuditLog(path, mac_key=)` can be used directly as an observer, and `verify()` checks the chain. |
| `telemetry.py` | Covers health, the Prometheus `Metrics` exporter, `StructuredLogger`/`redact`, W3C `span`, `explain`, and `fanout`. |
| `transport.py` | `PK_DESCRIPTOR_TRANSPORT/1`, a TLS 1.3 mutual-TLS profile. |
| `delegation.py` | Policy-controlled delegation by re-issuance (see ADR-0002). |
| `adapters.py` | Adapters for the INV-41 source and the INV-13 ABI boundary. |

```python
from inv42_capability_descriptors import descriptors, audit, telemetry
m = telemetry.Metrics()
t = descriptors.DescriptorTable("svc", observer=telemetry.fanout(m, audit.AuditLog("audit.jsonl", mac_key=K)))
```

## Release and certification pipeline

```text
python tools/certify.py --profile dev             # every test; pk_core optional
python tools/certify.py --profile certification   # pk_core required; any skip fails
python tools/coverage_gate.py
python tools/bench.py --soak 30                   # fails the release if a PERF_THRESHOLDS.json limit is exceeded
python tools/traceability.py --check              # all 100 requirements mapped to evidence
python tools/release.py build --out dist && python tools/release.py verify --dist dist --pubkey dist/release-pub.pem
python tools/exit_gate.py                         # writes evidence/PRODUCTION_EXIT.json
```

The current exit verdict is **NOT_ELIGIBLE**. See `WAIVERS.json` for the three blocker waivers and the exit condition for each.

## Running tests

From the directory containing this package:

```text
python -m unittest discover -s inv42_capability_descriptors/tests -v
```

The standalone runtime/security/integration suites (55 tests) execute without `pk_core`. The three suite-level certification tests in `tests/test_component.py` require `pk_core`; when it is unavailable they are explicitly skipped. A production release **must not** treat those skips as certification evidence.

When the framework is available:

```text
set PK_CORE_PATH=<path-containing-pk_core>
python inv42_capability_descriptors/tests/test_component.py
python -m pk_core run INV-42 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-42 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

## Day 0 / day 1 / day 2

- **Day 0:** run the standalone tests, then run the `pk_core` evidence workflow and archive the evidence head.
- **Day 1:** require the suite gate plus integration/security/performance evidence before rollout; a non-passing verdict blocks deployment.
- **Day 2:** re-run on every contract/runtime change, monitor exported descriptor counters, and use `destroy()` for local emergency revocation.

Restart creates a new table session. Old descriptors are not restored and must be re-issued from authoritative resources.

## Audit note

This archive still does **not** contain `MASTER.md` (waiver W-002). The status of every component, with its evidence, is recorded in `MISSING_COMPONENTS.json` (`status_4_3_0`), `REMEDIATION_STATUS.md`, and `TRACEABILITY.json`.
