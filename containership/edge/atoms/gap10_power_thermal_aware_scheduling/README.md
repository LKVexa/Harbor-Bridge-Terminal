# GAP-10 - Power/thermal-aware scheduling

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 04_Gap_Subsystems  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

GAP-10 converts node temperature, power-budget pressure, battery reserve, and telemetry freshness into a hard capacity ceiling that downstream placement and elasticity systems must obey.

## Responsibility

Own power and thermal ceilings per node: convert measured thermal and power state into a capacity ceiling and an exclusion verdict, and lower the ceiling before hardware throttling or shutdown does it unpredictably.

## What v4.3.0 adds

A stdlib-only `production/` layer implementing the 40 missing components (P0 enforcement path, P1 operational models, P2 security/observability/resilience, P3 certification/release/governance). Start at `production/controller.py` (decision path) and `docs/COMPONENTS.md` (one design record per component). Evidence per checklist item: `evidence/CHECKLIST_EVIDENCE.md`.

```text
python tools/run_all_tests.py                      # all suites -> evidence/TEST_REPORT.json
python tools/build_evidence.py docs/GAP10_v4.2.0_MISSING_COMPONENTS_PROFESSIONAL_CHECKLIST.md
python tools/bench.py --nodes 2000 --rounds 5      # fleet-scale benchmark
python tools/build_release.py --out dist --source-revision <sha> --key-file <key>
```

## What v4.2.0 hardens

- A standalone standard-library scheduling kernel in `model.py`.
- Validated, immutable `PowerThermalPolicy` configuration.
- Independent temperature, battery, and power-budget constraints.
- Fail-closed handling for missing, NaN, infinite, physically implausible, stale, future-dated, or replayed thermal evidence.
- Immediate escalation and hysteretic recovery for thermal and power pressure.
- Stable machine-readable decision reasons in `PK_POWER_CEILING/1` output.
- JSON Schema documents for `PK_THERMAL_STATE/1`, `PK_POWER_CEILING/1`, and `PK_THERMAL_POLICY/1`.
- Standalone unit tests that run without `pk_core`, plus the existing estate conformance test when `pk_core` is available.

## Owns

- Thermal and power state interpretation per node
- Capacity ceiling derived from that state
- Node exclusion under thermal or power emergency
- Hysteresis on ceiling recovery
- Battery-reserve awareness
- Telemetry freshness rejection

## Explicitly does not own

- Placement decisions
- Capacity targets above the enforced ceiling
- Hardware fan or governor control
- Node lifecycle
- Accelerator allocation
- Sensor attestation itself (delegated to GAP-09 when available)

## Default policy

| Constraint | Elevated | Critical | Emergency |
|---|---:|---:|---:|
| Temperature | 75 C | 85 C | 95 C |
| Power / budget | 80% | 90% | 100% |
| Capacity fraction | 60% | 25% | 0% |

Battery reserve defaults to 15%. Thermal recovery requires a 5 C margin; power recovery requires a 5 percentage-point margin. Telemetry older than 30 seconds, more than 5 seconds in the future, or older than the last accepted timestamp is treated as unusable. Default plausible temperature input is bounded to -100 C through 250 C; deployments should tighten this to their hardware.

Defaults are safe examples, not universal hardware limits. Production deployments should instantiate `PowerThermalPolicy` with validated site- and hardware-specific limits.

## Interfaces

- `PK_THERMAL_STATE/1` - measured temperature, power draw, power budget, battery state, and observation time
- `PK_POWER_CEILING/1` - derived capacity ceiling, exclusion verdict, telemetry status, and reasons
- `PK_THERMAL_POLICY/1` - validated thresholds and hysteresis policy

Reference JSON Schemas are under `schemas/`; example inputs are under `fixtures/`.

## Service-level objectives

- **Emergency exclusion:** zero placements onto a node above its emergency threshold (no error budget).
- **Pre-emption:** ceiling lowered before hardware throttling in 99% of thermal/power ramps (1% may be overtaken by hardware).
- **Stability:** no more than one exclusion flip per node per hysteresis window (1% may exceed under severe sensor noise).

## Running tests

From the package directory:

```text
python tests/test_kernel.py
python tests/test_component.py   # set PK_CORE_PATH if pk_core lives elsewhere
```

Estate-level commands, when `pk_core` is available:

```text
python -m pk_core list
python -m pk_core run GAP-10 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-10 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

## Production-readiness note

`CHECKLIST.json` is a requirements inventory, not proof that every production capability exists in this ZIP. `MISSING_COMPONENTS.md` records the remaining concrete production gaps discovered in the v4.2.0 audit. The prior README referred to a `MASTER.md` file that was not present in the archive; that incorrect reference has been removed rather than fabricating missing source material.

## Day-0 / day-1 / day-2

- **Day 0:** validate policy, import/register the component, run standalone tests, then run the estate conformance gate.
- **Day 1:** canary the policy on representative hardware, confirm ceilings and reasons against live telemetry, and block rollout on a `NO_GO` gate.
- **Day 2:** re-run the gate on every policy or code change, monitor exclusion/flapping/staleness signals, and preserve the evidence chain.

Rollback is the previous approved artifact and policy pair. Emergency disable must be explicit and observable; downstream schedulers must never interpret absence of GAP-10 as unlimited capacity.
