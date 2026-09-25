"""Deterministic bootstrap (item 22) and process entrypoint.

Startup is a fixed, ordered list of steps; each step records (name, ok, detail)
and the first failure aborts before any watch or side effect starts. The
bootstrap record's digest is exported on /configz and in the audit trail.

    python -m inv67_kubernetes_integration_mechanism.plane.bootstrap --config cfg.json --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from typing import Any

from . import PLANE_VERSION, compat
from .config import ConfigStore, digest
from .secrets import FileSecretProvider

STEPS = ("python-version", "config-load", "config-validate", "compat-matrix", "secrets-resolve",
         "downstream-endpoint", "state-dir")


def run(config_path: str, *, secret_root: str | None, state_dir: str | None, kube_version: str | None = None) -> dict:
    rec: dict[str, Any] = {"schema": "INV67_BOOTSTRAP/1", "version": PLANE_VERSION, "steps": [], "ok": False}

    def step(name, fn):
        try:
            detail = fn()
            rec["steps"].append({"name": name, "ok": True, "detail": detail})
            return True
        except Exception as e:  # noqa: BLE001 - every failure is recorded and aborts
            rec["steps"].append({"name": name, "ok": False, "detail": f"{type(e).__name__}: {e}"})
            return False

    raw = {}
    cfg = {}

    def load():
        nonlocal raw
        with open(config_path, encoding="utf-8") as fh:
            raw = json.load(fh)
        return hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()

    def validate():
        nonlocal cfg
        cfg = ConfigStore(raw).active
        return digest(cfg)

    def matrix():
        compat.check_peer("python", platform.python_version())
        if kube_version:
            compat.check_peer("kubernetes", kube_version)
        return {"python": platform.python_version(), "kubernetes": kube_version or "not-probed"}

    def secrets_():
        ref = cfg["downstream"]["tokenSecretRef"]
        if not ref:
            return "no secrets referenced"
        if not secret_root:
            raise RuntimeError("secret refs configured but no secret root mounted")
        FileSecretProvider(secret_root).get(ref)
        return "resolved (value not recorded)"

    def endpoint():
        if not cfg["downstream"]["endpoint"]:
            raise RuntimeError("no downstream endpoint configured; refusing to start a controller that cannot place")
        return cfg["downstream"]["endpoint"]

    def state():
        if not state_dir or not os.path.isdir(state_dir) or not os.access(state_dir, os.W_OK):
            raise RuntimeError("state dir for journal/audit is missing or not writable")
        return state_dir

    def interpreter():
        compat.check_peer("python", platform.python_version())
        return platform.python_version()

    steps = [interpreter, load, validate, matrix, secrets_, endpoint, state]
    for name, fn in zip(STEPS, steps, strict=True):
        if not step(name, fn):
            break
    else:
        rec["ok"] = True
    rec["digest"] = hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(prog="inv67-controller")
    ap.add_argument("--config", required=True)
    ap.add_argument("--secret-root", default="/var/run/inv67/secrets")
    ap.add_argument("--state-dir", default="/var/lib/inv67")
    ap.add_argument("--check", action="store_true", help="run bootstrap checks only and print the record")
    a = ap.parse_args(argv)
    rec = run(a.config, secret_root=a.secret_root, state_dir=a.state_dir)
    print(json.dumps(rec, indent=2))
    if not rec["ok"]:
        return 2
    if a.check:
        return 0
    print("controller loop requires an in-cluster API server; not started from this archive", file=sys.stderr)
    return 3


if __name__ == "__main__":
    sys.exit(main())
