# Day-0 / day-1 / day-2 runbooks (C040, C095, C096)

## Day 0 — bootstrap (empty environment → healthy)
1. `python -m venv .venv && . .venv/bin/activate && pip install --require-hashes -r requirements.lock` (or `pip install .`).
2. `python -m inv25_microvm_devices.pk_bootstrap` — exit 0 required for pk_core-driven gates (exit 3 = not installed).
3. `python -m unittest discover -s inv25_microvm_devices/tests` — all green.
4. Create the store with the environment, verifier config, `state_path` and audit path; `health()["ready"]` must be true.
5. Propose, approve (second person), activate the initial catalogue; archive the activation record.

## Day 1 — deploy
Run `python tools/gate.py run` on the release commit; deploy only a GO gate whose `source_tree` matches.
Follow `docs/rollout.md` stages.

## Day 2 — operate
- Watch dashboards (`docs/telemetry-policy.md`).
- Change: propose → approve → activate with `expected_digest`; widening needs security review.
- Verify audit chain weekly: `AuditLog.verify_file(path)`.
- Backup: copy state file + audit JSONL (append-only) to WORM storage after every activation.
- Restore: place state file; the store re-verifies every catalogue digest on load and refuses tampering.
- Migration: export `active.document`, verify with `catalogue_from_export`, re-activate in the new store.
