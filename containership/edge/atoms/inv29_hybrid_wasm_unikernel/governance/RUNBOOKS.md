# INV-29 runbooks (INV29-MC097, MC098)

All commands run from the package directory. `STATE` is the service state directory.

## Day 0 — bootstrap
1. `python -m pip install .` (or vendor the package); confirm `python -c "import inv29_hybrid_wasm_unikernel as p; print(p.__version__)"`.
2. Provision keys: attestation verification keys for INV-27 / INV-44 and the INV-29 record-signing key, from the secret store — never from files in this repo.
3. Start endpoints; expect `/healthz` 200. `/readyz` must stay 503 until `/dependencies` shows pk_core + INV-11/27/44 + PLN-04 AVAILABLE.
4. `python tools/run_tests.py` then `python tools/build_release.py`; archive `conformance/evidence_ledger.jsonl` head as the baseline.
**Exit:** `/readyz` 200, gate artifact archived. **Failure branch:** any dependency ≠ AVAILABLE → stay not-ready; do not override.

## Day 1 — deploy
Follow `governance/ROLLOUT.md`. A `NO_GO` blocks; `CONDITIONAL_GO` requires the listed waivers to be valid for this version and environment.

## Day 2 — operate
* Every change: rerun tests + gate; ledger must chain onto the previous head (`inv29ctl verify-ledger`).
* Run `reconcile` every 60 s and immediately after key revocation / policy change.
* Weekly: `inv29ctl backup --state $STATE --out <dated file>`; quarterly restore drill into a scratch dir + reconcile.
* Policy change: bump `generation`; lowering it requires `rollback_policy` and an incident/change reference.

### Dependency loss (`INV29DependencyUnavailable`)
Admission already fails closed. Check `/dependencies`; restore the dependency; the circuit half-opens after its cool-down. Do **not** bypass with test doubles.

### Attestation failures spike
Check INV-27/INV-44 signer health, clock skew (`clock_skew_s`), recent key rotations/revocations.

### Replay cache saturated
Scale out replicas or shorten `record_ttl_s`; saturation refuses by design.

## Incident response (MC098)
| Sev | Definition | Page | Response | Update cadence |
|---|---|---|---|---|
| SEV1 | invariant breach possible (single-layer admit, import escape, forged record accepted) | on-call + security owner immediately | 15 min | 30 min |
| SEV2 | admission unavailable / fail-closed for > 5 min for any tenant | on-call | 30 min | 1 h |
| SEV3 | degraded latency, elevated refusals for one workload | ticket | 1 business day | daily |
| SEV4 | telemetry / docs defects | backlog | — | — |

**Containment (SEV1):** `inv29ctl disable --state $STATE --reason SEV1-<id> --actor <you>`; revoke suspect keys (`Keyring.revoke`) and run `reconcile` to revoke affected live compositions; preserve the store, ledger and decision stream (copy before any change). **Recovery:** fix → full test + gate → canary → `inv29ctl enable`. **Post-incident:** review within 5 business days, add a regression test, update the threat model.
