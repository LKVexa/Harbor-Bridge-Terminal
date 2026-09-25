# Pending managed-file recovery — UC-2.3.0

## What is protected

The serialized `build`, `load`, `unload`, `run`, `slot-run`, `mount`, `studio-register`, `seal`, `studio-test`, `verify`, and mutating `fabric` commands use the new wrapper. Read-only commands remain available for inspection. Named mutations snapshot registry, MANIFEST.json, SHA256SUMS.txt, the named berth and the entire local `_studio` root. Whole-ship build/verify/studio-test snapshot all berths and the same metadata/studio roots. Seal snapshots registry and ship seals only.

This is deliberately conservative and storage-heavy. The protected resource allowlist cannot name arbitrary host paths. `_engines`, `_runs` logs/old backups, external native effects, already-spawned processes, remote resources are not rolled back. For explicit `--out`, the operation report is staged inside the journal and only published after a COMMITTED or ROLLED_BACK decision, with its transaction status attached. An explicit output path must be outside the workspace or under a non-control `_runs` path; it cannot overwrite sealed source, the control database, objects or transaction backups. A post-commit report-publication failure returns failure with an explicit COMMITTED diagnostic; it does not pretend to undo a committed operation. Default internal run records remain intermediate diagnostics. Use the CLI exit and `UC/TRANSACTION_RESULT/1` record, not a successful-looking internal log alone.

## Commit and failure protocol

1. Under the inherited process lock, inspect pending journals and refuse a second protected mutation until they are resolved. Validate the named resources, input size estimate and free space.
2. Inventory content, file modes and empty directories; copy/fsync all originals; verify copied hashes and write a PREPARED journal. Managed mutation never begins during PREPARING.
3. Allocate a local operation token/generation where applicable, record EXECUTING, and invoke the original command. Success text remains buffered.
4. Record the local operation outcome and durable COMMITTED marker, then publish success output. SQLite identity and managed files are separate stores; lack of a final commit marker requires recovery, not inference from a successful-looking intermediate file.
5. A nonzero outcome or ordinary exception attempts verified old-state rollback. Abrupt termination leaves a pending journal that the next protected command refuses. A failure while rolling back remains RECOVERY_FAILED and can be retried.

There is a deliberate distinction between recoverability and atomic visibility: an unrelated reader can observe intermediate file renames. Cooperating CLI commands honor the lock and pending journal. Hardware power-loss durability depends on the actual filesystem/OS and was not qualified by the process-exit tests.

## Operator procedure

Stop other writers. Preserve the whole workspace, including `_runs/control`, both transaction directories, retained backups and logs, on a separate destination. Then inspect from an open terminal:

```bat
python -X utf8 -B uc.py recover list
python -X utf8 -B uc.py recover inspect TRANSACTION_ID
python -X utf8 -B uc.py lifecycle WORKLOAD_NAME
```

Use the actual 32-character ID printed by `recover list`; the placeholders above are not literal arguments. Compare command, workload, inventories and state. Recover only the intended **pending** transaction:

```bat
python -X utf8 -B uc.py recover rollback TRANSACTION_ID
python -X utf8 -B uc.py recover list
python -X utf8 -B uc.py lifecycle WORKLOAD_NAME
python -X utf8 -B uc.py doctor
```

Rollback verifies every available original before touching live resources. It restores original bytes/modes/empty directories, moves displaced new data into the transaction's `displaced` directory, and advances the local workload generation when an operation was tracked. Repeating an already finished rollback is harmless. A PREPARING journal can be safely abandoned by this same command because its managed action never began. A directory with no journal is reported as PREPARATION_ORPHAN and retained for inspection.

A COMMITTED journal cannot be used as arbitrary historical rollback; that command refuses. General guest snapshot migration, old-release restore and automated pruning remain open roadmap items. Failed backup hashes, an unknown journal schema, unsupported resource paths, insufficient free space or a damaged control database require investigation. Do not edit hashes or delete journals to force success.

After recovery, rerun relevant native and semantic checks and save the new evidence. A completed rollback restores managed files only; inspect externally visible effects and native processes independently. Legacy `_runs/transactions` from UC-2.2.0 are still reported but are not silently migrated into the new coordinator.

## Retention

No automatic deletion is performed. Snapshot metadata, originals, displaced data and old berth backups consume disk. Admission refuses at the documented count/size/free-space defaults. Archive a complete consistent workspace offline before any manual retention maintenance; never prune an unresolved transaction or the local identity database. Production reference-aware GC and storage reservation are not provided in this development pass.
