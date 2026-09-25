"""Minimal dependency-free test harness (pytest is unavailable in this env).

Discovers test_* functions in the given modules, runs each, and returns a
machine-readable result suitable for release evidence (INV-38-C020/C090).
"""
from __future__ import annotations
import importlib, json, sys, traceback, types

def run_module(mod: types.ModuleType) -> list[dict]:
    results = []
    for name in sorted(dir(mod)):
        if not name.startswith("test_"):
            continue
        fn = getattr(mod, name)
        if not callable(fn):
            continue
        rec = {"module": mod.__name__, "test": name, "status": "PASS", "error": ""}
        try:
            fn()
        except AssertionError as e:
            rec["status"] = "FAIL"; rec["error"] = str(e) or "assertion failed"
        except Exception as e:  # noqa
            rec["status"] = "ERROR"; rec["error"] = f"{type(e).__name__}: {e}"
            rec["trace"] = traceback.format_exc()
        results.append(rec)
    return results

def run_all(module_names: list[str]) -> dict:
    all_results = []
    for name in module_names:
        mod = importlib.import_module(name)
        all_results.extend(run_module(mod))
    passed = sum(r["status"] == "PASS" for r in all_results)
    return {"total": len(all_results), "passed": passed,
            "failed": len(all_results) - passed, "results": all_results}
