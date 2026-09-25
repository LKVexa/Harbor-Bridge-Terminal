# External consensus / membership contract (MC-007)

Status: **contract defined; implementation BLOCKED on backend selection (EX-001).** INV-05 does not implement consensus; any adapter must prove every clause below against a real multi-node deployment before MC-007 can close.

1. **Quorum (MC-007-01):** all mutating ops and `range` with `serializable=false` require leader + quorum confirmation (linearizable). Watches may be served by any member but must carry revisions assigned by the quorum.
2. **Membership change (MC-007-02):** add as learner → catch up → promote; remove one member at a time; never change more than one voting member per configuration change (or joint consensus). Operator workflow: `docs/operations/RUNBOOK_DAY2.md#membership`.
3. **Partition behaviour (MC-007-03):** minority side refuses writes and linearizable reads with `CSTATE_UNAVAILABLE`; leader loss ⇒ retryable unavailability until election; quorum loss ⇒ fail closed, no writes, readiness false; asymmetric connectivity ⇒ leader must step down on check-quorum failure.
4. **Stale leaders (MC-007-04):** a deposed leader cannot commit (term check) — verified by a partition test that asserts zero acknowledged conflicting writes via the linearizability checker.
5. **Member identity (MC-007-05):** member ids persisted with the data dir; a replaced member gets a new id; a removed member may not rejoin with old data.
6. **Churn tests (MC-007-06):** membership changes while the mixed workload of `linearizability.py` runs; histories must check linearizable.
