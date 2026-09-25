"""Adjacent-layer execution adapter: V8 WebAssembly engine via a sandboxed Node process.

This is the "INV-44 Wasm hardening system / runtime" side of the boundary for
integration and release certification (C030, C083).  Each execution runs in a
fresh ``node`` process (process-isolation tier, INV-39) with:

* an **empty environment** and a private temporary working directory;
* the **Node permission model** enabled (``--permission``): filesystem writes,
  child processes and worker threads are denied; only the runner script is readable;
* ``--disallow-code-generation-from-strings`` (no ``eval``/``Function`` in the host);
* a hard wall-clock timeout (the process is killed; no partial state survives);
* host imports restricted to an explicit per-module allowlist.

Engine-level SFI requirements that this repository does not implement itself -
code-page W^X, randomised code placement, a protected (non-linear-memory) call
stack and the engine's own base-register handling - are *preflighted* here only to
the extent a user-space process can observe them (engine identity/version and the
permission model); they are recorded as engine prerequisites in ADR-0001.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

from .errors import SfiError

RUNNER = Path(__file__).with_name("engine_runner.js")
SUPPORTED_NODE_MAJORS = frozenset({20, 22, 24})


def _node() -> Optional[str]:
    return shutil.which("node")


def preflight(expected_major: Optional[int] = None) -> dict[str, Any]:
    """Detect engine prerequisites.  Never raises; returns a structured report."""
    node = _node()
    rep: dict[str, Any] = {"engine": "node-v8", "node_path": bool(node), "ok": False, "checks": {}}
    if not node:
        rep["checks"]["node_present"] = False
        return rep
    try:
        ver = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=10, env={}).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        rep["checks"]["node_present"] = False
        return rep
    major = int(ver.lstrip("v").split(".")[0]) if ver.startswith("v") else -1
    rep["version"] = ver
    rep["checks"]["node_present"] = True
    rep["checks"]["supported_major"] = major in SUPPORTED_NODE_MAJORS
    rep["checks"]["pinned_major"] = expected_major is None or major == expected_major
    probe = ("try{require('fs').writeFileSync('x','y');console.log('WRITE')}catch(e){console.log('DENIED')}")
    with tempfile.TemporaryDirectory() as td:
        script = Path(td) / "probe.js"
        script.write_text(probe)
        try:
            r = subprocess.run([node, *_perm_flags(major), f"--allow-fs-read={script}", str(script)],
                               capture_output=True, text=True, timeout=10, env={}, cwd=td)
            rep["checks"]["permission_model_denies_writes"] = r.stdout.strip() == "DENIED"
        except (OSError, subprocess.TimeoutExpired):
            rep["checks"]["permission_model_denies_writes"] = False
    rep["ok"] = all(rep["checks"].values())
    return rep


def _perm_flags(major: int) -> list[str]:
    return ["--permission"] if major >= 22 else ["--experimental-permission"]


class NodeV8Engine:
    def __init__(self, *, timeout: float = 5.0, expected_major: Optional[int] = 22):
        self.timeout = timeout
        self.report = preflight(expected_major)
        if not self.report["ok"]:
            raise SfiError("SFI_DEPENDENCY_UNAVAILABLE", "engine preflight failed", dependency="node-v8",
                           reason=",".join(k for k, v in self.report["checks"].items() if not v))
        self.major = int(self.report["version"].lstrip("v").split(".")[0])

    def run(self, job: dict[str, Any]) -> dict[str, Any]:
        """Run a job ``{modules:[{name,bytes,allow}], memory_pages, canary, calls, regions}``."""
        wire = dict(job)
        wire["modules"] = [{"name": m["name"], "b64": base64.b64encode(m["bytes"]).decode(),
                            "allow": list(m.get("allow", ()))} for m in job["modules"]]
        node = _node()
        if not node:
            raise SfiError("SFI_DEPENDENCY_UNAVAILABLE", "node not found", dependency="node-v8")
        with tempfile.TemporaryDirectory(prefix="inv45-exec-") as td:
            argv = [node, *_perm_flags(self.major), f"--allow-fs-read={RUNNER}",
                    "--disallow-code-generation-from-strings", "--max-old-space-size=256", str(RUNNER)]
            try:
                r = subprocess.run(argv, input=json.dumps(wire), capture_output=True, text=True,
                                   timeout=self.timeout, env={}, cwd=td)
            except subprocess.TimeoutExpired:
                raise SfiError("SFI_DEADLINE_EXCEEDED", "engine execution timed out; process killed",
                               limit=self.timeout, dependency="node-v8") from None
            except OSError:
                raise SfiError("SFI_DEPENDENCY_UNAVAILABLE", "engine could not start", dependency="node-v8") from None
        if r.returncode != 0:
            raise SfiError("SFI_DEPENDENCY_UNAVAILABLE", "engine process failed", dependency="node-v8",
                           observed=r.returncode)
        try:
            out = json.loads(r.stdout)
        except ValueError:
            raise SfiError("SFI_DEPENDENCY_UNAVAILABLE", "engine returned malformed output",
                           dependency="node-v8") from None
        if out.get("error"):
            raise SfiError("SFI_POLICY_REJECTED", "engine refused instantiation", reason=out["error"][:200])
        return out


def validate_with_engine(modules: list[bytes], timeout: float = 30.0) -> list[bool]:
    """Differential oracle: V8's ``WebAssembly.validate`` for each module (batch, one process)."""
    node = _node()
    if not node:
        raise SfiError("SFI_DEPENDENCY_UNAVAILABLE", "node not found", dependency="node-v8")
    js = ("let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{const a=JSON.parse(s);"
          "process.stdout.write(JSON.stringify(a.map(b=>WebAssembly.validate(Buffer.from(b,'base64')))))})")
    r = subprocess.run([node, "-e", js], input=json.dumps([base64.b64encode(m).decode() for m in modules]),
                       capture_output=True, text=True, timeout=timeout, env={"PATH": os.defpath})
    return json.loads(r.stdout)
