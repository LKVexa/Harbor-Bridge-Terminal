# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Operator tooling (GAP-062, GAP-038, GAP-048, GAP-026): bootstrap, health, rollout, rollback, disable.

``python -m pk_components.inv30_capability_hardware_sandbox.ops <cmd>``

Rollout state lives in a JSON file (``--state``) written atomically; every
transition is appended to the tamper-evident audit ledger next to it. Stages:
off → canary(1%) → canary(5%) → staged(25%) → staged(50%) → full(100%).
``promote`` refuses to advance unless the supplied health/SLO evidence is green;
``rollback`` returns to the previous stage; ``disable`` is the emergency stop
(rollout=off, service must invalidate all capabilities on next start).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from .audit import AuditLedger

STAGES = [("off", 0), ("canary", 1), ("canary", 5), ("staged", 25), ("staged", 50), ("full", 100)]


def _load(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"schema": "INV30_ROLLOUT/1", "index": 0, "history": [], "disabled": False}


def _save(path: Path, st: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    with os.fdopen(fd, "w") as fh:
        json.dump(st, fh, indent=1, sort_keys=True)
    os.replace(tmp, path)


def _audit(path: Path) -> AuditLedger:
    return AuditLedger(path.with_suffix(".audit.jsonl"))


def promote(path: Path, *, operator: str, health: dict) -> dict:
    st = _load(path)
    if st["disabled"]:
        raise SystemExit("refused: emergency-disabled; run `enable` after incident review")
    bad = [k for k in ("error_rate_ok", "latency_ok", "invariant_violations_zero") if not health.get(k)]
    if bad:
        _audit(path).append("rollout.promote", "refused", operator=operator, failing=bad)
        raise SystemExit(f"refused: health gates failing {bad}")
    if st["index"] >= len(STAGES) - 1:
        raise SystemExit("already at full rollout")
    st["history"].append(st["index"])
    st["index"] += 1
    _save(path, st)
    _audit(path).append("rollout.promote", "ok", operator=operator, stage=STAGES[st["index"]])
    return status(path)


def rollback(path: Path, *, operator: str, reason: str) -> dict:
    st = _load(path)
    st["index"] = st["history"].pop() if st["history"] else 0
    _save(path, st)
    _audit(path).append("rollout.rollback", "ok", operator=operator, reason=reason, stage=STAGES[st["index"]])
    return status(path)


def disable(path: Path, *, operator: str, reason: str) -> dict:
    st = _load(path)
    st.update(disabled=True, index=0, history=[])
    _save(path, st)
    _audit(path).append("emergency.disable", "ok", operator=operator, reason=reason)
    return status(path)


def enable(path: Path, *, operator: str, reason: str) -> dict:
    st = _load(path)
    st["disabled"] = False
    _save(path, st)
    _audit(path).append("emergency.enable", "ok", operator=operator, reason=reason)
    return status(path)


def status(path: Path) -> dict:
    st = _load(path)
    name, pct = STAGES[st["index"]]
    led = _audit(path)
    return {"schema": "INV30_ROLLOUT_STATUS/1", "stage": name, "percent": 0 if st["disabled"] else pct,
            "disabled": st["disabled"], "audit_ok": not led.verify(), "audit_head": led.head}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="inv30-ops")
    ap.add_argument("cmd", choices=["env", "health", "bootstrap", "status", "promote", "rollback", "disable",
                                    "enable", "config-check"])
    ap.add_argument("--state", default="inv30_rollout.json")
    ap.add_argument("--operator", default=os.environ.get("USER", "operator"))
    ap.add_argument("--reason", default="")
    ap.add_argument("--health-json", default="")
    ap.add_argument("--context", default="datacenter")
    ap.add_argument("--mode", default=None)
    a = ap.parse_args(argv)
    p = Path(a.state)
    if a.cmd == "env":
        from .discovery import environment_report
        out = environment_report()
    elif a.cmd == "config-check":
        from .config import digest, load
        cfg = load(a.context, mode=a.mode)
        out = {"ok": True, "digest": digest(cfg), "mode": cfg["mode"], "context": cfg["deployment_context"]}
    elif a.cmd in ("health", "bootstrap"):
        from .authz import Authenticator, MintingAuthority
        from .config import load
        from .service import CapabilityService
        cfg = load(a.context, mode=a.mode)
        key = os.urandom(32)
        svc = CapabilityService(cfg, authenticator=Authenticator(), authority=MintingAuthority(key))
        out = svc.health()
    elif a.cmd == "status":
        out = status(p)
    elif a.cmd == "promote":
        out = promote(p, operator=a.operator, health=json.loads(a.health_json or "{}"))
    else:
        out = {"rollback": rollback, "disable": disable, "enable": enable}[a.cmd](p, operator=a.operator,
                                                                               reason=a.reason or "unspecified")
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
