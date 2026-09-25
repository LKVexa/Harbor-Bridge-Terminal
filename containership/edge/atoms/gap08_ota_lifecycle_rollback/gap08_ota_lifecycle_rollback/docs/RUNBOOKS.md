# GAP-08 operator runbooks (v4.3.0)

All commands below are controller API calls; every call is authorized, rate-limited and audited. Error responses are `PK_ERROR/1` envelopes — act on `code` and `retry`, never on message text.

## Normal deployment

1. Obtain a GAP-07 `PK_VERIFICATION/1` statement for the bundle (subject **and** `sha256:` digest).
2. `create(bundle, waves, environment, verification, compat_profile, lineage)` — pins the rollback target from *authenticated* node queries, admits the artifact, reserves scope. Expect `phase=admitted`.
3. For each wave: `step` → wait ≥ `settle_s` → submit GAP-09 evidence to `gate`. `healthy=True` advances; anything else rolls back.
4. If `phase=deferred`: wait for nodes to reconnect, `reverify` if the GAP-07 statement expired, then `retry_deferred` → `gate`.
5. `reconcile` before closing the change; expect `recommendation: in sync`.

## Rollback (operator)

`rollback(reason)`. Two-phase: intent is committed first, then fenced commands, then the outcome. If the call dies midway, run `recover(rollout_id)` from any controller — it finishes the rollback idempotently. Check `explain` for per-node outcomes.

## Rollback incomplete <a id="rollback-incomplete"></a>

Alert `Gap08RollbackIncomplete`. The listed nodes are **quarantined on the bad bundle**. Do not start new rollouts touching them (the conflict detector and blast-radius engine already count them unavailable). Go to *Quarantine recovery*.

## Quarantine recovery <a id="quarantine-recovery"></a>

1. Remediate the node out of band (console rollback, reimage from golden image, hardware swap → re-enrol identity).
2. Requester (`quarantine.release`) opens an approval bound to `release:<rollout>:<node>` with justification.
3. A different principal with `rollout.approve` approves.
4. `release_quarantine(node, approval_id, evidence_note)` — refused unless an authenticated, attested query shows the node on the pinned target.

## Emergency stop / freeze

* Freeze everything: `freeze(scope="global")`. Freeze one rollout: `scope="rollout", target=<id>`. Disable an artifact everywhere: `scope="artifact", target=<sha256:…>`.
* Freezes stop step/retry immediately; rollback, pause, quarantine, reconcile still work.
* Lifting requires `emergency.unfreeze` **plus** a second-person approval bound to `<scope>:<target>`.

## Degraded dependencies <a id="degraded-dependencies"></a>

Alert `Gap08DependencyFailClosed`. See the policy table in `dependencies.py` / `ARCHITECTURE.md`. Forward progress halts on any required dependency; rollback continues unless the store, lease, identity, supervisor, time or authz is down. Audit-sink outage: rollback proceeds and events are **buffered** (`sealed < audit_events` in `status`); they are sealed automatically on the next operation after the sink recovers — forward operations refuse until then.

## Deferred nodes <a id="deferred-nodes"></a>

Alert `Gap08DeferredAging`. `explain` shows reason/attempts/next attempt. Escalated entries (attempt budget or 7-day expiry) need a human decision: fix connectivity and `retry_deferred(force=True)`, or roll back.

## Reconciliation <a id="reconciliation"></a>

Alert `Gap08Drift`. `reconcile` classes: `installed_while_deferred` (unknown-outcome install actually landed — retry through a gate to bring it under evidence), `unexpected_version` (out-of-band change — investigate, quarantine if unsafe). Unreachable nodes stay in `needs_reconcile`. Never start new mutations while drift is unexplained.

## Integrity failure <a id="integrity-failure"></a>

Alert `Gap08StateIntegrity` (`GAP08-E008-INTEGRITY`). Treat as a security incident: stop the controller, preserve the store and sink, run `FileWormSink.verify` and `audit_sink.reconstruct(rollout_id)` to rebuild the authoritative chain from the sealed copy, compare with the store, escalate to security (see `OWNERS.md`).

## Disaster recovery <a id="disaster-recovery"></a>

Objectives (proposed, to be ratified by the owner): **RPO 0** for committed transitions (every commit is fsync'd and replicated by the production backend; backups are additionally taken every 15 min), **RTO 30 min** to a controller able to roll back, 2 h to forward progress.

1. Provision an isolated store location; `FileStateStore.restore(backup_dir, target)` — verifies the manifest digest and every record digest; refuses a non-empty target.
2. Start a controller with a **new lease service high-water ≥ the old** (restore `leases.json` or bump), so every pre-disaster fence is dead.
3. Verify the audit sink (`verify`), and for each rollout `verify_against` the restored history; reconcile any gap from `reconstruct`.
4. `recover(rollout_id)` for each non-terminal rollout, then `reconcile` against the real fleet **before** any `step`.
5. Declare recovery only when every rollout is `in sync` or explicitly quarantined.

## Interpreting telemetry

| Signal | Meaning | Action |
|---|---|---|
| `gap08_gate_verdicts_total{outcome="evidence_rejected"}` | evidence stale/replayed/mis-bound | check GAP-09 pipeline, clocks |
| `gap08_commands_total{outcome="unknown"}` | no authenticated ack before deadline | network/node health; reconcile |
| `gap08_rollbacks_total{complete="false"}` | rollback left nodes behind | quarantine recovery |
| `gap08_state_restore_failures_total` | snapshot/audit verification failed | integrity-failure runbook |
| `gap08_drift_nodes` | observed ≠ recorded | reconciliation runbook |

## Escalation

Operational: on-call → service owner. Security (integrity failure, forged acks/evidence, key compromise): security owner immediately. Names and channels live in `OWNERS.md` (currently **unassigned** — must be filled before production).
