# INV-71 - Heavy agent sandbox

**Version:** 4.3.0 (see `CHANGELOG.md`)
**Group:** 01_Source_Inventory · **Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklists:** 100 controls in `CHECKLIST.json`, plus the 1,730-line production remediation checklist in `governance/INV71_v4.2.0_PRODUCTION_REMEDIATION_MASTER_CHECKLIST.md`
**Production gate:** **NO_GO**. See `evidence/gate-result.json`.

INV-71 owns the heavyweight session sandbox: per-session isolation, clean-snapshot filesystems, egress allowlists, resource limits and verified teardown. This package holds the contract, a dependency-free guest-semantics model (`sandbox.py`), and, new in 4.3.0, a **reference control layer** (`control/`), a rendered Firecracker/jailer launch plan, a reproducible evidence bundle and a fail-closed production gate.

> **Production boundary.** Nothing here is a Firecracker isolation boundary. The launch plan is rendered and never executed. No Firecracker, kernel, rootfs or snapshot bytes exist, and the artifact manifest is `UNPINNED`. There is no PKI, KMS, WORM sink or CI runner, and no accountable owner or approval exists. Read `docs/PRODUCTION_BOUNDARY.md` before relying on anything here.

## Layout

| Path | What it is |
|---|---|
| `sandbox.py` | guest-semantics model (4.2.0; one zone-ID defect fixed in 4.3.0) |
| `control/` | reference control plane: errors/outcomes, lifecycle + fencing, authn/authz, DNS-bound egress, admission/retry/breaker/idempotency/dependency health, config layers + provenance + generation switch, artifact manifest verification, durable signed audit stream, telemetry/explain, compatibility, node qualification, runtime plan + reconciliation, and `controller.py` composing them |
| `schemas/` | v1 (unchanged) and v2 record schemas, plus error, status and config schemas |
| `fixtures/` | deterministic conformance bundle (valid, invalid, golden bytes, `MANIFEST.json`) |
| `governance/` | requirements, failure matrix, perf thresholds, RACI, waivers, review schedule, alert rules, approvals (empty), per-item checklist status |
| `docs/` | ADR-0001 v2 (Proposed), ownership, architecture, security design, operations, observability/testing, production boundary, threat model; `docs/generated/` is rendered from code |
| `tools/` | `build_evidence.py`, `production_gate.py`, `fuzz.py`, `bench.py`, `make_fixtures.py`, `render_docs.py`, `pk_core_probe.py`, `repo_audit.py` |
| `evidence/` | tests, fuzz, bench, probe, qualification, SBOM, provenance, licences, checklist execution, traceability, release manifest, gate result |

## Run

From the directory that contains the package:

```text
python -B -m unittest discover -s inv71_heavy_agent_sandbox/tests -p "test_*.py" -v
python -B -O -m unittest discover -s inv71_heavy_agent_sandbox/tests -p "test_*.py"
python -B inv71_heavy_agent_sandbox/tools/fuzz.py --iterations 20000 --seed 71
python -B inv71_heavy_agent_sandbox/tools/bench.py
python -B inv71_heavy_agent_sandbox/tools/build_evidence.py      # regenerates evidence/, AUDIT_AFTER.json, MISSING_COMPONENTS.md
python -B inv71_heavy_agent_sandbox/tools/production_gate.py     # exit 2 = NO_GO (expected)
```

Runtime dependencies: none. `jsonschema` is optional. Without it, schema-fixture tests report NOT_RUN. The three legacy `pk_core` conformance tests still skip unless a pinned, digest-verified `pk_core` is supplied (`tools/pk_core_probe.py`).

## Status vocabulary

Checklist lines are `IMPLEMENTED_UNREVIEWED`, `PARTIAL`, `OPEN` or `BLOCKED` (`governance/checklist_status.py`). None is `DONE`, because `DONE` needs independent review and the real production path. Controls in `AUDIT_AFTER.json` keep the 4.2.0 definitions: reference-scope work raises `MISSING` to `PARTIAL` only, and nothing becomes `EVIDENCED` from this pass.

## Historical source

The 4.1.0 README referred to a `MASTER.md` master-prompt file. It was never present in any uploaded archive, and this pass declared it unavailable after searching (`docs/PRODUCTION_BOUNDARY.md`). No replacement was fabricated.

## Licence

Unspecified. See `LICENSE_STATUS.md`.
