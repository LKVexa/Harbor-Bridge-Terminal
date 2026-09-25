"""Component 61 - backup / restore / migration / reconstruction (PK_DYN_BACKUP/2).

Backup directory layout::

  <dir>/state.json      canonical JSON: {"format": 2, "pool": <Pool.snapshot()>, "meta": {...}}
  <dir>/manifest.json   {"schema": "PK_DYN_BACKUP/2", "files": {"state.json": sha256},
                         "created": ts, "signature": HMAC over the manifest body}

* integrity: sha256 per file + HMAC-SHA256 signature (``core.TrustRoot``,
  nonproduction key).  Encryption at rest is BLOCKED: the stdlib has no vetted
  cipher and no KMS is provisioned; this module never pretends to encrypt.
* restore: verifies manifest, signature and digests, copies into an isolated
  temp directory, rebuilds a ``Pool`` (its constructor re-validates all
  invariants) and runs a dry tick on a copy.
* migration: v1 ``{"min": .., "max": .., "nodes": {id: expires}}`` -> v2.
* reconstruction: from lease records (source of truth) and a provider inventory
  double; nodes present in the provider but unleased are LEAKED (cost risk),
  leases without a provider node are LOST, both reported for operator action.
"""
from __future__ import annotations

import copy
import json
import shutil
import tempfile
from pathlib import Path

from ..model import Pool
from .core import Inv08Error, Outcome, TrustRoot, canonical, sha256_hex

SCHEMA = "PK_DYN_BACKUP/2"
FORMAT = 2


def _err(name, msg, **d):
    return Inv08Error(code=f"INV08.BACKUP.{name}", message=msg, outcome=Outcome.TERMINAL_FAILURE, details=d)


def migrate(state: dict) -> dict:
    fmt = state.get("format", 1)
    if fmt == FORMAT:
        return state
    if fmt != 1:
        raise _err("UNSUPPORTED_FORMAT", f"cannot migrate format {fmt}")
    nodes = {nid: {"expires": exp, "busy": False} for nid, exp in state.get("nodes", {}).items()}
    return {"format": 2, "pool": {"min_nodes": state["min"], "max_nodes": state["max"],
                                  "per_node": state.get("per_node", 4), "lease_ttl": state.get("ttl", 10),
                                  "nodes": nodes, "node_hours": float(state.get("node_hours", 0.0)),
                                  "last_now": None},
            "meta": {"migrated_from": 1}}


def write_backup(pool: Pool, dest: str | Path, trust: TrustRoot, kid: str, *, created: float, meta: dict | None = None) -> dict:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=False)
    state = {"format": FORMAT, "pool": pool.snapshot(), "meta": meta or {}}
    data = canonical(state)
    (dest / "state.json").write_bytes(data)
    body = {"schema": SCHEMA, "files": {"state.json": sha256_hex(data)}, "created": created}
    man = dict(body, signature=trust.sign(kid, body))
    (dest / "manifest.json").write_bytes(canonical(man))
    return man


def verify_backup(src: str | Path, trust: TrustRoot) -> list[str]:
    src = Path(src)
    try:
        man = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"manifest unreadable: {exc}"]
    p = []
    body = {k: v for k, v in man.items() if k != "signature"}
    if man.get("schema") != SCHEMA:
        p.append("schema mismatch")
    if not trust.verify(body, man.get("signature") or {}):
        p.append("manifest signature invalid")
    for name, dig in man.get("files", {}).items():
        f = src / name
        if "/" in name or ".." in name or not f.is_file():
            p.append(f"missing or unsafe {name}")
        elif sha256_hex(f.read_bytes()) != dig:
            p.append(f"digest mismatch {name}")
    return p


def pool_from_state(state: dict) -> Pool:
    s = migrate(state)["pool"]
    pool = Pool(min_nodes=s["min_nodes"], max_nodes=s["max_nodes"], per_node=s["per_node"],
                lease_ttl=s["lease_ttl"], nodes=copy.deepcopy(s["nodes"]), node_hours=s["node_hours"])
    if s.get("last_now") is not None:
        pool._last_now = s["last_now"]   # restore time watermark (model has no public API; see defects)
    return pool


def restore(src: str | Path, trust: TrustRoot, *, workdir: str | Path | None = None) -> tuple[Pool, Path]:
    problems = verify_backup(src, trust)
    if problems:
        raise _err("INTEGRITY", "; ".join(problems))
    iso = Path(tempfile.mkdtemp(prefix="inv08-restore-", dir=workdir))
    for name in ("state.json", "manifest.json"):
        shutil.copyfile(Path(src) / name, iso / name)
    state = json.loads((iso / "state.json").read_text(encoding="utf-8"))
    try:
        pool = pool_from_state(state)
        probe = copy.deepcopy(pool)
        last = state["pool"].get("last_now")
        probe.tick(last if last is not None else 0, 0, elapsed_hours=0)
    except (ValueError, KeyError, TypeError) as exc:
        raise _err("VALIDATION", f"restored state invalid: {exc}")
    return pool, iso


def reconstruct(leases: dict[str, dict], provider_inventory: list[str], *, min_nodes: int, max_nodes: int,
                per_node: int = 4, lease_ttl: int = 10) -> dict:
    """Leases are the source of truth; provider inventory is cross-checked."""
    inv = set(provider_inventory)
    live = {n: {"expires": l["expires"], "busy": bool(l.get("busy", False))}
            for n, l in sorted(leases.items()) if n in inv}
    lost = sorted(n for n in leases if n not in inv)
    leaked = sorted(inv - set(leases))
    report = {"lost_leases": lost, "leaked_nodes": leaked, "restored": sorted(live),
              "outcome": (Outcome.SUCCESS if not lost and not leaked else Outcome.OPERATOR_REQUIRED).value}
    if len(live) > max_nodes:
        report["outcome"] = Outcome.OPERATOR_REQUIRED.value
        report["error"] = "more live leased nodes than max_nodes"
        return report
    report["pool"] = Pool(min_nodes=min_nodes, max_nodes=max_nodes, per_node=per_node, lease_ttl=lease_ttl, nodes=live)
    return report
