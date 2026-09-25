"""Deterministic empty-environment preflight + bootstrap health check (MC-010, INV-58-C040).

    python -B tools/bootstrap.py [--config site.json] [--dev-keys] [--json]

Exit 0 = every REQUIRED check passed; 3 = a required check failed.  pk_core and
jsonschema are reported; pk_core absence is BLOCKED (framework conformance cannot
run), never silently OK.  --dev-keys uses an in-memory provider (never for production).
"""
from __future__ import annotations

import importlib
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True


def main(argv):
    checks = []

    def add(name, ok, required, detail=""):
        checks.append({"check": name, "status": "PASS" if ok else ("FAIL" if required else "BLOCKED"),
                       "required": required, "detail": detail})

    add("python>=3.10", sys.version_info >= (3, 10), True, sys.version.split()[0])
    sys.path.insert(0, str(ROOT.parent))
    try:
        pkg = importlib.import_module(ROOT.name)
        add("package import", True, True, pkg.__version__)
        add("VERSION matches __version__", (ROOT / "VERSION").read_text().strip() == pkg.__version__, True)
    except Exception as e:  # noqa: BLE001
        add("package import", False, True, repr(e))
        pkg = None
    try:
        import jsonschema  # noqa: F401
        from importlib.metadata import version as _v
        add("jsonschema (test dependency)", True, False, _v("jsonschema"))
    except ModuleNotFoundError:
        add("jsonschema (test dependency)", False, False, "schema tests would skip -> release gate fails")
    pk_path = os.environ.get("PK_CORE_PATH")
    if pk_path:
        sys.path.insert(0, pk_path)
    try:
        importlib.import_module("pk_core")
        add("pk_core framework", True, False)
    except ModuleNotFoundError:
        add("pk_core framework", False, False, "not installed/pinned; framework conformance BLOCKED")
    if pkg is not None:
        config = importlib.import_module(ROOT.name + ".config")
        secret_refs = importlib.import_module(ROOT.name + ".secret_refs")
        service = importlib.import_module(ROOT.name + ".service")
        doc = {}
        if "--config" in argv:
            doc = json.loads(pathlib.Path(argv[argv.index("--config") + 1]).read_text())
        composed = config.compose(doc)
        try:
            config.validate(composed)
            add("configuration valid", True, True, config.digest(composed))
        except config.ConfigError as e:
            add("configuration valid", False, True, "; ".join(e.problems[:5]))
            composed = None
        if composed is not None and "--dev-keys" in argv:
            keys = {}
            resolver = secret_refs.SecretResolver({"kms": lambda n: keys.setdefault(n, os.urandom(32))})
            svc = service.MeshLayerService(resolver=resolver)
            try:
                svc.bootstrap(composed, author="bootstrap-preflight", source="tools/bootstrap.py")
                r = svc.readiness()
                add("bootstrap -> ready", r["ready"], True, svc.lifecycle.state)
                add("audit chain after bootstrap", svc.audit.verify()[0], True)
            except Exception as e:  # noqa: BLE001
                add("bootstrap -> ready", False, True, type(e).__name__)
        elif composed is not None:
            add("bootstrap -> ready", False, False, "skipped: needs a host key provider (or --dev-keys for a dry run)")
    failed = [c for c in checks if c["status"] == "FAIL"]
    if "--json" in argv:
        print(json.dumps({"checks": checks, "ok": not failed}, indent=2))
    else:
        for c in checks:
            print(f"{c['status']:8} {c['check']:32} {c['detail']}")
    return 3 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
