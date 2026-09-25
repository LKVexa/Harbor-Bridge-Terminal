"""Conformance runner (C029).  Consumes only fixture JSON + a small adapter
interface, so alternate implementations can be tested without repository
internals:  python -m <pkg>.conformance.run [--adapter module:factory] [--out report.json]

Adapter contract (see conformance/README.md): validate_manifest(m),
new_receiver(m) -> obj with accept(i, bytes), assemble() -> bytes,
resume_token() -> dict; negotiate(offer) -> dict.  Errors must expose ``.code``.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent


def default_adapter():
    sys.path.insert(0, str(PKG.parent))
    return importlib.import_module(PKG.name)


def check_lock() -> list[str]:
    lock = json.loads((HERE / "FIXTURES.lock").read_text())["fixtures"]
    problems = []
    present = {p.name for p in (HERE / "fixtures").glob("*.json")}
    for name, digest in lock.items():
        p = HERE / "fixtures" / name
        if not p.exists():
            problems.append(f"missing:{name}")
        elif hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            problems.append(f"modified:{name}")
    problems += [f"unlocked:{n}" for n in sorted(present - set(lock))]
    return problems


def run_one(impl, f) -> tuple[bool, str]:
    inp, exp = f["input"], f["expect"]
    try:
        if f["kind"] == "manifest":
            impl.validate_manifest(inp["manifest"])
            if "object_hex" in inp:
                obj = bytes.fromhex(inp["object_hex"])
                if hashlib.sha256(obj).hexdigest() != exp["object_sha256"]:
                    return False, "object sha mismatch"
                if impl.manifest(obj, inp["manifest"]["chunk"])["object"] != exp["object_digest"]:
                    return False, "object digest mismatch"
        elif f["kind"] == "chunk":
            r = impl.Receiver(inp["manifest"])
            for _ in range(inp.get("repeat", 1)):
                r.accept(inp["index"], bytes.fromhex(inp["payload_hex"]))
        elif f["kind"] in ("object", "resume"):
            data = b"conformance" * 1000
            r = impl.Receiver(inp["manifest"])
            c = inp["manifest"]["chunk"]
            for i in inp["indices"]:
                r.accept(i, data[i * c:(i + 1) * c])
            if f["kind"] == "resume":
                if r.resume_token() != exp["resume"]:
                    return False, "resume token mismatch"
            else:
                out = r.assemble()
                if hashlib.sha256(out).hexdigest() != exp["object_sha256"]:
                    return False, "assembled object mismatch"
        elif f["kind"] == "negotiate":
            got = impl.negotiate(inp["offer"])
            if exp.get("chosen") and got != exp["chosen"]:
                return False, f"negotiated {got}"
    except Exception as exc:  # noqa: BLE001
        code = getattr(exc, "code", type(exc).__name__)
        if exp["ok"]:
            return False, f"unexpected error {code}"
        return (code == exp["code"]), f"code={code}"
    return (exp["ok"], "ok" if exp["ok"] else f"expected {exp['code']}, got success")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.adapter:
        mod, fn = a.adapter.split(":")
        impl = getattr(importlib.import_module(mod), fn)()
    else:
        impl = default_adapter()
    lock_problems = check_lock()
    results = []
    for p in sorted((HERE / "fixtures").glob("*.json")):
        f = json.loads(p.read_text(encoding="utf-8"))
        ok, detail = run_one(impl, f)
        results.append({"id": f["id"], "pass": ok, "detail": detail})
    report = {"schema": "INV37_CONFORMANCE_REPORT/1", "implementation": getattr(impl, "__name__", str(impl)),
              "version": getattr(impl, "__version__", None), "fixtures": len(results),
              "passed": sum(r["pass"] for r in results), "lock_problems": lock_problems, "results": results}
    report["status"] = "PASS" if report["passed"] == len(results) and not lock_problems and results else "FAIL"
    text = json.dumps(report, indent=1)
    if a.out:
        Path(a.out).write_text(text)
    print(json.dumps({k: report[k] for k in ("status", "fixtures", "passed", "lock_problems")}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
