# Work order INV58-20260922-missing-components — CLOSED

- **Owner request:** execute `INV58_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md` (41 work packages, 2,770 checkbox lines) on the candidate `inv58_existing_service_mesh_layer_v4.2.0_hardened.zip`.
- **Result:** `inv58_existing_service_mesh_layer_v4.3.0.zip`, stdlib-only runtime (jsonschema for tests only).
- **Bay:** chop-shop standard job, **degraded mode** — this yard copy's `_YARDOFFICE` holds only `work-orders/`: no engine, ledger, `yard_query.py` or published map, and this computer has no device shell. No `ledger recall`, no `yard_query`, no `log-job`.
- **Donor parts:** none copied. Pattern-only reuse of shop conventions from sibling work orders INV44/INV46 (fail-closed release gate with falsifier, lane skips counted as blockers, "roles defined, people unassigned").
- **build-new:** boundary service, capability authz, config subsystem, audit chain, resilience controls, telemetry, integrity verifier, RTM/gate/bench/bootstrap tooling (searched: nothing — no map on this yard copy).

## Outcome
- Requirements C001–C100: 56 VERIFIED_LOCAL / 20 DEFINED / 16 PARTIAL / 8 BLOCKED (4.2.0 was 11 / 25 partial / 64 missing).
- Work packages: 20 implemented-local / 16 partial / 5 blocked (MC-001 MASTER.md, MC-002 owners+ADR approval, MC-036, MC-038, MC-039 need named people).
- Tests 185 (2 pk_core skips), identical under -O; clean copy PASS; bare venv proves missing jsonschema is caught as an unexpected skip.
- Release gate: engineering PASS, production NO_GO exit 3 with named blockers; falsifier test proves GO is reachable.

## Defects found by this pass's own checks
1. Config activation replaced the admission controller mid-traffic → `release without acquire`.
2. Idempotency-key race executed a duplicate migration.
3. Frozen component answered `E_NOT_READY` instead of `E_FROZEN`.
4–6. Fuzz: uppercase `SPIFFE://`, empty `?`/`#`, and non-SPIFFE path characters were accepted (urlsplit normalisation).
7. Redaction wiped the status entry for the dependency named `key`.
8. Config JSON Schema drifted from the validator (7 keys missing).
9. RTM self-referenced its own output.
10. Per-tenant overhead benchmark exposed a per-request deep copy of the whole config (ratio 1.3 → 1.0 after fix); baseline re-recorded.
(+ review finding: tenant-existence probe before authentication.)

## Follow-ups (owner)
- Supply MASTER.md, pk_core (version + sha256), the approved Istio range, a licence, a release signing key; name people in `governance/OWNERSHIP.json`; approve or amend ADR-001; commission an independent review record.
- Run shop-setup on this yard copy so the ledger/map exist, then back-fill:
  `ledger log-job --job "INV58 v4.3.0 checklist execution" --parts "build-new" --outcome "v4.3.0, RTM 56/20/16/8, 185 tests, gate NO_GO" --notes "build-new: mesh boundary service, capability authz, config overlays, audit chain, admission/breaker/fencing (searched: nothing - no map)"`
