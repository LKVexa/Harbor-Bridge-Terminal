"""MC-007 - Distributed atomic placement commit protocol (GAP03-TXN/1).

Saga with an idempotent, fenced prepare/commit/abort journal:

  BEGIN -> PREPARED (ledger reservation, provisional)
        -> COMMITTED  (downstream SCH-01 accepted + ledger commit)
        -> ABORTED    (deterministic downstream refusal / timeout before send; ledger abort = compensation)
        -> UNKNOWN    (downstream outcome lost) -> recover() queries SCH-01 by txn id and finalizes.

Every record binds the immutable decision inputs (workload ref, candidate-set
digest, topology generation, ledger state token, entitlement generation,
config generation, scoring version).  Every step carries the current fencing
token; a superseded leader's writes are refused by the ledger, the journal and
the downstream harness.  Re-invoking any step with the same txn id returns the
prior terminal state.
"""
from __future__ import annotations

import time
import uuid

from .. import scheduler as sch
from . import canonical
from .durable import DurableStore
from .errors import SchedulerError, classify

SCORING_VERSION = "gap03-score/2"
TERMINAL = ("COMMITTED", "ABORTED")


class TxnJournal(DurableStore):
    KIND = "txn"

    def initial_state(self):
        return {"fence": 0, "txns": {}}

    def apply(self, state, op):
        if op.get("fence", 0) < state["fence"]:
            raise SchedulerError("FENCED", "stale fencing token")
        state["fence"] = op.get("fence", 0)
        tx = state["txns"].get(op["txn"])
        if op["type"] == "begin":
            if tx is not None:
                return tx["state"]
            state["txns"][op["txn"]] = {"state": "BEGIN", "inputs": op["inputs"], "node": None, "history": ["BEGIN"],
                                        "created": op["now"], "deadline": op["deadline"]}
            return "BEGIN"
        if tx is None:
            raise SchedulerError("INVALID_ARGUMENT", "unknown txn")
        if tx["state"] in TERMINAL:
            return tx["state"]
        new = op["state"]
        allowed = {"BEGIN": {"PREPARED", "ABORTED"}, "PREPARED": {"COMMITTED", "ABORTED", "UNKNOWN"},
                   "UNKNOWN": {"COMMITTED", "ABORTED"}}
        if new not in allowed[tx["state"]]:
            raise SchedulerError("CONFLICT", f"illegal transition {tx['state']} -> {new}")
        tx["state"] = new
        tx["history"].append(new)
        if op.get("node"):
            tx["node"] = op["node"]
        if op.get("reason"):
            tx["reason"] = op["reason"]
        return new


def decision_inputs(*, workload: dict, candidates: list[str], snapshot, ledger_token: str, entitlement_generation: int,
                    config_generation: int) -> dict:
    return {"workload_id": workload["id"], "workload_version": workload.get("version", 1),
            "candidate_digest": canonical.digest(sorted(candidates)), "topology_generation": snapshot.generation,
            "ledger_token": ledger_token, "entitlement_generation": entitlement_generation,
            "config_generation": config_generation, "scoring_version": SCORING_VERSION}


class PlacementCoordinator:
    def __init__(self, *, journal: TxnJournal, ledger, topology_snapshot, downstream, fence, clock=time.time,
                 config_generation=lambda: 0, prepare_ttl: float = 30.0, controls=None, metrics=None, explain=None, tracer=None):
        self.tracer = tracer
        self.journal, self.ledger, self.snapshot, self.down = journal, ledger, topology_snapshot, downstream
        self.fence, self.clock, self.cfg_gen, self.ttl = fence, clock, config_generation, prepare_ttl
        self.controls, self.metrics, self.explain = controls, metrics, explain

    def _j(self, txn, state, **kw):
        return self.journal.submit({"type": "step", "txn": txn, "state": state, "fence": self.fence(), **kw})

    def place(self, *, txn: str | None, workload: dict, anchor: str, candidates: list[str], tenant: str, slots: int = 1,
              spread_from=(), deadline_s: float = 5.0) -> dict:
        txn = txn or str(uuid.uuid4())
        existing = self.journal.state["txns"].get(txn)
        if existing and existing["state"] in TERMINAL:
            if self.metrics:
                self.metrics.inc("gap03_idempotent_replays_total")
            return self.result(txn)
        if existing and existing["state"] == "UNKNOWN":
            return self.recover_one(txn)
        fence = self.fence()
        snap = self.snapshot()
        if self.controls is not None:
            self.controls.check("placement.commit", scope={"tenant": tenant, "workload_class": workload.get("class", "")})
        verdict, _, ent_gen = self.ledger.verdict(tenant, slots)
        scored = sch._score_snapshot(snap, anchor, candidates, spread_from=spread_from)
        inputs = decision_inputs(workload=workload, candidates=candidates, snapshot=snap, ledger_token=verdict.state_token,
                                 entitlement_generation=ent_gen, config_generation=self.cfg_gen())
        now = self.clock()
        self.journal.submit({"type": "begin", "txn": txn, "inputs": inputs, "now": now, "deadline": now + deadline_s,
                             "fence": fence})
        span = self.tracer.start("durable_claim", txn=txn) if self.tracer else None
        if self.explain is not None:
            self.explain.record(txn=txn, tenant=tenant, workload=workload, inputs=inputs, scored=scored, fairness=verdict,
                                snapshot_nodes={k: list(v) for k, v in snap.nodes.items()},
                                sources={"anchor": anchor, "spread_from": list(spread_from),
                                         "trace_id": span["trace_id"] if span else None})
        if not verdict.allowed or not scored:
            self._j(txn, "ABORTED", reason=verdict.reason if not verdict.allowed else "no_candidates")
            return self.result(txn)
        try:
            res = self.ledger.submit({"type": "prepare", "op_id": f"{txn}:prepare", "claim_id": txn, "tenant": tenant,
                                      "slots": slots, "owner": f"txn:{txn}", "fence": fence, "expires_at": now + self.ttl,
                                      "expected_token": verdict.state_token, "entitlement_generation": ent_gen, "txn": txn})
        except SchedulerError as exc:
            if exc.code == "FENCED":
                raise
            res = {"ok": False, "code": exc.code}
        if self.metrics and res.get("code") == "STALE_STATE":
            self.metrics.inc("gap03_stale_rejections_total", kind="ledger_token")
        if span is not None:
            self.tracer.end(span, error_code=None if res.get("ok") else res.get("code"))
        if not res.get("ok"):
            self._j(txn, "ABORTED", reason=res.get("code", "prepare_failed"))
            return self.result(txn)
        node = scored[0].node
        self._j(txn, "PREPARED", node=node)
        dspan = self.tracer.start("downstream_commit", txn=txn) if self.tracer else None
        try:
            if self.controls is not None:  # a freeze created after prepare must be honoured before commit
                self.controls.check("placement.commit", scope={"tenant": tenant, "node": node,
                                                               "workload_class": workload.get("class", "")})
            out = self.down.place({"txn": txn, "node": node, "tenant": tenant, "slots": slots, "fence": fence,
                                   "idempotency_key": txn, "inputs_digest": canonical.digest(inputs)})
        except Exception as exc:  # noqa: BLE001
            err = classify(exc)
            if dspan is not None:
                self.tracer.end(dspan, error_code=err.code)
            if err.code in ("DEADLINE_EXCEEDED", "DEPENDENCY_UNAVAILABLE", "INTERNAL"):
                self._j(txn, "UNKNOWN", reason=err.code)
                return self.recover_one(txn)
            self.ledger.submit({"type": "abort", "op_id": f"{txn}:abort", "claim_id": txn, "fence": fence})
            self._j(txn, "ABORTED", reason=err.code)
            return self.result(txn)
        if dspan is not None:
            self.tracer.end(dspan)
        return self._finish(txn, out, fence)

    def _finish(self, txn, out, fence):
        if out.get("status") == "placed":
            self.ledger.submit({"type": "commit", "op_id": f"{txn}:commit", "claim_id": txn, "fence": fence,
                                "now": self.clock()})
            self._j(txn, "COMMITTED")
        else:
            self.ledger.submit({"type": "abort", "op_id": f"{txn}:abort", "claim_id": txn, "fence": fence})
            self._j(txn, "ABORTED", reason=out.get("reason", "downstream_refused"))
        if self.metrics:
            self.metrics.inc("gap03_placement_txn_total", outcome=self.journal.state["txns"][txn]["state"])
        return self.result(txn)

    def recover_one(self, txn: str) -> dict:
        tx = self.journal.state["txns"][txn]
        if tx["state"] in TERMINAL:
            return self.result(txn)
        fence = self.fence()
        if tx["state"] == "BEGIN":
            self._j(txn, "ABORTED", reason="orphan_begin")
            return self.result(txn)
        try:
            status = self.down.status(txn)
        except Exception:  # noqa: BLE001 - still unknown; leave for the next recovery pass
            return self.result(txn)
        if status.get("status") == "placed":
            return self._finish(txn, status, fence)
        if status.get("status") in ("absent", "refused"):
            return self._finish(txn, {"status": "refused", "reason": "not_placed_downstream"}, fence)
        return self.result(txn)

    def recover_all(self) -> list[dict]:
        """Crash recovery: deterministically finish every non-terminal transaction and expire leaked claims."""
        out = [self.recover_one(t) for t, tx in sorted(self.journal.state["txns"].items()) if tx["state"] not in TERMINAL]
        r = self.ledger.submit({"type": "reclaim_expired", "now": self.clock(), "fence": self.fence()})
        if self.metrics:
            self.metrics.set("gap03_orphaned_reservations", len(r.get("expired", [])))
        return out

    def result(self, txn: str) -> dict:
        tx = self.journal.state["txns"][txn]
        return {"txn": txn, "state": tx["state"], "node": tx["node"], "reason": tx.get("reason"), "inputs": tx["inputs"]}
