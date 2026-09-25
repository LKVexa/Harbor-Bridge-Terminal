"""Deterministic, idempotent bootstrap from an empty environment (C031, C040).

Single entry point: ``python -m inv18_completion_primitive bootstrap``.  Steps:
runtime version -> dependency lock (no third-party packages; pk_core pin) ->
artifact digests -> configuration validation -> smoke tests -> pk_core
registration check -> conformance preflight (fixtures).  Nothing in the package
is modified; the only output is ``bootstrap_report.json`` in the evidence dir,
overwritten on each run (repeat runs cannot corrupt anything).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import platform
import sys
import time

PKG = pathlib.Path(__file__).resolve().parent
MIN_PY = (3, 10)


def _step(steps, name, result, detail=""):
    steps.append({"step": name, "result": result, "detail": detail})


def run(evidence_dir: str | pathlib.Path | None = None, *, write: bool = True) -> dict:
    t0 = time.perf_counter()
    steps: list[dict] = []
    _step(steps, "python_version", "PASS" if sys.version_info[:2] >= MIN_PY else "FAIL",
          f"{platform.python_version()} (min {MIN_PY[0]}.{MIN_PY[1]})")
    lock = json.loads((PKG / "requirements.lock.json").read_text())
    third_party = [d for d in lock["dependencies"] if d["kind"] == "third-party" and d.get("required")]
    _step(steps, "dependency_lock", "PASS" if not third_party else "FAIL",
          f"{len(lock['dependencies'])} locked entries; runtime needs stdlib only")
    from .tools_verify import verify_tree
    probs = verify_tree(PKG)
    _step(steps, "artifact_digests", "PASS" if not probs else "FAIL", "; ".join(probs[:5]) or "SHA256SUMS intact")
    from . import config
    cfg_errors = {}
    for p in sorted((PKG / "config").glob("*.json")):
        errs = config.validate(config.layer(config.DEFAULTS, config.load_file(p)))
        if errs:
            cfg_errors[p.name] = [e.message for e in errs]
    _step(steps, "configuration", "PASS" if not cfg_errors else "FAIL", json.dumps(cfg_errors) if cfg_errors else "all config layers valid")
    try:
        from .future import Future
        from .runtime import Runtime
        f = Future(int); f.resolve(1)
        assert_ok = f.take() == ("ok", 1)
        rt = Runtime({"environment": "test"})
        r, q = rt.create(str); rt.resolve(r, "x")
        assert_ok = assert_ok and rt.take(q) == ("ok", "x") and rt.health()["ready"]
        _step(steps, "smoke", "PASS" if assert_ok else "FAIL", "future + governed runtime cycle")
    except Exception as exc:  # noqa: BLE001
        _step(steps, "smoke", "FAIL", repr(exc))
    pk = importlib.util.find_spec("pk_core") is not None
    pin = next((d for d in lock["dependencies"] if d["name"] == "pk_core"), {})
    _step(steps, "pk_core_registration", "PASS" if pk and pin.get("sha256") else "BLOCKED",
          "pk_core importable and pinned" if pk and pin.get("sha256") else
          "pk_core not available/pinned: audit integration (component.py) cannot register (W-C031)")
    from . import fixtures_runner
    fx = fixtures_runner.run_all()
    _step(steps, "conformance_preflight", "PASS" if all(x["passed"] for x in fx) else "FAIL",
          f"{sum(x['passed'] for x in fx)}/{len(fx)} fixtures")
    # the core may run without pk_core; bootstrap is ok when every non-BLOCKED step passes
    ok = all(s["result"] in ("PASS", "BLOCKED") for s in steps)
    report = {"schema": "INV18_BOOTSTRAP/1", "ok": ok, "steps": steps,
              "elapsed_s": round(time.perf_counter() - t0, 3), "python": platform.python_version(),
              "package_digest": hashlib.sha256((PKG / "SHA256SUMS").read_bytes()).hexdigest()
              if (PKG / "SHA256SUMS").exists() else None}
    if write:
        ed = pathlib.Path(evidence_dir) if evidence_dir else PKG / "evidence"
        ed.mkdir(parents=True, exist_ok=True)
        (ed / "bootstrap_report.json").write_text(json.dumps(report, indent=1))
    return report
