# UC-2.7.0 Master Workflow Application

The attached 15-volume v1.0.0 series is preserved byte-for-byte under `source/`. It contains **150 components, 15,000 checklist requirements and 375,000 prompt/workflow records**.

Application state:
- component statuses: `{'BLOCKED': 44, 'IN_PROGRESS': 68, 'OPEN': 38}`
- source-task dispositions: `{'BLOCKED': 110000, 'OPEN': 265000}`
- source tasks promoted PASS: **0**

Use `MASTER_FLOW.cmd status`, `MASTER_FLOW.cmd check --deep`, `MASTER_FLOW.cmd show C001.001.T01`, or `MASTER_FLOW.cmd execute`. The execution profile runs bounded local tests aligned to all 15 volumes; it is evidence for this candidate, not a substitute for the individual source acceptance criteria.
