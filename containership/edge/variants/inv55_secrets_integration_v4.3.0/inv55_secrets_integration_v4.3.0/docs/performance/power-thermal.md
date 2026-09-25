# Power and thermal

| ID | INV55-PERF-POWER | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

**NOT MEASURED.** No power or thermal data exists for 4.3.0 (WVR-004).

Method (for far-edge qualification):
1. Hardware: target edge device class; record CPU model, governor, ambient temperature.
2. Instrument: RAPL (`/sys/class/powercap/intel-rapl`) or external meter at 1 Hz; `thermal_zone*` temps.
3. Workloads via `tools/benchmark.py`: idle 10 min; steady cached resolve at 50 % and 100 % of admitted rate for 30 min; provider-miss mix.
4. Report: J/request, idle W, peak W, max temperature, throttling events.
5. Store in `evidence/` with source revision and host description.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
