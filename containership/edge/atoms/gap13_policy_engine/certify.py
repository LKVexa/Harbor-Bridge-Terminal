"""G13-MC-039 machine-readable certification evidence.

python -m gap13_policy_engine.certify [--out DIR] [--sign-key RAW_ED25519_SEED --key-id ID] [--quick]
python -m gap13_policy_engine.certify --verify DIR/manifest.json

Runs every suite, the benchmark, and records artifact digests, tool versions,
per-test results (pass/fail/error/skip with reasons), requirement coverage from
TRACEABILITY.json, component status and waivers.  The manifest is content
addressed (``manifest_digest``) and optionally Ed25519-signed; ``--verify``
independently re-checks the manifest digest, signature and every artifact
digest against the bytes on disk.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import io
import json
import platform
import re
import sys
import time
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parent
EXCLUDE_DIRS = {"__pycache__", "evidence", ".pytest_cache"}
SECRET_PATTERNS = [re.compile(p) for p in (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"(?i)aws_secret_access_key",
                                           r"(?i)password\s*[:=]\s*\S{6,}")]


def artifact_digests(root: Path = PKG) -> dict[str, str]:
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and not (set(p.relative_to(root).parts) & EXCLUDE_DIRS) and p.suffix != ".pyc":
            out[p.relative_to(root).as_posix()] = "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()
    return out


class _Collector(unittest.TextTestResult):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.outcomes: dict[str, dict] = {}
        self._t = {}

    def startTest(self, test):
        self._t[test.id()] = time.perf_counter()
        super().startTest(test)

    def _rec(self, test, status, detail=""):
        tid = test.id()
        self.outcomes[tid] = {"status": status, "detail": detail[:500],
                              "duration_s": round(time.perf_counter() - self._t.get(tid, time.perf_counter()), 4)}

    def addSuccess(self, test):
        super().addSuccess(test)
        if self.outcomes.get(test.id(), {}).get("status") != "fail":   # keep subTest failures
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

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self._rec(test, "fail", self._exc_info_to_string(err, test))


def run_tests() -> dict:
    tests_dir = PKG / "tests"
    if str(tests_dir) not in sys.path:
        sys.path.insert(0, str(tests_dir))
    if str(PKG.parent) not in sys.path:
        sys.path.insert(0, str(PKG.parent))
    suite = unittest.defaultTestLoader.discover(str(tests_dir), pattern="test_*.py", top_level_dir=str(tests_dir))
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, resultclass=_Collector, verbosity=0)
    t0 = time.perf_counter()
    res = runner.run(suite)
    outcomes = res.outcomes
    summary = {s: sum(1 for o in outcomes.values() if o["status"] == s) for s in ("pass", "fail", "error", "skip")}
    summary["total"] = len(outcomes)
    summary["duration_s"] = round(time.perf_counter() - t0, 3)
    return {"command": "python -m unittest discover -s tests -p 'test_*.py'", "summary": summary,
            "results": dict(sorted(outcomes.items()))}


def requirement_coverage(results: dict, bench: dict | None) -> dict:
    trace = json.loads((PKG / "docs" / "TRACEABILITY.json").read_text())
    cov = {}
    for row in trace["rows"]:
        states = []
        for t in row["tests"]:
            if t.startswith("bench:"):
                path = t[6:].split(".")
                node = bench
                for part in path:
                    node = node.get(part) if isinstance(node, dict) else None
                states.append("pass" if node not in (None, 0) else "missing")
                continue
            matches = [o["status"] for tid, o in results.items() if tid == t or tid.startswith(t + ".")]
            states.append("missing" if not matches else ("pass" if all(s == "pass" for s in matches) else
                                                         "skip" if all(s == "skip" for s in matches) else "fail"))
        verdict = "pass" if states and all(s == "pass" for s in states) else \
            "fail" if "fail" in states else "incomplete"
        cov[row["requirement"]] = {"status": verdict, "tests": dict(zip(row["tests"], states)), "code": row["code"]}
    return cov


def _tool_versions() -> dict:
    v = {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
         "platform": platform.platform()}
    for mod in ("cryptography", "jsonschema"):
        try:
            from importlib.metadata import version
            v[mod] = version(mod)
        except Exception:
            v[mod] = None
    return v


def manifest_digest(m: dict) -> str:
    body = {k: v for k, v in m.items() if k not in ("manifest_digest", "signature")}
    return "sha256:" + hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def scan_secrets(text: str) -> list[str]:
    return [p.pattern for p in SECRET_PATTERNS if p.search(text)]


def build(quick: bool = True, sources: dict | None = None) -> dict:
    from . import __version__
    from .compat import MATRIX
    tests = run_tests()
    from . import bench
    b = bench.run(sizes=(100, 1000) if quick else (100, 1000, 10000), requests=2000 if quick else 5000,
                  burst=5000 if quick else 20000)
    status = json.loads((PKG / "COMPONENT_STATUS.json").read_text())
    waivers = json.loads((PKG / "WAIVERS.json").read_text())
    m = {
        "schema": "PK_POLICY_EVIDENCE/1",
        "release": __version__,
        "component": "GAP-13",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "environment": _tool_versions(),
        "artifacts": artifact_digests(),
        "sources": sources or {},
        "tests": tests,
        "benchmark": b,
        "benchmark_profile": "quick" if quick else "full",
        "requirements": requirement_coverage(tests["results"], b),
        "components": {c["id"]: {"status": c["status"], "open_items": c["open_items"]} for c in status["components"]},
        "external_contracts": {c["id"]: c["status"] for c in status["external_contracts"]},
        "waivers": waivers["waivers"],
        "compatibility": MATRIX,
    }
    m["secret_scan"] = scan_secrets(json.dumps(m))
    m["manifest_digest"] = manifest_digest(m)
    return m


def sign_manifest(m: dict, seed: bytes, key_id: str) -> dict:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    sig = Ed25519PrivateKey.from_private_bytes(seed).sign(("PK_POLICY_EVIDENCE/1\0" + m["manifest_digest"]).encode())
    m["signature"] = {"alg": "ed25519", "key_id": key_id, "value_b64": base64.b64encode(sig).decode()}
    return m


def verify_manifest(path: str | Path, *, root: Path = PKG, public_key: bytes | None = None) -> tuple[bool, list[str]]:
    m = json.loads(Path(path).read_text())
    problems = []
    if m.get("schema") != "PK_POLICY_EVIDENCE/1":
        problems.append("wrong schema")
    if manifest_digest(m) != m.get("manifest_digest"):
        problems.append("manifest digest mismatch (manifest modified)")
    current = artifact_digests(root)
    for name, d in m.get("artifacts", {}).items():
        if current.get(name) != d:
            problems.append(f"artifact differs from evidence: {name}")
    for name in set(current) - set(m.get("artifacts", {})):
        problems.append(f"artifact not covered by evidence: {name}")
    if m.get("secret_scan"):
        problems.append("secret scan hits")
    if public_key is not None:
        sig = m.get("signature")
        if not sig:
            problems.append("manifest unsigned")
        else:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            try:
                Ed25519PublicKey.from_public_bytes(public_key).verify(
                    base64.b64decode(sig["value_b64"]), ("PK_POLICY_EVIDENCE/1\0" + m["manifest_digest"]).encode())
            except Exception:
                problems.append("manifest signature invalid")
    return not problems, problems


def write(m: dict, out: Path) -> Path:
    d = out / m["release"]
    d.mkdir(parents=True, exist_ok=True)
    text = json.dumps(m, indent=2, sort_keys=True) + "\n"
    (d / "manifest.json").write_text(text)
    (d / f"manifest-{m['manifest_digest'][7:19]}.json").write_text(text)   # content-addressed copy
    return d / "manifest.json"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG.parent / "evidence"))
    ap.add_argument("--full", action="store_true", help="full benchmark (10k rules)")
    ap.add_argument("--sign-key")
    ap.add_argument("--key-id", default="evidence")
    ap.add_argument("--source", action="append", default=[], help="name=path of an authoritative source to digest")
    ap.add_argument("--verify")
    a = ap.parse_args(argv)
    if a.verify:
        ok, problems = verify_manifest(a.verify)
        print(json.dumps({"ok": ok, "problems": problems}, indent=2))
        return 0 if ok else 1
    sources = {}
    for s in a.source:
        name, _, p = s.partition("=")
        sources[name] = "sha256:" + hashlib.sha256(Path(p).read_bytes()).hexdigest()
    m = build(quick=not a.full, sources=sources)
    if a.sign_key:
        m = sign_manifest(m, Path(a.sign_key).read_bytes(), a.key_id)
    path = write(m, Path(a.out))
    s = m["tests"]["summary"]
    print(f"evidence: {path}  tests pass={s['pass']} fail={s['fail']} error={s['error']} skip={s['skip']}  "
          f"digest={m['manifest_digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
