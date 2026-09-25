# GAP-10 v4.2.0 Audit Report

Date: 2026-09-22  
Input version: 4.1.0  
Output version: 4.2.0

## Scope

Static audit of the supplied ZIP, source-level hardening, interface/schema review, deterministic unit validation, documentation correction, and package rebuild. No untrusted package code was executed before archive-path inspection and extraction. The wider `pk_core` estate was not included in this ZIP, so estate-level conformance is preserved but cannot be independently proven from this artifact alone.

## Executive findings

| Severity | Finding | Resolution in 4.2.0 |
|---|---|---|
| Critical | Contract claimed power-aware ceilings but implementation did not consume power draw/budget | Fixed: independent power-budget bands now participate in the most-restrictive-wins ceiling |
| High | A brand-new state started `nominal`, allowing a ceiling query before any sensor sample to return full capacity | Fixed: startup is now `critical`/constrained until usable evidence is applied |
| High | Infinite temperatures were accepted as numeric; `-inf` could be classified nominal | Fixed: all non-finite temperature evidence is unusable and fail-closed |
| High | No freshness/clock-skew semantics existed, so stale telemetry could remain authoritative indefinitely | Fixed: bounded age and future skew with fail-closed behavior |
| High | Thresholds and hysteresis were hard-coded and not validated as a coherent policy | Fixed: immutable validated `PowerThermalPolicy` |
| Medium | Core safety tests depended on importing `pk_core`; in a partial checkout they were skipped | Fixed: stdlib-only `model.py` plus standalone unit tests |
| Medium | External interfaces were named but had no schema artifacts | Fixed: three Draft 2020-12 JSON Schemas plus fixtures |
| Medium | Decision output exposed one coarse reason and no telemetry status | Fixed: structured reasons, ceiling fraction, and telemetry status |
| Medium | README claimed a bundled `MASTER.md` that was not present | Fixed: false reference removed and omission documented |
| High | Several custom conformance checks were written into checklist indices whose requirement text did not match the evidence | Fixed: remapped implementation/security/resilience evidence to the actual checklist semantics |
| High | No monotonic timestamp guard existed, permitting older in-window samples to be reconsidered after newer telemetry | Fixed: out-of-order/replayed timestamped telemetry fails closed and cannot advance the accepted timestamp |
| Medium | Checklist coverage wording could be read as production-completeness evidence | Fixed: README now distinguishes requirements inventory from implemented production components |

## Behavioral changes

1. `ThermalState` starts in `critical`, not `nominal`. A safe first reading can immediately recover it to the appropriate band.
2. Temperature, battery, and power constraints are evaluated independently; the highest severity controls the ceiling.
3. Power ratios default to 80% elevated, 90% critical, and 100% emergency/excluded.
4. Missing, invalid, implausible, stale, future-dated, or replayed temperature evidence is critical and cannot cause recovery.
5. Recovery is hysteretic: temperature, battery, and power constraints must clear their configured recovery margins.
6. Emergency capacity is required to be zero by policy validation.

## Compatibility

The original `update(temperature=..., battery=...)` call shape remains valid. New optional arguments are `power_draw_watts`, `power_budget_watts`, `observed_at`, and `now`. Compatibility constants (`ELEVATED`, `CRITICAL`, `EMERGENCY`, `RECOVERY_MARGIN`, `BATTERY_RESERVE`, `BAND_CEILING`) remain available from `model.py` for sibling code.

The output record keeps the original keys (`schema`, `node`, `band`, `ceiling`, `excluded`, `reason`) and adds `ceiling_fraction`, `reasons`, and `telemetry_status`.

## Validation performed

- ZIP path traversal check before extraction.
- Python syntax compilation for package and tests.
- Standalone unit tests for policy validation, startup fail-closed, thermal boundaries, hysteresis, battery reserve/recovery, power budget enforcement, stale/future timestamps, invalid telemetry, and capacity validation.
- JSON parsing for all added schemas and fixtures.
- Version/reference scan to catch stale 4.1.0 pins and nonexistent `MASTER.md` references outside historical changelog text.
- Rebuilt archive inventory and SHA-256 generation.

## Remaining limitations

The package is now a stronger reference implementation, but it is not a complete fleet production service. It still relies on surrounding subsystems for authenticated telemetry, durable controller state, policy distribution, scheduler enforcement, rollout governance, observability backends, and production certification. See `MISSING_COMPONENTS.md` for the concrete inventory.


---

# Addendum — v4.3.0 missing-components pass (2026-09-22)

Input: `gap10_power_thermal_aware_scheduling_v4.2.0_Audited_Hardened.zip` + `GAP10_v4.2.0_MISSING_COMPONENTS_PROFESSIONAL_CHECKLIST.md` (40 components, 2,020 checklist items). All work is stdlib-only; the v4.2.0 kernel (`model.py`) is unchanged.

Results: see `evidence/TEST_REPORT.json`, `evidence/CHECKLIST_EVIDENCE.json`, `evidence/BENCH_2000x5.json`, `evidence/SOAK_200x200.json`. No checklist box is ticked: the checklist requires reviewed evidence and no reviewer has signed (EX-001). Defects found by the new tests are listed in `CHANGELOG.md` 4.3.0 "Fixed during the pass".
