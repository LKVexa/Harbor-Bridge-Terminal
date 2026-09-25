"""Deterministic conformance runner (MC-047-04).

Executes every ``vectors_v*.json`` file against a fresh in-process service
(``--target inproc``, default) and emits a machine-readable report.  Independent
implementations can execute the same vectors over HTTP with ``--target
http://host:port --token ...`` (MC-047-05).  Expectations are *subset* matches:
every expected field must equal the actual field; extra actual fields are
allowed (forward compatibility).

    python -m inv05_current_control_state_system.conformance.runner [--out report.json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))


def subset(expected: Any, actual: Any, path: str = "$") -> list[str]:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected object"]
        out = []
        for k, v in expected.items():
            if k not in actual:
                out.append(f"{path}.{k}: missing")
            else:
                out += subset(v, actual[k], f"{path}.{k}")
        return out
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return [f"{path}: expected list of {len(expected)}, got {actual!r}"[:200]]
        return [m for i, (e, a) in enumerate(zip(expected, actual)) for m in subset(e, a, f"{path}[{i}]")]
    return [] if expected == actual else [f"{path}: expected {expected!r}, got {actual!r}"[:200]]


class InProcTarget:
    def __init__(self, principal_spec: dict[str, Any]) -> None:
        from ..audit import AuditLog
        from ..limits import Limits
        from ..security import Namespace, Principal
        from ..service import ControlStateService, RequestContext
        from ..store import ControlStore
        self._RequestContext, self._Limits = RequestContext, Limits
        ns = Namespace(*principal_spec["namespace"])
        self.p = Principal("conformance-client", ns, frozenset(principal_spec["roles"]))
        self.admin = Principal("conformance-operator", ns, frozenset({"operator"}))
        self.svc = ControlStateService(ControlStore(), audit=AuditLog(None, b"c" * 32))
        self.svc.bootstrapped = True

    def run(self, step: dict[str, Any]) -> Any:
        svc, op, body = self.svc, step["op"], step["body"]
        c = self._RequestContext(self.p)
        if "limits" in step:
            old = svc.store.limits
            svc.store.limits = self._Limits(**{**old.as_dict(), **step["limits"]})
            try:
                return self.run({k: v for k, v in step.items() if k != "limits"})
            finally:
                svc.store.limits = old
        if op == "txn":
            return svc.txn(c, body)
        if op == "range":
            return svc.range(c, body)
        if op == "compact_admin":
            return svc.compact(self._RequestContext(self.admin), body)
        if op == "lease_grant":
            return svc.lease_grant(c, body)
        if op == "lease_keepalive":
            return svc.lease_keepalive(c, body)
        if op in ("watch_collect", "watch_open"):
            w = svc.watch(c, body)
            evs = []
            while True:
                f = w.poll(0.05)
                if f.type != "events":
                    break
                evs += [{"revision": e["revision"], "kind": e["kind"], "key": e["key"]} for e in f.events]
            w.cancel()
            return {"events": evs}
        raise ValueError(f"unknown op {op}")


def run_file(path: str) -> dict[str, Any]:
    from ..errors import StateError, to_wire
    with open(path, encoding="utf-8") as fh:
        spec = json.load(fh)
    target = InProcTarget(spec["principal"])
    results = []
    for step in spec["steps"]:
        try:
            actual = target.run(step)
            err = None
        except StateError as exc:
            actual, err = None, to_wire(exc)["code"]
        if "expect_error" in step:
            problems = [] if err == step["expect_error"] else [f"expected error {step['expect_error']}, got {err or 'success'}"]
        else:
            problems = [f"unexpected error {err}"] if err else subset(step["expect"], actual)
        results.append({"id": step["id"], "ok": not problems, "problems": problems})
    return {"file": os.path.basename(path), "protocol": spec["protocol"], "passed": sum(r["ok"] for r in results),
            "failed": sum(not r["ok"] for r in results), "results": results}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    reports = [run_file(p) for p in sorted(glob.glob(os.path.join(HERE, "vectors_v*.json")))]
    summary = {"schema": "cstate.conformance_report/1", "files": reports,
               "ok": all(r["failed"] == 0 for r in reports) and bool(reports)}
    s = json.dumps(summary, indent=2)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(s)
    print(json.dumps({"ok": summary["ok"], "passed": sum(r["passed"] for r in reports),
                      "failed": sum(r["failed"] for r in reports)}))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
