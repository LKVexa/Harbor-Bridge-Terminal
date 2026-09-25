"""Machine-readable unittest runner (C020, C082, C090).

Every test is recorded with id ``tests/<file>::<Class>::<method>``, status
(pass | fail | error | skip), skip reason, duration and the requirement tags
found on a ``REQ:`` line of its docstring.  A test is *mandatory* unless its
docstring contains ``OPTIONAL``.  Environment labels (python, platform,
``INV18_CONTEXT``) are attached so evidence says where it was produced.
"""
from __future__ import annotations

import io
import json
import os
import pathlib
import platform
import re
import sys
import time
import unittest

PKG = pathlib.Path(__file__).resolve().parent
TAG = re.compile(r"REQ:\s*([^\n]+)")


def tags_of(test: unittest.TestCase) -> tuple[list[str], bool]:
    doc = getattr(test, "_testMethodDoc", None) or ""
    cls_doc = type(test).__doc__ or ""
    tags: list[str] = []
    for d in (cls_doc, doc):
        for m in TAG.finditer(d):
            tags += re.findall(r"\b(C\d{3}|INV18-[A-Z]+-\d{3}|INV-18-C\d{3})\b", m.group(1))
    norm = []
    for t in tags:
        if re.fullmatch(r"C\d{3}", t):
            t = "INV-18-" + t
        norm.append(t)
    return sorted(set(norm)), "OPTIONAL" not in doc


def test_id(test: unittest.TestCase) -> str:
    mod = type(test).__module__.rsplit(".", 1)[-1]
    return f"tests/{mod}.py::{type(test).__name__}::{test._testMethodName}"


class _Result(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.records: list[dict] = []
        self._t0 = 0.0

    def startTest(self, test):
        self._t0 = time.perf_counter()
        super().startTest(test)

    def _rec(self, test, status, detail=None):
        tags, mandatory = tags_of(test)
        self.records.append({"id": test_id(test), "status": status, "detail": (detail or "")[-2000:] or None,
                             "tags": tags, "mandatory": mandatory,
                             "duration_s": round(time.perf_counter() - self._t0, 4)})

    def addSuccess(self, test):
        super().addSuccess(test)
        self._rec(test, "pass")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._rec(test, "fail", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self._rec(test, "error", self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._rec(test, "skip", reason)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._rec(test, "fail", "expected failure is not accepted as evidence")

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._rec(test, "fail", "unexpected success")


def environment() -> dict:
    return {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "system": platform.system(), "machine": platform.machine(),
            "context": os.environ.get("INV18_CONTEXT", "local"), "optimize": sys.flags.optimize}


def run(pattern: str = "test_*.py", verbosity: int = 1) -> dict:
    root = PKG.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    loader = unittest.TestLoader()
    suite = loader.discover(str(PKG / "tests"), pattern=pattern, top_level_dir=str(PKG / "tests"))
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=verbosity, resultclass=_Result)
    t0 = time.perf_counter()
    res = runner.run(suite)
    recs = sorted(res.records, key=lambda r: r["id"])
    counts: dict[str, int] = {}
    for r in recs:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"schema": "INV18_TEST_RESULTS/1", "environment": environment(), "elapsed_s": round(time.perf_counter() - t0, 2),
            "counts": counts, "total": len(recs), "tests": recs,
            "log_tail": stream.getvalue()[-4000:]}


if __name__ == "__main__":
    out = run()
    print(json.dumps(out, indent=1))
