# INV-43 operational runbook (item 47; C096)

Owner / on-call: **UNASSIGNED** (see `governance/OWNERS.json`) — this runbook is not operable until names are filled in.

## Day 0 — install and prove
1. `python -m pip install .` (or vendor the package); Python ≥ 3.10; no runtime dependencies.
2. Verify the artifact: `python tools/verify_release.py` (checks SHA256SUMS, SBOM, provenance statement signature).
3. `python verify.py` and `python -O verify.py` — both must pass. Release CI adds `PK_REQUIRE_CORE=1 INV43_REQUIRE_JSONSCHEMA=1`; with `pk_core` absent this **fails by design** (item 02).
4. Load policy: `Policy.load()` refuses on digest mismatch or a baseline below the INV-43 floor.
5. Enrol collectors: `KeyRegistry.enrol(node)` per node; store secrets in the platform secret store (not config, not logs); grant `collector` role scoped to that node only.
6. Start the service on loopback, or with an `ssl.SSLContext` on any other address.

**Dependency checks:** `/healthz` must be `ready`; `inv43_nodes_with_posture` must equal the fleet size within one TTL.

## Day 1 — go live
- Run `bench/run_bench.py --gate` on production hardware and archive `evidence/perf/`.
- Roll config/policy changes only through `rollout.run(...)` with a named approver; watch `inv43_refusals_total{failure_class="policy_rejection"}` per stage.

## Day 2 — operate
| Symptom | Check | Action |
|---|---|---|
| `health=degraded` | `degraded_nodes()` / `posture_stale` refusals | check collector on those nodes; do NOT raise TTL to "fix" it |
| `health=stalled` | `HealthMonitor.stalled()` | collector heartbeat overdue — network or collector crash |
| refusal spike `attack_suspected` | audit `refusal` events with `attestation_*`/`authz_denied` | treat as incident SEV-2 (INCIDENT_RESPONSE.md) |
| `required_mitigation_missing` after kernel update | `/v1/status/<node>` v2 | mitigation regressed; quarantine node, open ticket with kernel team |
| `internal_error` > 0 | explain record + logs | SEV-2 software defect; decisions keep failing closed |
| need to stop all cross-tenant placement | `POST /v1/control/freeze` (unscoped operator) or config `cross_tenant_placement_enabled=false` via rollout | audit records who did it |
| after restart | quarantine lost? | `restore_controls(verify_file(audit, key, expected_head))` before serving |

Key rotation: `KeyRegistry.rotate(key_id)` → deliver new secret to the collector → old key is revoked immediately.
