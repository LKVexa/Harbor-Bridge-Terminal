"""Automated day-0 / day-1 / day-2 actions with evidence capture (MC-063, MC-066).

  python3 tools/runbook.py day0  --root DIR --config cfg.json --author A
  python3 tools/runbook.py canary --metrics before.json after.json
  python3 tools/runbook.py day2  --root DIR          (reconcile pass report, local emulator only)

Every action writes an evidence record under DIR/evidence/.  There is no
deployment system here: canary *evaluation* is automated, canary *rollout* is
the operator's deploy tool (BLOCKED: B-DEPLOY).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

from _common import source_digest

from inv34_legacy_cpu_expansion_path.production.config import ConfigRepository
from inv34_legacy_cpu_expansion_path.production.store import FileStateStore

ABORT_RULES = {  # canary abort thresholds (PROPOSED)
    "inv34_http_errors_rate": 0.05, "duplicate_hotadd": 0, "observation_regression": 0, "stalled_vms": 0,
}


def evidence(root: pathlib.Path, kind: str, body: dict) -> pathlib.Path:
    d = root / "evidence"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{int(time.time() * 1000)}-{kind}.json"
    p.write_text(json.dumps({"kind": kind, "at": time.time(), "source_digest": source_digest(), **body}, indent=1))
    return p


def day0(root: pathlib.Path, cfg_path: str, author: str) -> dict:
    cfg = json.loads(pathlib.Path(cfg_path).read_text())
    if cfg.get("expansion_enabled"):
        raise SystemExit("day0 refuses a config with expansion_enabled=true; enable after checks (OPERATIONS.md)")
    repo = ConfigRepository(root / "config")
    d = repo.stage(cfg)
    rec = repo.activate(d, author=author, approver=cfg.get("_approver"), reason="day0 bootstrap")
    FileStateStore(root / "state")
    return {"config_digest": d, "provenance": rec, "state_root": str(root / "state"),
            "evidence": str(evidence(root, "day0", {"config_digest": d}))}


def canary(before: dict, after: dict) -> dict:
    violations = []
    for k, lim in ABORT_RULES.items():
        if after.get(k, 0) > lim:
            violations.append(f"{k}={after.get(k)} > {lim}")
        if k.endswith("_rate") and after.get(k, 0) > 2 * max(before.get(k, 0), 0.001):
            violations.append(f"{k} doubled vs baseline")
    return {"decision": "ABORT_AND_ROLLBACK" if violations else "PROCEED", "violations": violations,
            "rules": ABORT_RULES, "rules_status": "PROPOSED"}


def day2(root: pathlib.Path) -> dict:
    store = FileStateStore(root / "state")
    rows = []
    for vm in store.vm_ids():
        doc = store.load(vm)
        pend = [e for e in doc["journal"] if e["state"] not in ("done", "failed", "abandoned", "superseded")]
        rows.append({"vm_id": vm, "desired": doc["cpu"]["desired_vcpus"], "observed": doc["cpu"]["observed_vcpus"],
                     "pending_ops": len(pend), "needs_reconcile": bool(doc.get("needs_reconcile"))})
    return {"vms": rows, "evidence": str(evidence(root, "day2", {"vms": rows}))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["day0", "canary", "day2"])
    ap.add_argument("--root", default=".inv34")
    ap.add_argument("--config")
    ap.add_argument("--author", default="")
    ap.add_argument("--metrics", nargs=2)
    a = ap.parse_args()
    root = pathlib.Path(a.root)
    if a.action == "day0":
        out = day0(root, a.config, a.author)
    elif a.action == "canary":
        out = canary(*(json.loads(pathlib.Path(p).read_text()) for p in a.metrics))
    else:
        out = day2(root)
    print(json.dumps(out, indent=1, default=str))
    return 0 if out.get("decision", "PROCEED") == "PROCEED" else 4


if __name__ == "__main__":
    sys.exit(main())
