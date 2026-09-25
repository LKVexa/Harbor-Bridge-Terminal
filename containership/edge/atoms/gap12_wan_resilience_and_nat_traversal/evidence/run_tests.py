"""Run every test module and write machine-readable results (G12-H085-05,
G12-H100): one record per test with status PASS / FAIL / ERROR / SKIP, its
duration, its coverage tags, plus build identity (source digest, config
digest, interpreter, kernel, seed).  SKIP is recorded as SKIP and credits
nothing downstream.

    python3 -B evidence/run_tests.py [--out evidence/out/test_results.json] [--only module,...]
"""
from __future__ import annotations

import argparse
import collections
import threading
import hashlib
import importlib
import json
import os
import platform
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(PKG))
sys.dont_write_bytecode = True
PKGNAME = os.path.basename(PKG)

MODULES = ["test_path", "test_component", "test_a_traversal", "test_b_network", "test_c_quality", "test_d_security",
           "test_e_state", "test_f_g_config_obs", "test_h_engineering", "test_i_release"]

# v4.2.0 tests are kept byte-identical; their relevance is declared here instead of in the file.
LEGACY_TAGS = {
    "test_path": [("G12-H085", "unit"), ("G12-H085", "coverage"), ("G12-H085", "deterministic"),
                  ("G12-C029", "state-machine"), ("G12-C028", "state-machine")],
    "test_component": [],
}


def source_digest() -> str:
    sys.path.insert(0, os.path.join(PKG, "ops"))
    import build
    h = hashlib.sha256()
    for rel in build.files():
        with open(os.path.join(PKG, rel), "rb") as fh:
            h.update(rel.encode() + b"\0" + hashlib.sha256(fh.read()).digest())
    return h.hexdigest()


class Collector(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.records = []
        self._t0 = {}

    def startTest(self, test):
        super().startTest(test)
        self._t0[test.id()] = time.monotonic()

    def _rec(self, test, status, detail=""):
        fn = getattr(test, test._testMethodName, None)
        tags = list(getattr(fn, "__covers__", []))
        mod = test.__class__.__module__.rsplit(".", 1)[-1]
        tags += LEGACY_TAGS.get(mod, [])
        self.records.append({"id": test.id().replace(PKGNAME + ".tests.", ""), "module": mod, "status": status,
                             "seconds": round(time.monotonic() - self._t0.get(test.id(), time.monotonic()), 4),
                             "covers": [list(t) for t in tags], "detail": detail[-1500:]})

    def addSuccess(self, test):
        self._rec(test, "PASS")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._rec(test, "FAIL", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self._rec(test, "ERROR", self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._rec(test, "SKIP", reason)


class LineCoverage:
    """Stdlib line coverage for this package's runtime modules (all threads)."""

    def __init__(self, roots):
        self.roots = tuple(roots)
        self.hits = collections.defaultdict(set)

    def _local(self, frame, event, arg):
        if event == "line":
            self.hits[frame.f_code.co_filename].add(frame.f_lineno)
        return self._local

    def _global(self, frame, event, arg):
        if frame.f_code.co_filename.startswith(self.roots):
            return self._local
        return None

    def start(self):
        threading.settrace(self._global)
        sys.settrace(self._global)

    def stop(self):
        sys.settrace(None)
        threading.settrace(None)

    def report(self) -> dict:
        import ast
        out = {}
        files = []
        for root in self.roots:
            files += [os.path.join(root, f) for f in sorted(os.listdir(root)) if f.endswith(".py")] if os.path.isdir(root) else [root]
        for path in files:
            if True:
                with open(path) as fh:
                    tree = ast.parse(fh.read())
                lines = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.stmt) and not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if not (isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant)):
                            lines.add(node.lineno)
                hit = self.hits.get(path, set()) & lines
                rel = os.path.relpath(path, PKG)
                out[rel] = {"statements": len(lines), "covered": len(hit),
                            "ratio": round(len(hit) / len(lines), 4) if lines else 1.0}
        return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "out", "test_results.json"))
    ap.add_argument("--only", default="")
    ap.add_argument("--no-coverage", action="store_true")
    a = ap.parse_args(argv)
    cov = None if a.no_coverage else LineCoverage([os.path.join(PKG, "wan"), PKG + os.sep + "path.py"])
    mods = [m for m in MODULES if not a.only or m in a.only.split(",")]
    loader = unittest.TestLoader()
    col = Collector()
    t0 = time.time()
    if cov:
        cov.start()
    try:
        for m in mods:
            mod = importlib.import_module(f"{PKGNAME}.tests.{m}")
            loader.loadTestsFromModule(mod).run(col)
    finally:
        if cov:
            cov.stop()
    from gap12_wan_resilience_and_nat_traversal.wan import config
    doc = {"schema": "G12-TEST-RESULTS/1", "started": t0, "finished": time.time(),
           "build": {"version": open(os.path.join(PKG, "VERSION")).read().strip(), "source_digest": source_digest(),
                     "config_digest": config.fingerprint(config.defaults()), "python": platform.python_version(),
                     "implementation": platform.python_implementation(), "platform": platform.platform(),
                     "kernel": platform.release(), "seed": 20260922},
           "summary": {s: sum(r["status"] == s for r in col.records) for s in ("PASS", "FAIL", "ERROR", "SKIP")},
           "coverage": cov.report() if cov else None,
           "tests": col.records}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(doc, fh, indent=1)
    print(json.dumps(doc["summary"]))
    for r in col.records:
        if r["status"] in ("FAIL", "ERROR"):
            print(r["status"], r["id"], r["detail"].splitlines()[-1] if r["detail"] else "")
    return 0 if not (doc["summary"]["FAIL"] or doc["summary"]["ERROR"]) else 1


if __name__ == "__main__":
    sys.exit(main())
