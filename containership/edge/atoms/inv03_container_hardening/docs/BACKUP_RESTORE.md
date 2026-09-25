# Backup, restore and reconstruction — INV-03 (checklist item 58)

State that matters, and where it lives:

| State | File | Authority |
|---|---|---|
| Active + previous signed baseline, epoch | `baseline.json` (atomic rename writes) | signed artifacts; re-verified on every load |
| Exceptions (all transitions) | `audit.jsonl` | the ledger **is** the store — `ExceptionStore` rebuilds from it |
| Every decision, emergency toggle, IDS finding | `audit.jsonl` | hash chain + HMAC seal |

## Backup
1. Record the ledger head externally (ticket, WORM bucket): `python3 -B tools/recurring_review.py --ledger audit.jsonl --seal-key-file seal.key`
   prints `audit_chain.head`. The chain cannot detect tail truncation without this external head.
2. Copy `audit.jsonl` and `baseline.json` together (the two are independent; order does not matter).

## Restore
1. Put both files back. On start, `BaselineStore` re-verifies both signatures — a tampered file refuses to load (fail closed, pods denied, not admitted).
2. Verify the ledger against the recorded head: `AuditLedger(path, key).verify(expected_head=<recorded>)`.
3. If verification fails: keep the webhook denying (it will, with `BASELINE_UNAVAILABLE` or `DEPENDENCY_FAILURE`), restore the previous backup, repeat.

## Reconstruction without a backup
Re-sign and activate the baseline from its source document; exceptions are **not** reconstructed — every
waiver must be re-requested and re-approved. That is the fail-closed choice.

Drill status: exercised in-process only (`test_item23_store_rebuilds_from_ledger`, `test_item53_restart_recovers_state`); a production-storage drill has not been run.
