"""MC-004 - Durable topology state store (GAP03-TOPO-STORE, schema v2).

Engine: single-writer hash-chained WAL + snapshots (:mod:`.durable`) on local
durable storage; consistency is linearizable for the lease holder (MC-006
fencing tokens are checked on every write).  Replication is NOT provided by
this engine - a replicated deployment must place the directory on a
quorum-replicated volume or swap the engine (see ADR-0001, blocked item).
"""
from __future__ import annotations

import re
from types import MappingProxyType

from .. import scheduler as sch
from . import canonical
from .durable import DurableStore
from .errors import SchedulerError

TYPES = ("region", "site", "rack", "node")
PARENT_TYPE = {"region": None, "site": "region", "rack": "site", "node": "rack"}
LIFECYCLE = ("active", "quarantined", "decommissioned")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:\-]{0,62}$")
MAX_LABELS, MAX_LABEL_LEN, MAX_BATCH = 32, 128, 1000


def _migrate_v1(state):
    for rec in state["nodes"].values():
        rec.setdefault("lifecycle", "active")
    return state


class TopologyStore(DurableStore):
    KIND = "topology"
    SCHEMA_VERSION = 2
    MIGRATIONS = {1: _migrate_v1}

    def initial_state(self):
        return {"generation": 0, "fence": 0, "nodes": {}}

    # ---- constraints -------------------------------------------------------------------
    def check_invariants(self, state):
        nodes = state["nodes"]
        for nid, rec in nodes.items():
            if not ID_RE.match(nid):
                raise SchedulerError("INTEGRITY_FAILURE", f"invalid id {nid!r}")
            if rec["type"] not in TYPES:
                raise SchedulerError("INTEGRITY_FAILURE", "invalid type")
            if rec.get("lifecycle", "active") not in LIFECYCLE:
                raise SchedulerError("INTEGRITY_FAILURE", "invalid lifecycle")
            want = PARENT_TYPE[rec["type"]]
            if want is None:
                if rec["parent"] is not None:
                    raise SchedulerError("INTEGRITY_FAILURE", "region must be a root")
            else:
                parent = nodes.get(rec["parent"])
                if parent is None:
                    raise SchedulerError("INTEGRITY_FAILURE", f"orphan {nid}")
                if parent["type"] != want:
                    raise SchedulerError("INTEGRITY_FAILURE", f"{nid}: parent type {parent['type']} != {want}")
            if len(rec["labels"]) > MAX_LABELS or any(len(k) > 63 or len(str(v)) > MAX_LABEL_LEN for k, v in rec["labels"].items()):
                raise SchedulerError("INTEGRITY_FAILURE", "label bounds")
        if state["generation"] < 0:
            raise SchedulerError("INTEGRITY_FAILURE", "negative generation")

    # ---- apply ------------------------------------------------------------------------------
    def apply(self, state, op):
        if op["type"] == "fence":
            if op["token"] < state["fence"]:
                raise SchedulerError("FENCED", "stale fencing token")
            state["fence"] = op["token"]
            return state["fence"]
        if op["type"] != "batch":
            raise SchedulerError("INVALID_ARGUMENT", "unknown op")
        if op.get("fence", 0) < state["fence"]:
            raise SchedulerError("FENCED", "stale fencing token")
        state["fence"] = max(state["fence"], op.get("fence", 0))
        if op["expected_generation"] != state["generation"]:
            raise SchedulerError("STALE_STATE", f"generation {state['generation']} != expected {op['expected_generation']}")
        muts = op["mutations"]
        if not muts or len(muts) > MAX_BATCH:
            raise SchedulerError("PAYLOAD_TOO_LARGE" if muts else "INVALID_ARGUMENT", "batch size")
        nodes = state["nodes"]
        for m in muts:
            kind, nid = m["op"], m["id"]
            if not isinstance(nid, str) or not ID_RE.match(nid):
                raise SchedulerError("INVALID_ARGUMENT", "invalid node id")
            if kind == "create":
                if nid in nodes:
                    raise SchedulerError("CONFLICT", f"{nid} exists")
                if m["node_type"] not in TYPES:
                    raise SchedulerError("INVALID_ARGUMENT", "invalid node type")
                nodes[nid] = {"type": m["node_type"], "parent": m.get("parent"), "labels": dict(m.get("labels", {})),
                              "lifecycle": "active", "rev": 1}
            elif kind in ("relabel", "reparent", "set_lifecycle", "delete"):
                rec = nodes.get(nid)
                if rec is None:
                    raise SchedulerError("NOT_IN_TOPOLOGY", nid)
                if kind == "relabel":
                    rec["labels"] = dict(m["labels"])
                elif kind == "reparent":
                    if not m.get("replace"):
                        raise SchedulerError("CONFLICT", "re-parent requires explicit replace intent")
                    rec["parent"] = m["parent"]
                elif kind == "set_lifecycle":
                    if m["lifecycle"] not in LIFECYCLE:
                        raise SchedulerError("INVALID_ARGUMENT", "invalid lifecycle")
                    rec["lifecycle"] = m["lifecycle"]
                else:
                    if any(r["parent"] == nid for r in nodes.values()):
                        raise SchedulerError("CONFLICT", f"{nid} has children")
                    del nodes[nid]
                    continue
                rec["rev"] += 1
            else:
                raise SchedulerError("INVALID_ARGUMENT", f"unknown mutation {kind}")
        # full validation before commit (cycle/orphan/type) - DurableStore also re-checks
        self.check_invariants(state)
        state["generation"] += 1
        return state["generation"]

    # ---- reads -----------------------------------------------------------------------------
    @property
    def generation(self) -> int:
        return self.state["generation"]

    def path_of(self, state, nid):
        chain, cur = [], nid
        while cur is not None:
            rec = state["nodes"][cur]
            chain.append((rec["type"], cur))
            cur = rec["parent"]
        return {t: i for t, i in chain}

    def scheduler_snapshot(self) -> sch.TopologySnapshot:
        """Immutable snapshot of active leaf nodes, verified before use."""
        with self._lock:
            state = self.state
            self.check_invariants(state)
            out = {}
            for nid, rec in state["nodes"].items():
                if rec["type"] != "node" or rec["lifecycle"] != "active":
                    continue
                p = self.path_of(state, nid)
                if any(state["nodes"][p[t]]["lifecycle"] != "active" for t in ("region", "site", "rack")):
                    continue
                out[nid] = (p["region"], p["site"], p["rack"])
            return sch.TopologySnapshot(MappingProxyType(out), state["generation"])

    def import_bundle(self, bundle: dict, *, fence: int = 0) -> int:
        """Bootstrap/reconstruct from an exported bundle after verifying its integrity hash."""
        if bundle.get("kind") != self.KIND or bundle.get("digest") != canonical.digest(bundle.get("state")):
            raise SchedulerError("INTEGRITY_FAILURE", "bundle digest mismatch")
        nodes = bundle["state"]["nodes"]
        order = sorted(nodes, key=lambda n: (TYPES.index(nodes[n]["type"]), n))
        muts = [{"op": "create", "id": n, "node_type": nodes[n]["type"], "parent": nodes[n]["parent"],
                 "labels": nodes[n]["labels"]} for n in order]
        gen = self.generation
        for i in range(0, len(muts), MAX_BATCH):
            gen = self.submit({"type": "batch", "expected_generation": gen, "mutations": muts[i:i + MAX_BATCH], "fence": fence})
        lif = [{"op": "set_lifecycle", "id": n, "lifecycle": nodes[n].get("lifecycle", "active")}
               for n in order if nodes[n].get("lifecycle", "active") != "active"]
        if lif:
            gen = self.submit({"type": "batch", "expected_generation": gen, "mutations": lif, "fence": fence})
        return gen
