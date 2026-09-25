"""MC17 - Anti-entropy / reconciliation engine.

Digest tree per (tenant, environment): keys are bucketed by ``sha256(key)[0:1]`` into
256 leaves; each leaf digest is sha256 over the sorted ``(key, frontier op_ids,
tombstone floor)`` tuples; the root is sha256 over leaf digests.  Two replicas compare
roots, then only differing leaves, then exchange the *signed* frontier documents of the
keys in those leaves.  Each document is re-submitted through the receiver's normal
accept path as a relayed write (authz REPLICATE + provenance verification + fencing),
so repair can never introduce an unauthenticated write.  Floors (collected tombstones)
are exchanged too so resurrection cannot occur through repair.

Convergence proof obligation (tested): after ``sync`` in both directions, the two
replicas' root digests are equal and every key's frontier op-id set is equal.
"""
from __future__ import annotations

import hashlib

from .errors import Gap05Error
from .node import ReplicaNode, split_key
from .schemas import canonical_bytes


def _leaf(key: str) -> int:
    return hashlib.sha256(key.encode()).digest()[0]


def digest_tree(node: ReplicaNode, tenant: str, environment: str) -> dict:
    leaves: dict[int, list] = {}
    for sk in set(node.state_keys()) | set(node.floors):
        t, e, k = split_key(sk)
        if (t, e) != (tenant, environment):
            continue
        ops = sorted(d["op_id"] for d in node._frontier_docs(sk))
        floor = sorted(node.floors.get(sk, {}).items())
        leaves.setdefault(_leaf(k), []).append((k, ops, floor))
    leaf_digests = {i: hashlib.sha256(canonical_bytes(sorted(v))).hexdigest() for i, v in leaves.items()}
    root = hashlib.sha256(canonical_bytes(sorted(leaf_digests.items()))).hexdigest()
    return {"root": root, "leaves": leaf_digests}


def docs_for_leaves(node: ReplicaNode, tenant: str, environment: str, leaves: set[int]) -> tuple[list, dict]:
    docs, floors = [], {}
    for sk in set(node.state_keys()) | set(node.floors):
        t, e, k = split_key(sk)
        if (t, e) == (tenant, environment) and _leaf(k) in leaves:
            docs.extend(node._frontier_docs(sk))
            if sk in node.floors:
                floors[sk] = dict(node.floors[sk])
    return docs, floors


def sync_one_way(src: ReplicaNode, dst: ReplicaNode, tenant: str, environment: str, *, principal: str) -> dict:
    """Push what ``src`` has and ``dst`` lacks.  ``principal`` is src's authenticated identity."""
    a, b = digest_tree(src, tenant, environment), digest_tree(dst, tenant, environment)
    if a["root"] == b["root"]:
        return {"differing_leaves": 0, "sent": 0, "applied": 0, "rejected": []}
    diff = {i for i in set(a["leaves"]) | set(b["leaves"]) if a["leaves"].get(i) != b["leaves"].get(i)}
    docs, floors = docs_for_leaves(src, tenant, environment, diff)
    for sk, floor in floors.items():  # floors first: prevents resurrection during repair
        if dst.floors.get(sk) != floor:
            dst.wal.append("gc", {"sk": sk, "floor": floor})
            dst._gc_key(sk, floor)
    applied, rejected = 0, []
    # causal order is not required (the model is order-independent) but sorting makes the run reproducible
    for doc in sorted(docs, key=lambda d: (d["key"], d["vector"], d["op_id"])):
        try:
            r = dst.submit(doc, principal=principal, relay=True, recovery=True)
            applied += r["outcome"] != "duplicate"
        except Gap05Error as exc:
            rejected.append({"op_id": doc["op_id"], "code": exc.code})
    return {"differing_leaves": len(diff), "sent": len(docs), "applied": applied, "rejected": rejected}


def reconcile(a: ReplicaNode, b: ReplicaNode, tenant: str, environment: str, *, principal_a: str,
              principal_b: str, max_rounds: int = 4) -> dict:
    rounds = []
    for _ in range(max_rounds):
        r1 = sync_one_way(a, b, tenant, environment, principal=principal_a)
        r2 = sync_one_way(b, a, tenant, environment, principal=principal_b)
        rounds.append([r1, r2])
        if digest_tree(a, tenant, environment)["root"] == digest_tree(b, tenant, environment)["root"]:
            for n in (a, b):
                if n.recovery_mode:
                    n.finish_recovery()
            return {"converged": True, "rounds": rounds}
    return {"converged": False, "rounds": rounds}
