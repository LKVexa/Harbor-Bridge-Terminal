"""MC-002 -- host/runtime adapter: policy in Python, execution in a real engine.

Instantiation sequence (fixed order): (1) identity verified by caller,
(2) policy decision, (3) binary admission (`wasm_loader.admit`: digest,
format, import->capability surface), (4) resource-table/quota reservation,
(5) engine instantiation with *only* the granted host functions bound,
(6) guest start under a wall-time limit, (7) teardown and audit.

The bundled engine binding is V8 (Node >= 18) for **core** Wasm modules using
the INV-13 core ABI.  Component-model binaries are refused with
UNSUPPORTED_VERSION until a component-model engine (e.g. Wasmtime) binding
is added behind the same ``Engine`` protocol -- see COMPONENT_STATUS.json.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Protocol

from .errors import ErrorCode, Inv13Error
from . import wasm_loader

ADAPTER_JS = Path(__file__).with_name("adapter_v8.mjs")
SUPPORTED_ENGINES = {"v8-node": ">=18"}


class Engine(Protocol):
    name: str
    def run(self, binary: bytes, grant: dict[str, Any], entry: str, timeout: float) -> dict[str, Any]: ...


class V8NodeEngine:
    name = "v8-node"

    def __init__(self, node: str | None = None) -> None:
        self.node = node or shutil.which("node")
        if not self.node:
            raise Inv13Error(ErrorCode.PROVIDER_UNAVAILABLE, "node not found")
        try:
            ver = subprocess.run([self.node, "--version"], capture_output=True, text=True, timeout=10).stdout.strip()
            major = int(ver.lstrip("v").split(".")[0])
        except (OSError, ValueError, subprocess.SubprocessError):
            raise Inv13Error(ErrorCode.PROVIDER_UNAVAILABLE, "engine not runnable") from None
        if major < 18:
            raise Inv13Error(ErrorCode.UNSUPPORTED_VERSION, ver)
        self.version = ver

    def run(self, binary: bytes, grant: dict[str, Any], entry: str, timeout: float) -> dict[str, Any]:
        req = json.dumps({"module_b64": base64.b64encode(binary).decode(), "grant": grant, "entry": entry})
        env = {"PATH": os.environ.get("PATH", ""), "NODE_OPTIONS": ""}  # no ambient env passes through
        try:
            p = subprocess.run([self.node, "--no-warnings", str(ADAPTER_JS)], input=req, capture_output=True,
                               text=True, timeout=timeout, env=env, cwd="/")
        except subprocess.TimeoutExpired:
            raise Inv13Error(ErrorCode.TIMED_OUT, "guest wall-time limit") from None
        except OSError:
            raise Inv13Error(ErrorCode.PROVIDER_UNAVAILABLE, "engine crashed or missing") from None
        try:
            return json.loads(p.stdout)
        except ValueError:
            raise Inv13Error(ErrorCode.PROVIDER_UNAVAILABLE, p.stderr[-500:]) from None


class RuntimeAdapter:
    def __init__(self, engine: Engine, *, allowed_digests: set[str] | None = None,
                 clock_resolution_ns: int = 1_000_000, stdout_limit: int = 65536, random_limit: int = 65536) -> None:
        self.engine, self.allowed = engine, allowed_digests
        self.defaults = {"clock_resolution_ns": clock_resolution_ns, "stdout_limit": stdout_limit,
                         "random_limit": random_limit}

    def instantiate_and_run(self, binary: bytes, granted: set[str], *, entry: str = "run",
                            timeout: float = 10.0) -> dict[str, Any]:
        info = wasm_loader.admit(binary, granted, allowed_digests=self.allowed)
        grant = {"capabilities": sorted(wasm_loader.required_capabilities(info)), **self.defaults}
        res = self.engine.run(binary, grant, entry, timeout)
        if not res.get("ok"):
            err = res.get("error") or {}
            code = next((c for c in ErrorCode if c.value == err.get("code")), ErrorCode.INTERNAL)
            raise Inv13Error(code, err.get("message"))
        # engine's own import view must equal ours (conformance cross-check)
        if sorted(map(tuple, res["imports"])) != sorted((m, n, "function") for m, n, _ in info.imports):
            raise Inv13Error(ErrorCode.INTERNAL, "engine/loader import view mismatch")
        res["stdout"] = base64.b64decode(res.get("stdout", ""))
        res["digest"] = info.digest
        return res
