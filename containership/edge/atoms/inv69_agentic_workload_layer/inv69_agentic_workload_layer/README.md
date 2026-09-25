# INV-69: Agentic workload layer

**Version:** 4.3.0 (see `CHANGELOG.md`) · **Group:** 01_Source_Inventory · **Series:** Post-Kubernetes Master
Prompt & Workflow Series v4.0.0 · **Checklist:** 100 requirements in `CHECKLIST.json`

**Owners and escalation:** [`ops/OWNERS.md`](ops/OWNERS.md) · **On-call runbook:** [`ops/RUNBOOK.md`](ops/RUNBOOK.md)
· **Security:** [`docs/SECURITY.md`](docs/SECURITY.md)

> **Release status: NO_GO.** `tools/release_gate.py` blocks this release. The named blockers are in
> `evidence/RELEASE_EVIDENCE.json`: owners unassigned, waivers unapproved, pk_core absent, and no
> release approval. Traceability for all 100 controls is in [`ops/RTM.md`](ops/RTM.md).

## What it is

INV-69 governs model-driven agents that plan and request tool calls. The safety kernel
(`runtime.Agent`, unchanged in intent since 4.2.0) enforces:

- per-agent allowlists
- step and cost budgets
- one-use, argument-bound approvals for tools with side effects
- routing to a sandbox tier by risk
- a hash-chained transcript

Version 4.3.0 adds the governed service layer around the kernel (`governed.GovernedRuntime`, see
`docs/ADR-0002-v4.3-service-layer.md`):

| Concern | Module | Controls |
|---|---|---|
| Error codes (stable, machine-readable, redacted) | `errors.py`, `redaction.py` | C026 |
| Run, invocation and approval state machines | `lifecycle.py` | C015 |
| Deadlines, cancellation, trace context, admission and backpressure | `context.py` | C025, C074 |
| Bounded retry with full jitter and a retry budget | `retry.py` | C053 |
| Declarative config, profiles, overlays, provenance, atomic generations | `config.py`, `config/` | C012, C033, C035–C037 |
| Constraint precedence and waivers | `precedence.py` | C019 |
| Trust-service outages, offline mode, degraded modes | `trust.py` | C018, C048, C056 |
| Artifact digest, signature and provenance verification | `artifacts.py` | C045 |
| Versioning, peer handshake, migration | `compat.py` | C016, C027, C093 |
| INV-57/59/70/71 adapters, fencing, failover | `sandbox.py` | C030, C055, C083 |
| Watchdog and status | `health.py` | C052, C071 |
| Telemetry policy, spans, metrics, lineage | `telemetry.py` | C074, C078, C079 |
| Explain view | `explain.py` | C077 |
| Backup and restore | `backup.py` | C095 |

The runtime uses only the Python standard library. `tools/deps_check.py` enforces this.

## Quick start

```python
from inv69_agentic_workload_layer import config, context, governed, sandbox, trust

eff = config.resolve([("base", config.load_layer_file("config/example.base.json"))])
store = config.ConfigStore(eff, author="you")
rt = governed.GovernedRuntime(config=store,
        authz=sandbox.AuthorizationAdapter({"alice": {"search_docs"}}),
        durable=sandbox.DurableExecutionAdapter(),
        fast=sandbox.SandboxAdapter("fast", {"search_docs": lambda a: "ok"}),
        heavy=sandbox.SandboxAdapter("heavy", {"search_docs": lambda a: "ok"}))
for dep in trust.DEPENDENCY_MATRIX:            # wire real health probes here
    rt.trust.report(dep, trust.Health.UP)
ctx = context.CallContext.new(tenant="acme")
rt.start_run("run-1", principal="alice", allow=frozenset({"search_docs"}), ctx=ctx)
print(rt.invoke("run-1", "search_docs", {"q": "x"}, ctx))
print(rt.status())
```

## Commands (run from the folder that contains this package)

```text
python -B    inv69_agentic_workload_layer/tests/run_all.py            # mandatory profile (133 tests)
python -O -B inv69_agentic_workload_layer/tests/run_all.py            # same, optimized mode
python -B    inv69_agentic_workload_layer/bench/perf_suite.py         # -> evidence/PERF_RESULTS.json
python -B -m inv69_agentic_workload_layer.tools.perf_gate
python -B -m inv69_agentic_workload_layer.tools.gen_spec --check      # SPEC.md drift
python -B -m inv69_agentic_workload_layer.tools.rtm                   # RTM + audit rerun
python -B -m inv69_agentic_workload_layer.tools.governance_check
python -B -m inv69_agentic_workload_layer.tools.deps_check --sbom inv69_agentic_workload_layer/evidence/SBOM.json
python -B -m inv69_agentic_workload_layer.tools.release_gate --skip-perf-run [--pk-gate F] [--approval F]
python -B -m inv69_agentic_workload_layer.explain EVIDENCE.json RUN_ID --tenant T
```

The `pk_core` conformance suite (`tests/test_component.py`) is a declared skip lane while `pk_core` is
absent (W-001). The skip is printed by name. It is **not** a certification.

## Documentation map

| Document | Contents |
|---|---|
| `ops/SPEC.md` | Normative tables generated from code: profiles, state machines, error codes, config fields, dependency matrix, precedence, telemetry policy |
| `ops/RTM.md`, `evidence/RTM.json` | 100-control traceability and the v4.2.0 → v4.3.0 delta |
| `ops/RUNBOOK.md`, `ops/ESCALATION.json`, `ops/INCIDENT_TEMPLATE.md` | Operations and incidents |
| `ops/COMPATIBILITY_MATRIX.json`, `ops/EOL.json`, `ops/APPROVED_TECH.json` | Supported versions and technology |
| `ops/WAIVERS.json`, `ops/REVIEWS.json` | Exceptions, deprecations, review schedule |
| `ops/alerts.json`, `ops/dashboards.json`, `ops/PERF_THRESHOLDS.json` | Observability as code |
| `POST_REMEDIATION_AUDIT.md` | What this pass did and did not achieve |
