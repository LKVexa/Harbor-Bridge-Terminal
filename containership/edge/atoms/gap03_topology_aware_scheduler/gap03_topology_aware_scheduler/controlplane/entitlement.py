"""MC-003 - Tenant entitlement / reservation authority (GAP03-ENT/1).

The authority is the only writer of reservations.  Records are normalised to
canonical ``slots`` before comparison, updated by per-tenant compare-and-swap
on ``revision``, bound into signed, generation-numbered snapshots, and
reconciled against the fair-share ledger.  Tenants can read their own record
and aggregate metadata only.
"""
from __future__ import annotations

from . import canonical
from .durable import DurableStore
from .errors import SchedulerError

DIMENSIONS = {"slots": {"slot": 1, "kslot": 1000}}
MAX_QTY = 10_000_000


def normalize(quantity: int, unit: str, dimension: str = "slots") -> int:
    units = DIMENSIONS.get(dimension)
    if units is None:
        raise SchedulerError("INVALID_ARGUMENT", "unknown resource dimension")
    if unit not in units:
        raise SchedulerError("INVALID_ARGUMENT", f"unit {unit!r} not valid for {dimension}")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
        raise SchedulerError("INVALID_ARGUMENT", "quantity must be a non-negative integer")
    value = quantity * units[unit]
    if value > MAX_QTY:
        raise SchedulerError("INVALID_ARGUMENT", "quantity overflow")
    return value


class EntitlementAuthority(DurableStore):
    KIND = "entitlement"

    def initial_state(self):
        return {"generation": 0, "capacity": 0, "oversubscription": {"ratio_ppm": 1_000_000, "approval": None},
                "records": {}}

    def check_invariants(self, state):
        total = sum(r["reserved"] for r in state["records"].values() if not r["revoked"])
        limit = state["capacity"] * state["oversubscription"]["ratio_ppm"] // 1_000_000
        if total > limit:
            raise SchedulerError("FAIRNESS_DENIED", f"aggregate reservations {total} exceed policy limit {limit}")

    def apply(self, state, op):
        t = op["type"]
        if t == "set_capacity":
            state["capacity"] = normalize(op["quantity"], op["unit"])
        elif t == "approve_oversubscription":
            if not op.get("approval_ref"):
                raise SchedulerError("PERMISSION_DENIED", "oversubscription requires an approval reference")
            if not (1_000_000 <= op["ratio_ppm"] <= 2_000_000):
                raise SchedulerError("INVALID_ARGUMENT", "ratio outside policy bounds")
            state["oversubscription"] = {"ratio_ppm": op["ratio_ppm"], "approval": op["approval_ref"]}
        elif t == "upsert":
            r = op["record"]
            cur = state["records"].get(r["tenant"])
            cur_rev = cur["revision"] if cur else 0
            if op["expected_revision"] != cur_rev:
                raise SchedulerError("STALE_STATE", f"entitlement revision {cur_rev} != expected {op['expected_revision']}")
            if r["dimension"] != "slots":
                raise SchedulerError("INVALID_ARGUMENT", "cross-dimension entitlement")
            reserved = normalize(r["quantity"], r["unit"], r["dimension"])
            hard = normalize(r.get("hard_limit", r["quantity"]), r["unit"], r["dimension"])
            if hard < reserved:
                raise SchedulerError("INVALID_ARGUMENT", "hard limit below reservation")
            if r["expires_at"] <= r["valid_from"]:
                raise SchedulerError("INVALID_ARGUMENT", "empty validity window")
            state["records"][r["tenant"]] = {"tenant": r["tenant"], "dimension": "slots", "unit": "slot",
                                             "reserved": reserved, "hard_limit": hard, "valid_from": r["valid_from"],
                                             "expires_at": r["expires_at"], "revision": cur_rev + 1, "revoked": False,
                                             "issuer": op["actor"]}
        elif t == "revoke":
            rec = state["records"].get(op["tenant"])
            if rec is None:
                raise SchedulerError("INVALID_ARGUMENT", "unknown tenant")
            rec["revoked"], rec["revision"] = True, rec["revision"] + 1
        else:
            raise SchedulerError("INVALID_ARGUMENT", "unknown op")
        state["generation"] += 1
        return state["generation"]

    # ---- API -----------------------------------------------------------------------
    def write(self, principal: dict, op: dict, *, audit=None) -> int:
        if "entitlement.write" not in principal.get("perms", set()):
            if audit:
                audit.append(actor=principal.get("sub", "?"), action="entitlement.write", target=op.get("type", "?"),
                             result="denied")
            raise SchedulerError("PERMISSION_DENIED", "entitlement.write required")
        op = dict(op, actor=principal["sub"])
        before = self.state["records"].get(op.get("tenant") or op.get("record", {}).get("tenant"))
        gen = self.submit(op)
        if audit:
            audit.append(actor=principal["sub"], action=f"entitlement.{op['type']}", target=str(op.get("tenant") or
                         op.get("record", {}).get("tenant", "estate")), result="ok", generation=gen, before=before,
                         after=self.state["records"].get(op.get("tenant") or op.get("record", {}).get("tenant")))
        return gen

    def effective(self, now: float) -> dict[str, int]:
        """Reservations that currently authorize claims (revoked/expired/not-yet-valid excluded)."""
        return {t: r["reserved"] for t, r in sorted(self.state["records"].items())
                if not r["revoked"] and r["valid_from"] <= now < r["expires_at"]}

    def snapshot(self, now: float, signer=None) -> dict:
        body = {"schema": "GAP03-ENT/1", "generation": self.state["generation"], "capacity": self.state["capacity"],
                "effective": self.effective(now), "as_of": int(now)}
        env = None
        if signer is not None:
            from .identity import sign_artifact
            env = sign_artifact(signer, "entitlement_snapshot", body, clock=lambda: now)
        return {"body": body, "envelope": env}

    def tenant_view(self, principal: dict, tenant: str) -> dict:
        if principal.get("tenant") != tenant and "entitlement.write" not in principal.get("perms", set()):
            raise SchedulerError("PERMISSION_DENIED", "tenants may only read their own entitlement")
        rec = self.state["records"].get(tenant)
        return {"record": dict(rec) if rec else None,
                "aggregate": {"tenants": len(self.state["records"]), "capacity": self.state["capacity"]}}

    def reconcile(self, ledger_reserved: dict[str, int], now: float) -> list[dict]:
        """Compare authority vs ledger; return explicit drift events (never silently repairs)."""
        want = self.effective(now)
        drift = []
        for t in sorted(set(want) | set(ledger_reserved)):
            a, b = want.get(t, 0), ledger_reserved.get(t, 0)
            if a != b:
                drift.append({"event": "entitlement_drift", "tenant": t, "authority": a, "ledger": b,
                              "repair": {"op": "set_reservation", "tenant": t, "slots": a}})
        return drift


def snapshot_digest(snap: dict) -> str:
    return canonical.digest(snap["body"])
