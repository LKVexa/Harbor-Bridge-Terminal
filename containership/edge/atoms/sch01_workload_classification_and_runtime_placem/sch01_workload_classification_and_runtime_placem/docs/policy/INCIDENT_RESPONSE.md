# Incident response (MC-55) — PROPOSED, paging tree UNASSIGNED
Severity: SEV1 unsafe placement / cross-tenant exposure / audit chain break; SEV2 scheduler unavailable; SEV3 degraded.
1. Contain: `operator disable` (kill switch) or `freeze`; quarantine suspect nodes.
2. Preserve: copy journal.jsonl, audit.jsonl, epoch; record head hashes (`tools/evidence_bundle.py`).
3. Verify: `audit.verify_chain`, `state.Journal(...).replay()`.
4. Communicate: owner -> affected tenants (template TBD by owner).
5. Recover: RB-03/RB-04; re-enable only after verification. 6. Post-incident review within 5 business days.
