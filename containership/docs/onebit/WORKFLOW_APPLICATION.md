# JYRM 1BNCF v3.1.0 workflow application

The ten supplied phase archives are retained byte-for-byte in `onebitflow/source/P01.zip` through `P10.zip`. The application ledger covers all 110 source components and all 275,000 prompt/workflow IDs. Local test success is deliberately separated from source-task promotion.

The adaptation marks 190,000 source units IN_PROGRESS and 85,000 BLOCKED; none are marked PASS. All ten source phase gates remain BLOCKED. Blocking reflects absent external runtimes/hardware/model semantics rather than being silently treated as not applicable.

Run `ONEBIT_FLOW.cmd status`, `ONEBIT_FLOW.cmd check`, `ONEBIT_FLOW.cmd check --deep`, `ONEBIT_FLOW.cmd show PW-001-001-01`, or `ONEBIT_FLOW.cmd execute`. `execute` runs a bounded local phase-aligned test profile and records logs under `_runs/onebitflow`. It does not execute source prose as shell commands and cannot close a source phase gate.
