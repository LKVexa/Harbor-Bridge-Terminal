# PLN-06 — Data plane

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Status:** implementation-complete for in-repo work packages; **production gate FAILS closed** on owner/legal/approval items (see `AUDIT_REPORT.md`)  
**Group:** 02_Synthesis_Planes  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

PLN-06 is the data-plane reference component for residency-aware, bounded bulk-transfer admission. The dependency-free runtime selects a transport tier from payload size and optional locality, refuses illegal residency, bounds concurrent non-inline transfers, records structured decision reasons, and exposes structured metrics. The `pk_core` adapter remains separate so the runtime can be imported and tested when the certification framework is not installed.

## Responsibility

Own transfer admission and routing policy for bulk movement: validate requests, enforce destination residency, select a transport tier, protect the bulk path with bounded backpressure, and require end-to-end integrity verification by the concrete transport.

## Owns

- Transport-tier selection by payload size and explicit locality
- Data-residency admission for transfers
- Separation of inline/control accounting from non-inline bulk accounting
- Bounded non-inline in-flight admission
- Integrity requirement/digest metadata carried on transfer decisions
- Stable structured error codes and runtime metrics

## Explicitly does not own

- Storage backends
- Data-classification policy authorship
- Encryption-key custody
- Workload placement
- Residency policy authorship (GAP-13) and gravity decisions (GAP-14)
- Compute placement after hand-off (PLN-03)
- OS-level sandbox profiles (deployment repo; W-011)

## Runtime API

```python
from pln06_data_plane import DataPlane

plane = DataPlane(
    {"us-east": {"public"}},
    inflight_limit=4,
    per_tenant_inflight_limit=2,
    config_revision="policy-2026-09-22",
    config_author="control-plane",
)
decision = plane.admit(
    tenant="tenant-a",
    workload="importer",
    size=8 * 1024 * 1024,
    classification="public",
    destination="us-east",
    locality="same_node",   # auto | in_process | same_node | same_host_vm | remote
)
try:
    # hand decision to the selected concrete transport
    ...
finally:
    plane.complete(decision)
```

`locality="auto"` preserves the pre-4.2 size-only behavior. Explicit locality acts as a safety floor: `same_node`/`same_host_vm` will not select the inline path, and `remote` will not select inline/local.

## 4.3 governed service (production composition)

```python
from pln06_data_plane import DataPlane, GovernedDataPlane
from pln06_data_plane.security import KeyRing, Authenticator, LabelAuthority, AuditLedger
from pln06_data_plane.lifecycle import TransferJournal, FencingLease
from pln06_data_plane.transports import InProcessAdapter, SharedMemoryAdapter, NetworkRpcAdapter, shm_reader

keys = KeyRing(); keys.add("k-2026-09")                      # bind KeyProvider to KMS/HSM in production
svc = GovernedDataPlane(
    DataPlane({"eu-west": {"public", "pii"}}, inflight_limit=64, per_tenant_inflight_limit=16),
    keyring=keys, authenticator=Authenticator(keys), labels=LabelAuthority(keys),
    audit=AuditLedger(keys, "/var/lib/pln06/audit/audit.jsonl"),
    journal=TransferJournal("/var/lib/pln06/journal/journal.jsonl",
                            lease=FencingLease("/var/lib/pln06/journal/lease.json"), holder="node-1"),
    adapters={"component-model-inprocess": InProcessAdapter(handler),
              "shared-memory": SharedMemoryAdapter(shm_reader),
              "network-rpc": NetworkRpcAdapter(("peer", 7406), peer_id="node-1", secret=peer_secret,
                                               ssl_context=mtls_ctx, server_hostname="peer")},
)
result = svc.submit(credential, workload="importer", data=payload, classification="pii",
                    destination="eu-west", label=signed_label, locality="remote", traceparent=incoming)
```

Request path (precedence order): authenticate → freeze/quarantine/emergency gates → authorize → signed label + digest → residency → capacity → `transport.use.<tier>` → journal → audit → adapter selection → bounded-retry send → receiver manifest verification → PLN-03 hand-off → journal completed → release capacity.

| Module | Work packages |
|---|---|
| `security.py` | #11 authN, #12 authZ, #19 authority guard, #20 signed labels, #22 tenant namespaces, #23 key lifecycle, #24 audit ledger |
| `integrity.py` | #21/#57 chunk manifests, verification, quarantine |
| `transports.py` | #3 adapters + SPI, #58 control-path isolation |
| `lifecycle.py` | #6 outcomes/degraded modes, #7 WAL + fencing, #49 backup/restore |
| `resilience.py` | #13 retry/timeouts, #25 failure model/stall, #26 failover, #28 fault injection |
| `scheduling.py`, `precedence.py`, `config.py` | #9 fairness, #10 precedence, #4/#16/#17 contexts, config, rollback |
| `observability.py` | #34–#40 health, metrics/exporter, logs, tracing, explain, lineage, governance |
| `integrations.py` | #14/#54–#56 GAP-13, GAP-14, PLN-03 protocols + reference fixtures |
| `service.py` | composition, #27 operator controls |
| `bench/perf.py` | #29–#33 baseline, load, efficiency, power/thermal, capacity model + perf gate |
| `tools/` | #47 evidence dossier + production gate, #61 test runner, #62 SBOM, traceability renderer |

## Interfaces

- `PK_TRANSFER/1` — versioned routing decision returned by `DataPlane.admit`
- `PK_RESIDENCY/1` — conceptual site → permitted-classification policy consumed by the runtime
- `PK_TRANSPORT_TIER/1` — conceptual transport-tier configuration; this reference implementation currently pins three built-in tier bounds
- `PK_DATA_PLANE_METRICS/1` — runtime metrics snapshot returned by `DataPlane.metrics`
- `PK_DATA_PLANE_HEALTH/1` — runtime health (deprecated, DEP-001); `/2` — dependency-aware service health
- `PK_PAYLOAD_MANIFEST/1`, `PK_LOG/1`, `PK_AUDIT_RECORD/1`, `PK_DATA_PLANE_EXPLAIN/1`, `PK_DATA_PLANE_CONFIG/1`
- Adapter SPI `PK_TRANSPORT_SPI/1`, component interface `pk:data-plane/transfer@1.0.0`, network protocol `pk06-rpc/1`

Machine-readable JSON Schema 2020-12 definitions are in `schemas/`. Configuration provenance and atomic residency replacement are exposed through `config_snapshot()` and `replace_residency()`.

## Tests and gates

```text
python pln06_data_plane/tools/run_tests.py --out results.json        # 92 tests; unexpected skips fail
python -O pln06_data_plane/tools/run_tests.py --out results-O.json
ruff check pln06_data_plane && mypy pln06_data_plane --config-file pln06_data_plane/pyproject.toml
python -m pln06_data_plane.bench.perf run --quick --out current.json
python -m pln06_data_plane.bench.perf gate --baseline pln06_data_plane/bench/baseline.json --current current.json
python pln06_data_plane/tools/evidence.py --artifact dist/*.whl --out evidence/dossier.json
python pln06_data_plane/tools/release_gate.py --dossier evidence/dossier.json
```

The only permitted skips are the three `pk_core` conformance tests, tied to waiver W-008.

When `pk_core` and the adjacent components are available, the broader series commands remain:

```text
python -m pk_core list
python -m pk_core run PLN-06 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate PLN-06 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

## Service-level objectives in the binding contract

- **Residency correctness:** zero transfers admitted to an illegal residence
- **Control isolation:** zero bulk payloads observed on the control transport
- **Bulk throughput:** p50 local-tier throughput at or above measured line rate minus 10%, with a 5% below-threshold budget

Measured baselines, thresholds, dashboards and alert rules are in `bench/baseline.json`, `docs/REQUIREMENTS.md` §7, and `ops/`.

## Dependency boundaries

GAP-07-equivalent signed labels and INV-37-equivalent payload integrity are implemented in-repo (`security.LabelAuthority`, `integrity`). GAP-13, GAP-14 and PLN-03 are reached through versioned protocols and exercised against reference fixtures; binding to the real services is waived (W-005..W-007).

## Operations

See `docs/RUNBOOKS.md` (day-0/1/2, dependency outages, backup/restore, incident severities), `docs/OWNERSHIP.md`, `docs/VULNERABILITY_POLICY.md`, `docs/TELEMETRY_GOVERNANCE.md`, `docs/REVIEWS.md`, `WAIVERS.json`.

The original `MASTER.md` source artifact is not part of this archive and has not been synthesized (W-009).
