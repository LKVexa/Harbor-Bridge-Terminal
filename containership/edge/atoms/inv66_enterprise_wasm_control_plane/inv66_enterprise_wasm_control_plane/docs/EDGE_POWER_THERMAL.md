# Edge power / thermal characterisation (MC-048, C068)

**Applicability (proposed): NOT APPLICABLE.** INV-66 is a central governance plane (ADR-0001).
Disconnected edge admission is an unsupported topology (`docs/TOPOLOGY.md`), so INV-66 isn't
planned to run on constrained near/far-edge nodes.

This is a **proposed** N/A disposition. It becomes valid only with architecture-owner approval
recorded in `release/reviews.jsonl` (waiver W-10 until then). No power or thermal measurements were
taken: the build environment is a cloud container with no RAPL or thermal sensors and no
representative edge hardware.

If the decision is reversed, the method to follow is: hardware classes H1 (ARM64 4-core 4 GB) and
H2 (x86 low-power). Idle and load baselines taken with `tools/bench.py --soak-seconds 1800`.
Package power from RAPL/INA219 sampled at 1 Hz. Throttling detected from `/sys/class/thermal`.
Energy per admission = ΔJ / admissions.
