"""Operator CLI: ``python -m inv18_completion_primitive <command>``.

Commands: status, explain, bootstrap, verify-install, validate-config, conformance,
faults, bench, slo-report, rtm, gate, verify-evidence, drill {canary,rollback,disable}.
Exit codes: 0 ok; 1 failure; gate: 0 GO, 10 CONDITIONAL_GO, 20 NO_GO.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parent


def _rt(config_path: str | None = None):
    from . import config
    from .runtime import Runtime
    layers = [config.DEFAULTS]
    if config_path:
        layers.append(config.load_file(config_path))
    layers.append(config.from_env())
    return Runtime(config.ConfigStore(config.layer(*layers), author="cli"))


def _evid(p: str | None) -> pathlib.Path:
    d = pathlib.Path(p) if p else PKG / "evidence"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cmd_drill(kind: str, evid: pathlib.Path) -> int:
    from .config import ConfigStore
    from .errors import Rejected
    from .runtime import Runtime
    rt = Runtime(ConfigStore({"environment": "staging"}))
    rep: dict = {"drill": kind}
    if kind == "canary":
        # canary: new config on one runtime; halt criteria = invariant violation or failed health
        good = dict(rt.config.values())
        rev = rt.config.activate_or_rollback({**good, "trace_sampling": 0.2}, author="canary",
                                             health_check=lambda r: rt.health()["ready"])
        caps = [rt.create(int) for _ in range(200)]
        for r, q in caps:
            rt.resolve(r, 1); rt.take(q)
        ok = rt.health()["state"] == "HEALTHY" and not rt.metrics.counter("inv18_invariant_violations_total")
        # failed canary: a config whose health check fails is rolled back automatically
        bad = rt.config.activate_or_rollback({**good, "soft_outstanding": 1}, author="bad-canary",
                                             health_check=lambda r: False)
        rep.update(canary_revision=rev.revision_id, canary_ok=ok,
                   failed_canary_rolled_back=bad.rollback_of is not None)
        rep["pass"] = ok and bad.rollback_of is not None
    elif kind == "rollback":
        before = rt.config.active().revision_id
        rt.config.activate({**dict(rt.config.values()), "max_outstanding": 50_000, "soft_outstanding": 40_000,
                            "max_per_tenant": 5_000}, author="upgrade")
        inflight = [rt.create(int) for _ in range(20)]
        rb = rt.config.rollback(author="operator", reason="drill")
        for r, q in inflight:
            rt.resolve(r, 1); rt.take(q)
        rep.update(restored=rb.values == dict(rt.config.history[0].values), rolled_back_to=rb.revision_id,
                   original=before, inflight_completed=rt.outstanding == 0)
        rep["pass"] = rep["restored"] and rep["inflight_completed"]
    elif kind == "disable":
        admin = rt.admin_capability()
        pending = [rt.create(int) for _ in range(10)]
        rt.disable(admin, mode="drain", reason="drill")
        try:
            rt.create(int); refused = False
        except Rejected as exc:
            refused = exc.code == "COMPONENT_DISABLED"
        for r, q in pending:
            rt.resolve(r, 1); rt.take(q)
        unauthorized = False
        try:
            from .runtime import AdminCap
            rt.enable(AdminCap(rt.runtime_id, "0" * 32))
        except Rejected:
            unauthorized = True
        rt.enable(admin)
        rt.create(int)
        rep.update(new_work_refused=refused, existing_drained=True, unauthorized_enable_refused=unauthorized,
                   audit_ok=rt.audit.verify()[0])
        rep["pass"] = refused and unauthorized and rep["audit_ok"]
    else:
        print(f"unknown drill {kind}", file=sys.stderr)
        return 1
    (evid / f"drill_{kind}.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))
    return 0 if rep["pass"] else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m inv18_completion_primitive")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("status", "explain", "slo-report"):
        s = sub.add_parser(n); s.add_argument("--config")
    for n in ("bootstrap", "faults", "gate", "bench"):
        s = sub.add_parser(n); s.add_argument("--evidence-dir")
    sub.choices["bench"].add_argument("--full", action="store_true")
    sub.choices["gate"].add_argument("--no-write", action="store_true")
    s = sub.add_parser("validate-config"); s.add_argument("path")
    sub.add_parser("verify-install")
    sub.add_parser("conformance")
    sub.add_parser("rtm")
    s = sub.add_parser("verify-evidence"); s.add_argument("path", nargs="?")
    s = sub.add_parser("drill"); s.add_argument("kind", choices=["canary", "rollback", "disable"]); s.add_argument("--evidence-dir")
    a = ap.parse_args(argv)

    if a.cmd == "status":
        from .status import status, to_json
        print(to_json(status(_rt(a.config))))
        return 0
    if a.cmd == "explain":
        from .status import explain
        print(explain(_rt(a.config)))
        return 0
    if a.cmd == "slo-report":
        from .slo import report
        print(json.dumps(report(_rt(a.config)), indent=1))
        return 0
    if a.cmd == "bootstrap":
        from .bootstrap import run
        rep = run(_evid(a.evidence_dir))
        print(json.dumps(rep, indent=1))
        return 0 if rep["ok"] else 1
    if a.cmd == "verify-install":
        from .tools_verify import verify_tree
        probs = verify_tree(PKG)
        print("INTACT" if not probs else "\n".join(probs))
        return 0 if not probs else 1
    if a.cmd == "validate-config":
        from . import config
        errs = config.validate(config.layer(config.DEFAULTS, config.load_file(a.path)))
        for e in errs:
            print(f"INVALID {e.details.get('key')}: {e.message}")
        print("VALID" if not errs else f"{len(errs)} error(s)")
        return 0 if not errs else 1
    if a.cmd == "conformance":
        from .fixtures_runner import run_all
        res = run_all()
        for r in res:
            print(("PASS " if r["passed"] else "FAIL ") + r["id"] + ("" if r["passed"] else f"  {r.get('detail')}"))
        return 0 if all(r["passed"] for r in res) else 1
    if a.cmd == "faults":
        from .fault import run_all
        res = run_all()
        (_evid(a.evidence_dir) / "fault_results.json").write_text(json.dumps(res, indent=1))
        for r in res:
            print(("PASS " if r["passed"] else "FAIL ") + r["scenario"])
        return 0 if all(r["passed"] for r in res) else 1
    if a.cmd == "bench":
        from .bench import run
        res = run(quick=not a.full)
        (_evid(a.evidence_dir) / "bench_results.json").write_text(json.dumps(res, indent=1, default=str))
        print(json.dumps({k: res["micro"][k]["p99_us"] for k in res["micro"]}, indent=1))
        return 0
    if a.cmd == "rtm":
        from .certify import build_rtm, rtm_markdown, run_suite
        rtm = build_rtm(run_suite())
        print(rtm_markdown(rtm))
        return 0
    if a.cmd == "gate":
        from .certify import certify
        ev = certify(write=not a.no_write)
        for c in ev["checks"]:
            print(f"{c['result']:9} {c['check']:38} {c['detail'][:150]}")
        print(f"\nVERDICT: {ev['verdict']}  (seal {ev['seal']['sha256'][:16]})")
        if ev["unaccepted_conditions"]:
            print("unaccepted conditions: " + ", ".join(ev["unaccepted_conditions"]))
        return ev["exit_code"]
    if a.cmd == "verify-evidence":
        from .certify import verify
        ok, probs = verify(a.path)
        print("EVIDENCE VALID" if ok else "\n".join(probs))
        return 0 if ok else 1
    if a.cmd == "drill":
        return cmd_drill(a.kind, _evid(a.evidence_dir))
    return 1


if __name__ == "__main__":
    sys.exit(main())
