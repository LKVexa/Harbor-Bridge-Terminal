# Applied master — UC-2.4.0

The original master is retained verbatim in `SOURCE_MASTER.md`.

This pass uses the supplied Node LOCAL_VOLATILE/hermit.vws.v2 terminal, adds the allowlisted containership bridge, and retains every original source task in `ledger.jsonl.gz`. Read `../docs/vws/REAPPLICATION.md` before selecting a task.

Run `python -B uc.py vws-workflow check` at the ship root to verify traceability. It deliberately reports engineering completion as NOT_COMPLETE.
