"""MC-005 - Durable fair-share ledger (GAP03-LEDGER, schema v1).

State: capacity, reservations (+entitlement generation), per-claim records
{tenant, slots, state: pending|committed|released|aborted|expired, owner,
fence, expires_at, txn}.  ``used`` = pending + committed (pending capacity is
never double-sold).  Admission reuses the reference :class:`FairShare`
verdict, evaluated *inside* the durable apply (the store boundary), so the
invariant holds regardless of caller logic.  Every op carries an idempotency
claim_id; replays return the original outcome.
"""
from __future__ import annotations

from .. import scheduler as sch
from . import canonical
from .canonical import readb
from .durable import DurableStore
from .errors import SchedulerError, classify

LIVE = ("pending", "committed")
MAX_SLOTS = 10_000_000


def used_of(state) -> dict[str, int]:
    used: dict[str, int] = {}
    for c in state["claims"].values():
        if c["state"] in LIVE:
            used[c["tenant"]] = used.get(c["tenant"], 0) + c["slots"]
    return used


def fair_share(state) -> sch.FairShare:
    return sch.FairShare(reserved=dict(state["reserved"]), used=used_of(state), capacity=state["capacity"])


class LedgerStore(DurableStore):
    KIND = "ledger"

    def initial_state(self):
        return {"revision": 0, "capacity": 0, "reserved": {}, "entitlement_generation": 0, "fence": 0, "claims": {},
                "outcomes": {}}

    def check_invariants(self, state):
        used = used_of(state)
        if any(v < 0 for v in used.values()):
            raise SchedulerError("INTEGRITY_FAILURE", "negative usage")
        if sum(used.values()) > state["capacity"]:
            raise SchedulerError("INTEGRITY_FAILURE", "used capacity above physical capacity")
        for c in state["claims"].values():
            if not (1 <= c["slots"] <= MAX_SLOTS):
                raise SchedulerError("INTEGRITY_FAILURE", "claim slots out of bounds")

    def token(self, state=None) -> str:
        return fair_share(state or self.state).state_token()

    def _fence(self, state, op):
        f = op.get("fence", 0)
        if f < state["fence"]:
            raise SchedulerError("FENCED", "stale fencing token")
        state["fence"] = f

    def apply(self, state, op):
        key = op.get("op_id")
        if key and key in state["outcomes"]:
            return state["outcomes"][key]  # idempotent replay: original outcome, no side effects
        t = op["type"]
        self._fence(state, op)
        try:
            result = self._apply(state, op, t)
        except Exception as exc:  # noqa: BLE001 - reference FairShare raises ShareViolation; classify at the boundary
            err = classify(exc)
            if not key or err.code in ("FENCED", "STALE_STATE", "DEPENDENCY_UNAVAILABLE"):
                raise err from None
            result = {"ok": False, "code": err.code, "reason": err.reason}
        state["revision"] += 1
        if key:
            state["outcomes"][key] = result
            if len(state["outcomes"]) > 200_000:
                for k in list(state["outcomes"])[:50_000]:
                    del state["outcomes"][k]
        return result

    def _apply(self, state, op, t):
        if t == "set_capacity":
            cap = op["capacity"]
            if isinstance(cap, bool) or not isinstance(cap, int) or not 0 <= cap <= MAX_SLOTS:
                raise SchedulerError("INVALID_ARGUMENT", "capacity bounds")
            if sum(used_of(state).values()) > cap:
                raise SchedulerError("CONFLICT", "capacity below used")
            state["capacity"] = cap
            return {"ok": True}
        if t == "set_reservations":
            if op["entitlement_generation"] < state["entitlement_generation"]:
                raise SchedulerError("STALE_STATE", "older entitlement generation")
            state["reserved"] = {k: int(v) for k, v in sorted(op["reserved"].items())}
            state["entitlement_generation"] = op["entitlement_generation"]
            return {"ok": True}
        if t == "prepare":
            cid = op["claim_id"]
            if cid in state["claims"]:
                raise SchedulerError("CONFLICT", "claim id reused")
            if op.get("expected_token") is not None and op["expected_token"] != fair_share(state).state_token():
                raise SchedulerError("STALE_STATE", "fair-share state changed after scoring")
            if op.get("entitlement_generation") is not None and op["entitlement_generation"] != state["entitlement_generation"]:
                raise SchedulerError("STALE_STATE", "entitlement generation changed after scoring")
            if op["tenant"] not in state["reserved"] and op.get("require_entitlement", True):
                raise SchedulerError("FAIRNESS_DENIED", "tenant has no entitlement")
            fs = fair_share(state)
            fs.claim(op["tenant"], op["slots"])  # raises ShareViolation -> classified
            state["claims"][cid] = {"tenant": op["tenant"], "slots": op["slots"], "state": "pending", "owner": op["owner"],
                                    "fence": op.get("fence", 0), "expires_at": op["expires_at"], "txn": op.get("txn")}
            return {"ok": True, "claim_id": cid, "state": "pending"}
        c = state["claims"].get(op.get("claim_id"))
        if t in ("commit", "release", "abort") and c is None:
            raise SchedulerError("INVALID_ARGUMENT", "unknown claim")
        if t == "commit":
            if c["state"] == "committed":
                return {"ok": True, "claim_id": op["claim_id"], "state": "committed"}
            if c["state"] != "pending":
                raise SchedulerError("CONFLICT", f"cannot commit a {c['state']} claim")
            if op.get("now", 0) >= c["expires_at"]:
                raise SchedulerError("STALE_STATE", "pending claim expired")
            c["state"] = "committed"
            return {"ok": True, "claim_id": op["claim_id"], "state": "committed"}
        if t in ("release", "abort"):
            target = "released" if t == "release" else "aborted"
            if c["state"] == target:
                return {"ok": True, "claim_id": op["claim_id"], "state": target}
            if c["state"] not in LIVE:
                raise SchedulerError("CONFLICT", f"cannot {t} a {c['state']} claim")
            if t == "abort" and c["state"] != "pending":
                raise SchedulerError("CONFLICT", "only pending claims can be aborted")
            c["state"] = target
            return {"ok": True, "claim_id": op["claim_id"], "state": target}
        if t == "reclaim_expired":
            freed = []
            for cid, cl in sorted(state["claims"].items()):
                if cl["state"] == "pending" and cl["expires_at"] <= op["now"] and op.get("fence", 0) >= cl["fence"]:
                    cl["state"] = "expired"
                    freed.append(cid)
            return {"ok": True, "expired": freed}
        if t == "reconcile":
            placed = op["placed"]  # {claim_id: tenant} actually running downstream
            report = {"orphan_committed": [], "unknown_placements": []}
            for cid, cl in sorted(state["claims"].items()):
                if cl["state"] == "committed" and cid not in placed:
                    report["orphan_committed"].append(cid)
                    if op.get("repair"):
                        cl["state"] = "released"
            report["unknown_placements"] = sorted(set(placed) - set(state["claims"]))
            report["ok"] = True
            return report
        raise SchedulerError("INVALID_ARGUMENT", "unknown ledger op")

    # ---- reads -------------------------------------------------------------------------
    def verdict(self, tenant: str, slots: int = 1):
        with self._lock:
            return fair_share(self.state).verdict(tenant, slots), self.state["revision"], self.state["entitlement_generation"]

    def point_in_time(self, seq: int) -> dict:
        """Rebuild state as of WAL sequence ``seq`` from archived+live history (read-only)."""
        import os
        state = self.initial_state()
        segs = sorted(os.listdir(os.path.join(self.dir, "archive")), key=lambda n: int(n.split("-")[-1].split(".")[0]))
        paths = [os.path.join(self.dir, "archive", s) for s in segs] + [self.wal_path]
        for path in paths:
            if not os.path.exists(path):
                continue
            for line in readb(path).split(b"\n"):
                if not line:
                    continue
                rec = canonical.loads(line, max_bytes=1 << 24)
                if rec["seq"] > seq:
                    return state
                self.apply(state, rec["op"])
        return state
