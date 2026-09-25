# RAMWS dispositions — summary of `ledger/dispositions.jsonl`

Candidate 2.0.0-ramws.1 · profile LOCAL_VOLATILE · 6300 overlay items, every original ID preserved, each carrying its `ram_overlay` and `challenge` from the kit and its prior VWS200 status.

Review mode: owner chose a **full per-item re-audit**. Items whose component is active in this candidate were audited one by one against `ledger/review_inputs/RUBRIC.md` (37 components, outputs in `ledger/review_outputs/C*.jsonl`, `basis: item`); items whose component is inactive under decisions RD-01…RD-04 (PowerShell/.NET hosts, snapshots, distributed/durable profiles, PIM) carry a component-level disposition (`basis: component`) with the decision that makes them NOT_APPLICABLE or BLOCKED named in `note`. No item is marked PASS without a file path or test name in `evidence`.

## Totals

| Status | Items | Meaning here |
|---|---|---|
| PASS | 2220 | implemented and evidenced on this host |
| IN_PROGRESS | 821 | implemented in part, or evidence weaker than the item asks (e.g. self-review, single host) |
| OPEN | 498 | not attempted in this run; nothing blocks it |
| BLOCKED | 690 | cannot be done in this environment (no pwsh/dotnet/Docker, registries blocked, no second host) |
| NOT_APPLICABLE | 2071 | excluded by an approved decision (RD-01…RD-04) or by the kit profile |

Basis: 0 per-item audited, 2400 component-level.

## Movement from the VWS200 ledger

| Prior → now | Items |
|---|---|
| NOT_APPLICABLE → NOT_APPLICABLE | 1983 |
| PASS → PASS | 1801 |
| BLOCKED → BLOCKED | 658 |
| IN_PROGRESS → IN_PROGRESS | 494 |
| OPEN → OPEN | 440 |
| NOT_APPLICABLE → PASS | 174 |
| IN_PROGRESS → PASS | 154 |
| PASS → IN_PROGRESS | 151 |
| OPEN → IN_PROGRESS | 101 |
| OPEN → PASS | 91 |
| NOT_APPLICABLE → IN_PROGRESS | 73 |
| OPEN → NOT_APPLICABLE | 39 |
| IN_PROGRESS → OPEN | 38 |
| PASS → NOT_APPLICABLE | 26 |

## By component

| Component | PASS | IN_PROGRESS | OPEN | BLOCKED | N/A |
|---|---|---|---|---|---|
| ALT01 | 0 | 0 | 0 | 0 | 100 |
| ALT02 | 0 | 0 | 0 | 0 | 100 |
| ALT03 | 0 | 0 | 0 | 0 | 100 |
| C01 | 0 | 0 | 0 | 0 | 100 |
| C02 | 0 | 0 | 0 | 0 | 100 |
| C03 | 0 | 0 | 0 | 100 | 0 |
| C04 | 55 | 18 | 16 | 0 | 11 |
| C05 | 0 | 0 | 0 | 0 | 100 |
| C06 | 0 | 0 | 0 | 100 | 0 |
| C07 | 0 | 0 | 0 | 100 | 0 |
| C08 | 72 | 20 | 1 | 4 | 3 |
| C09 | 37 | 21 | 22 | 11 | 9 |
| C10 | 67 | 18 | 10 | 4 | 1 |
| C11 | 0 | 0 | 0 | 0 | 100 |
| C12 | 0 | 0 | 0 | 0 | 100 |
| C13 | 53 | 19 | 9 | 2 | 17 |
| C14 | 73 | 14 | 6 | 3 | 4 |
| C15 | 53 | 9 | 25 | 9 | 4 |
| C16 | 62 | 18 | 9 | 2 | 9 |
| C17 | 41 | 31 | 24 | 0 | 4 |
| C18 | 49 | 22 | 29 | 0 | 0 |
| C19 | 37 | 30 | 33 | 0 | 0 |
| C20 | 43 | 27 | 30 | 0 | 0 |
| C21 | 71 | 12 | 5 | 0 | 12 |
| C22 | 0 | 0 | 0 | 0 | 100 |
| C23 | 73 | 10 | 6 | 0 | 11 |
| C24 | 71 | 17 | 1 | 4 | 7 |
| C25 | 58 | 32 | 0 | 0 | 10 |
| C26 | 68 | 26 | 0 | 0 | 6 |
| C27 | 75 | 25 | 0 | 0 | 0 |
| C28 | 78 | 19 | 0 | 0 | 3 |
| C29 | 72 | 26 | 0 | 0 | 2 |
| C30 | 67 | 30 | 0 | 0 | 3 |
| C31 | 51 | 27 | 9 | 0 | 13 |
| C32 | 62 | 21 | 9 | 0 | 8 |
| C33 | 64 | 34 | 1 | 0 | 1 |
| C34 | 61 | 19 | 13 | 0 | 7 |
| C35 | 0 | 0 | 0 | 0 | 100 |
| C36 | 83 | 16 | 0 | 0 | 1 |
| C37 | 58 | 24 | 18 | 0 | 0 |
| C38 | 35 | 27 | 28 | 6 | 4 |
| C39 | 30 | 19 | 33 | 2 | 16 |
| C40 | 78 | 14 | 8 | 0 | 0 |
| C41 | 62 | 7 | 15 | 1 | 15 |
| C42 | 0 | 0 | 0 | 0 | 100 |
| C43 | 0 | 0 | 0 | 100 | 0 |
| C44 | 0 | 0 | 0 | 0 | 100 |
| C45 | 0 | 0 | 0 | 0 | 100 |
| C46 | 65 | 15 | 8 | 4 | 8 |
| C47 | 54 | 19 | 18 | 5 | 4 |
| C48 | 47 | 24 | 20 | 1 | 8 |
| C49 | 49 | 29 | 20 | 0 | 2 |
| C50 | 42 | 24 | 23 | 8 | 3 |
| C51 | 0 | 0 | 0 | 100 | 0 |
| C52 | 0 | 0 | 0 | 100 | 0 |
| C53 | 20 | 15 | 18 | 11 | 36 |
| C54 | 30 | 23 | 31 | 13 | 3 |
| C55 | 0 | 0 | 0 | 0 | 100 |
| C56 | 0 | 0 | 0 | 0 | 100 |
| C57 | 0 | 0 | 0 | 0 | 100 |
| C58 | 0 | 0 | 0 | 0 | 100 |
| C59 | 0 | 0 | 0 | 0 | 100 |
| C60 | 54 | 20 | 0 | 0 | 26 |

## What the numbers do not say

A PASS is a self-reviewed PASS on one host (`reviewMode: SELF_REVIEWED` on every row); no human reviewer has signed any item. BLOCKED items are blocked by this environment, not by the design, and would need to be re-run where PowerShell, .NET, Docker or a second host exist. The 32 native kit work packages are recorded separately in `e/native/R01…R32.json` (25 PASS, 4 IN_PROGRESS, 2 NOT_APPLICABLE, 1 BLOCKED) and are what `ledger/release.json` is built from.
