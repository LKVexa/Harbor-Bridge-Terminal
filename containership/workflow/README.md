# Applied series — UC-2.3.0 development pass

`series.zip` is the byte-identical attached 2.0.0 nested task pack. Extract it separately for its 96 Markdown component task lists. `ledger.jsonl.gz` is a separate application-status record for all 96,000 original task IDs; it does not change the source.

- `python -X utf8 -B uc.py workflow status` reports this pass.
- `python -X utf8 -B uc.py workflow check` verifies source identity and complete task accounting, NOT engineering completion.
- `python -X utf8 -B uc.py workflow show UC-M01.04-C002-T03` shows exact source text and its related implementation.

`components.json` preserves all component acceptance criteria and records remaining blockers. `APPLICATION.json` contains counts and prerequisite order. IN_PROGRESS means a related implementation was delivered, not that the entire subtask or focus has passed. Optional exclusions only apply to this profile. No component or task is promoted to complete.
