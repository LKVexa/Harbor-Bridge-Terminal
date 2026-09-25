"""Component 53 - decision journal and explain API for ``Pool.tick`` (``PK_DYN_DECISION/1``).

Journal record (one canonical-JSON line, hash-chained like the audit log)::

  {"schema": "PK_DYN_DECISION/1", "id": "d-<seq>", "seq": int, "ts": number,
   "inputs": {"now", "demand", "elapsed_hours"},
   "policy": {"min_nodes", "max_nodes", "per_node", "lease_ttl"},
   "pre_state": {"nodes", "n", "node_hours", "last_now"},
   "result": <TickResult> | null, "error": {"type", "message"} | null,
   "graph": {"nodes": [{"id", "kind", "value"}], "edges": [[from, to, label]]},
   "prev": 64hex, "hash": 64hex}

``replay`` re-executes a record against a Pool rebuilt from ``pre_state`` and
``diff``s against the recorded result: a non-empty diff means the model's behaviour
changed (or the record was altered).  Access and retention: ``ACCESS_POLICY`` and
``may_purge``; durations are PROPOSED pending an UNASSIGNED data owner.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Callable

from ..model import Pool
from .core import Inv08Error, canonical, redact, sha256_hex

SCHEMA = "PK_DYN_DECISION/1"
GENESIS = "0" * 64

ACCESS_POLICY = {
    "operator": {"fields": "all"},
    "tenant": {"fields": ["id", "ts", "inputs.demand", "result.size", "result.target"]},
    "auditor": {"fields": "all", "read_only": True},
}
RETENTION = {"retain_days": 90, "status": "PROPOSED", "owner": "UNASSIGNED",
             "legal_hold": "suspends purge"}


def _num(v):
    if isinstance(v, int) and not isinstance(v, bool) and abs(v) > 2 ** 53:
        return {"bigint": str(v)}  # JSON-safe exact encoding for huge ints
    return v


def build_graph(inputs: dict, policy: dict, pre_nodes: dict, result: dict) -> dict:
    n: list[dict] = []
    e: list[list] = []
    for k, v in inputs.items():
        n.append({"id": f"input:{k}", "kind": "input", "value": _num(v)})
    for k, v in policy.items():
        n.append({"id": f"policy:{k}", "kind": "policy", "value": v})
    d, per, mx = inputs["demand"], policy["per_node"], policy["max_nodes"]
    capped = d >= mx * per
    dn = mx if capped else (math.ceil(d / per) if d else 0)
    n.append({"id": "constraint:demand_nodes", "kind": "constraint", "value": dn,
              "rule": "max_nodes (demand >= capacity)" if capped else "ceil(demand/per_node)"})
    e += [["input:demand", "constraint:demand_nodes", "divided"], ["policy:per_node", "constraint:demand_nodes", "divisor"]]
    n.append({"id": "decision:target", "kind": "decision", "value": result["target"],
              "rule": "clamp(demand_nodes, min_nodes, max_nodes)"})
    e += [["constraint:demand_nodes", "decision:target", "clamped"], ["policy:min_nodes", "decision:target", "lower bound"],
          ["policy:max_nodes", "decision:target", "upper bound"]]
    for nid in result["renewed"]:
        n.append({"id": f"action:renew:{nid}", "kind": "action", "value": nid})
        e.append(["input:now", f"action:renew:{nid}", "busy -> expires=now+lease_ttl"])
    for nid in result["reclaimed"]:
        st = pre_nodes.get(nid, {})
        why = "lease expired while idle" if st.get("expires", math.inf) <= inputs["now"] else "idle surplus over target"
        n.append({"id": f"action:reclaim:{nid}", "kind": "action", "value": nid, "reason": why})
        e.append(["decision:target" if "surplus" in why else "input:now", f"action:reclaim:{nid}", why])
    if result["added"]:
        n.append({"id": "action:add", "kind": "action", "value": result["added"], "reason": "size below target"})
        e.append(["decision:target", "action:add", "size below target"])
    return {"nodes": n, "edges": e}


class DecisionJournal:
    def __init__(self, path: str | os.PathLike, clock: Callable[[], float]) -> None:
        self.path, self.clock = Path(path), clock
        self.seq, self.prev = 0, GENESIS
        if self.path.exists():
            recs = self.records()
            ok, problems = verify_records(recs)
            if not ok:
                raise Inv08Error("INV08.EXPLAIN.JOURNAL_TAMPERED", "; ".join(problems[:3]))
            if recs:
                self.seq, self.prev = recs[-1]["seq"], recs[-1]["hash"]

    def _write(self, rec: dict) -> dict:
        rec["prev"] = self.prev
        rec["hash"] = sha256_hex(canonical(rec))
        with open(self.path, "ab") as fh:
            fh.write(canonical(rec) + b"\n")
        self.seq, self.prev = rec["seq"], rec["hash"]
        return rec

    def record_tick(self, pool: Pool, now, demand, *, elapsed_hours=1.0):
        pre = {"nodes": {k: dict(v) for k, v in pool.nodes.items()}, "n": pool._n,
               "node_hours": pool.node_hours, "last_now": pool._last_now}
        policy = {k: getattr(pool, k) for k in ("min_nodes", "max_nodes", "per_node", "lease_ttl")}
        inputs = {"now": now, "demand": demand, "elapsed_hours": elapsed_hours}
        seq = self.seq + 1
        rec = {"schema": SCHEMA, "id": f"d-{seq}", "seq": seq, "ts": self.clock(), "policy": policy,
               "pre_state": pre, "result": None, "error": None, "graph": None}
        try:
            result = pool.tick(now, demand, elapsed_hours=elapsed_hours)
        except (ValueError, OverflowError, TypeError) as exc:
            rec["inputs"] = redact({k: repr(v) for k, v in inputs.items()})
            rec["error"] = {"type": type(exc).__name__, "message": str(exc)[:500]}
            self._write(rec)
            raise
        rec["inputs"] = {k: _num(v) for k, v in inputs.items()}
        rec["result"] = {k: _num(v) for k, v in result.items()}
        rec["graph"] = build_graph(inputs, policy, pre["nodes"], result)
        self._write(rec)
        return result

    def records(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_bytes().splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except ValueError:
                    out.append({"__corrupt__": True})
        return out

    def explain(self, decision_id: str, *, role: str = "operator") -> dict:
        if role not in ACCESS_POLICY:
            raise Inv08Error("INV08.EXPLAIN.ACCESS_DENIED", f"role {role!r} has no access")
        for r in self.records():
            if r.get("id") == decision_id:
                return view(r, role)
        raise Inv08Error("INV08.EXPLAIN.NOT_FOUND", decision_id)

    def query(self, *, role: str = "operator", since_ts: float | None = None, kind: str | None = None) -> list[dict]:
        out = []
        for r in self.records():
            if since_ts is not None and r.get("ts", -math.inf) < since_ts:
                continue
            if kind == "error" and not r.get("error"):
                continue
            if kind == "scaled" and not (r.get("result") and (r["result"]["added"] or r["result"]["reclaimed"])):
                continue
            out.append(view(r, role))
        return out


def view(rec: dict, role: str) -> dict:
    pol = ACCESS_POLICY.get(role)
    if pol is None:
        raise Inv08Error("INV08.EXPLAIN.ACCESS_DENIED", f"role {role!r}")
    if pol["fields"] == "all":
        out = dict(rec)
        if rec.get("graph"):
            out["narrative"] = [f"{a} -> {b}: {lab}" for a, b, lab in rec["graph"]["edges"]]
        return out
    out: dict = {}
    for f in pol["fields"]:
        parts = f.split(".")
        src, dst = rec, out
        for p in parts[:-1]:
            src = (src or {}).get(p) or {}
            dst = dst.setdefault(p, {})
        dst[parts[-1]] = (src or {}).get(parts[-1])
    return out


def verify_records(recs: list[dict]) -> tuple[bool, list[str]]:
    problems, prev, seq = [], GENESIS, 0
    for r in recs:
        if "__corrupt__" in r or "hash" not in r:
            problems.append(f"after seq {seq}: corrupt record")
            break
        body = {k: v for k, v in r.items() if k != "hash"}
        if r.get("seq") != seq + 1 or r.get("prev") != prev or sha256_hex(canonical(body)) != r["hash"]:
            problems.append(f"seq {r.get('seq')}: chain/hash failure")
        prev, seq = r["hash"], r.get("seq", seq + 1)
    return not problems, problems


def _unnum(v):
    return int(v["bigint"]) if isinstance(v, dict) and "bigint" in v else v


def replay(rec: dict) -> dict:
    if rec.get("schema") != SCHEMA or rec.get("result") is None:
        raise Inv08Error("INV08.EXPLAIN.NOT_REPLAYABLE", "record has no successful result")
    pre = rec["pre_state"]
    pool = Pool(**rec["policy"], nodes={k: dict(v) for k, v in pre["nodes"].items()}, _n=pre["n"],
                node_hours=pre["node_hours"])
    pool._last_now = pre["last_now"]
    inp = {k: _unnum(v) for k, v in rec["inputs"].items()}
    got = pool.tick(inp["now"], inp["demand"], elapsed_hours=inp["elapsed_hours"])
    return diff({k: _unnum(v) for k, v in rec["result"].items()}, dict(got))


def diff(a: dict, b: dict) -> dict:
    return {k: {"recorded": a.get(k), "replayed": b.get(k)} for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)}


def may_purge(age_days: float, legal_hold: bool) -> bool:
    return not legal_hold and age_days > RETENTION["retain_days"]
