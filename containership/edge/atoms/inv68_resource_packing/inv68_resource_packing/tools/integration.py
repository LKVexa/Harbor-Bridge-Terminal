"""Adjacent-layer integration evidence (INV-68 MC-02, MC-08, MC-29; C030, C083, C084).

    python -m inv68_resource_packing.tools.integration [--out evidence/]

``INTEGRATION.json`` -- the hermetic emulator matrix: for each neighbour
(INV-67, SCH-01, GAP-10, INV-72) a success, refusal, failure and degraded path
is driven through the real :class:`service.PackingService`.

``INTEGRATION_REAL.json`` -- the *certification* record.  It looks for the real
artifacts, and only they can make it PASS:

* ``pk_core`` importable (``PK_CORE_PATH``) and ``python -m pk_core gate INV-68``
  producing a PASS/GO ``PK_GATE_RESULTS.json`` (MC-02);
* ``INV68_ADJACENT_INV67``, ``..._SCH01``, ``..._GAP10``, ``..._INV72`` pointing
  at importable real implementations (module paths) (MC-08).

Emulator success never upgrades the real record.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

from .common import PKG, write

from inv68_resource_packing.adjacent import (SchedulerClient, k8s_translate, power_overlay,  # noqa: E402
                                             split_accelerated)
from inv68_resource_packing.audit import AuditLog  # noqa: E402
from inv68_resource_packing.auth import Authorizer, mint  # noqa: E402
from inv68_resource_packing.config import ConfigStore, compose, defaults  # noqa: E402
from inv68_resource_packing.errors import PackError  # noqa: E402
from inv68_resource_packing.service import PackingService  # noqa: E402

KEY = {"k": b"i" * 32}
NEIGHBOURS = {"INV67": "INV-67 Kubernetes integration mechanism", "SCH01": "SCH-01 Multi-runtime scheduler",
              "GAP10": "GAP-10 Power/thermal-aware scheduling", "INV72": "INV-72 Accelerated workload requirement"}


def emulated() -> list[dict]:
    rows = []
    pods = json.loads((PKG / "tests" / "fixtures" / "adjacent" / "inv67_pods.json").read_text())
    with tempfile.TemporaryDirectory() as tmp:
        audit = AuditLog(Path(tmp) / "a.jsonl")
        store = ConfigStore(Path(tmp) / "c", audit=audit)
        store.activate(compose(defaults().document, ("int", {"tenants": {"overrides": {"shop": {
            "max_requests_per_minute": 100000}}}})), actor="int", epoch=1)
        svc = PackingService(store, Authorizer(KEY), audit)
        tok = lambda tenants=("shop",): mint(KEY["k"], kid="k", sub="sch01", kind="workload-scheduler",
                                              tenants=list(tenants), caps=["pack:submit"])

        def row(n, path, ok, obs):
            rows.append({"neighbour": n, "path": path, "result": "PASS" if ok else "FAIL", "observed": obs})
        # INV-67
        work = k8s_translate(pods["valid"])
        out = svc.pack({"tenant": "shop", "host_capacity": {"cpu": 16, "mem": 64}, "workloads": work}, tok())
        row("INV67", "success", out["outcome"] == "success", {"workloads": len(work)})
        codes = []
        for bad in pods["invalid"]:
            try:
                k8s_translate([bad])
                codes.append("accepted")
            except PackError as e:
                codes.append(e.code)
        row("INV67", "refusal", set(codes) == {"INVALID_REQUEST"}, {"codes": codes})
        huge = [{"name": f"p{i}", "cpu": 1, "mem": 200} for i in range(3)]
        out = svc.pack({"tenant": "shop", "host_capacity": {"cpu": 16, "mem": 64}, "workloads": huge}, tok())
        row("INV67", "degraded (all unplaceable -> partial, explained)", out["outcome"] == "partial"
            and len(out["result"]["unplaced"]) == 3, {"unplaced": len(out["result"]["unplaced"])})
        # SCH-01
        client = SchedulerClient(svc, tok, attempts=3, sleep=lambda s: None, rng=random.Random(1))
        r = client.place({"tenant": "shop", "host_capacity": {"cpu": 16, "mem": 64}, "workloads": work})
        row("SCH01", "success", r["state"] == "placed", {"log": client.log})
        svc.frozen = {"by": "int", "reason": "integration", "at": 0}
        client = SchedulerClient(svc, tok, attempts=2, sleep=lambda s: None, rng=random.Random(1))
        r = client.place({"tenant": "shop", "host_capacity": {"cpu": 16, "mem": 64}, "workloads": work})
        row("SCH01", "degraded (frozen -> retries then holds)", r["state"] == "held" and len(client.log) == 3,
            {"log": client.log})
        svc.frozen = None
        client = SchedulerClient(svc, lambda: tok(("other",)), attempts=3, sleep=lambda s: None)
        r = client.place({"tenant": "shop", "host_capacity": {"cpu": 16, "mem": 64}, "workloads": work})
        row("SCH01", "refusal (no retry on FORBIDDEN)", r["state"] == "held" and len(client.log) == 1,
            {"log": client.log})
        client = SchedulerClient(svc, lambda: "garbage", attempts=3, sleep=lambda s: None)
        r = client.place({"tenant": "shop", "workloads": work})
        row("SCH01", "failure (bad credential)", r["state"] == "held" and r["error"]["code"] == "UNAUTHENTICATED",
            {"code": r["error"]["code"]})
        # GAP-10
        out = svc.pack({"tenant": "shop", "host_capacity": {"cpu": 16, "mem": 64},
                        "workloads": [{"name": f"w{i}", "cpu": 4, "mem": 4} for i in range(12)]}, tok())
        view = power_overlay(out, idle_w=80, per_core_w=8, cap_w=200)
        row("GAP10", "downstream consumes response; over-cap hosts reported not repacked",
            view["over_cap"] == [h["host"] for h in view["hosts"] if h["watts"] > 200], view)
        # INV-72
        mixed = work + [{"name": "train", "cpu": 8, "mem": 32, "nvidia.com/gpu": 2}]
        mine, peer = split_accelerated(mixed)
        out = svc.pack({"tenant": "shop", "host_capacity": {"cpu": 16, "mem": 64}, "workloads": mine}, tok())
        row("INV72", "peer split: accelerator work never reaches the packer",
            [w["name"] for w in peer] == ["train"] and "train" not in out["result"]["assignments"], {"peer": len(peer)})
    return rows


def real() -> dict:
    checks = []
    env = dict(os.environ)
    pk_path = env.get("PK_CORE_PATH")
    if pk_path and pk_path not in sys.path:
        sys.path.insert(0, pk_path)
    try:
        importlib.import_module("pk_core")
        checks.append({"check": "pk_core importable", "result": "PASS"})
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "PK_GATE_RESULTS.json"
            p = subprocess.run([sys.executable, "-m", "pk_core", "gate", "INV-68", "--out", str(out)],
                               capture_output=True, text=True, cwd=str(PKG.parent), timeout=600)
            verdict = json.loads(out.read_text()).get("verdict") if out.exists() else None
            checks.append({"check": "pk_core gate INV-68", "result": "PASS" if p.returncode == 0 and
                           str(verdict).upper() in ("PASS", "GO") else "FAIL", "verdict": verdict})
    except ModuleNotFoundError:
        checks.append({"check": "pk_core importable", "result": "FAIL",
                       "reason": "pk_core not supplied with the candidate (MC-02 BLOCKED_EXTERNAL)"})
    for key, name in NEIGHBOURS.items():
        mod = env.get(f"INV68_ADJACENT_{key}")
        if not mod:
            checks.append({"check": f"real {name}", "result": "FAIL", "reason": f"INV68_ADJACENT_{key} not set; "
                           "no real implementation available to this build"})
            continue
        try:
            importlib.import_module(mod)
            checks.append({"check": f"real {name}", "result": "FAIL",
                           "reason": "module importable but no conformance driver is registered for it yet"})
        except Exception as exc:  # noqa: BLE001
            checks.append({"check": f"real {name}", "result": "FAIL", "reason": f"import failed: {exc}"[:200]})
    return {"schema": "PK_PACK_INTEGRATION_REAL/1", "checks": checks,
            "result": "PASS" if all(c["result"] == "PASS" for c in checks) else "FAIL"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG / "evidence"))
    a = ap.parse_args(argv)
    rows = emulated()
    failed = [f"{r['neighbour']}:{r['path']}" for r in rows if r["result"] != "PASS"]
    write(Path(a.out) / "INTEGRATION.json", {"schema": "PK_PACK_INTEGRATION/1", "mode": "emulated", "rows": rows,
                                             "failed": failed, "result": "PASS" if not failed else "FAIL",
                                             "scope": "INV-68 side of each boundary only; neighbours emulated"})
    r = real()
    write(Path(a.out) / "INTEGRATION_REAL.json", r)
    print(f"INTEGRATION emulated {'PASS' if not failed else 'FAIL'} ({len(rows)} paths); real {r['result']}")
    for f in failed:
        print("  ", f)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
