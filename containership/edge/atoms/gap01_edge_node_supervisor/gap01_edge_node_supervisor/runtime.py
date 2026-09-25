"""Workload runtime manager (3) and runtime isolation integration (11).

The manager speaks to runtimes through the :class:`RuntimeAdapter` protocol
(launch/stop/kill/inspect/list/reclaim_proof).  Concrete production adapters
for Wasm (wasmtime), microVMs (Firecracker) and unikernels plug in behind the
protocol; this package ships :class:`ProcessAdapter` (real OS processes, used
for integration tests and as a reference) and :class:`FakeRuntime` (a
deterministic, fault-injectable simulator).

A workload is only considered *terminated* when the adapter returns a
reclaim proof: the process/VM is gone and its resources are released.  A stop
that cannot be proven leaves the workload resident (fail closed).
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Protocol

from .errors import SupervisorError

RUNTIME_KINDS = ("wasm", "microvm", "unikernel", "process")


@dataclass
class WorkloadSpec:
    name: str
    trust_class: str
    kind: str = "process"
    image: str = ""
    argv: tuple[str, ...] = ()
    memory_mb: int = 64


@dataclass
class ReclaimProof:
    workload: str
    terminated: bool
    resources_released: bool
    evidence: dict = field(default_factory=dict)

    @property
    def proven(self) -> bool:
        return self.terminated and self.resources_released


class RuntimeAdapter(Protocol):
    kind: str

    def launch(self, spec: WorkloadSpec) -> str: ...
    def stop(self, name: str, grace_s: float) -> None: ...
    def kill(self, name: str) -> None: ...
    def inspect(self, name: str) -> dict: ...
    def list(self) -> list[str]: ...
    def reclaim_proof(self, name: str) -> ReclaimProof: ...


class FakeRuntime:
    """Deterministic fault-injectable runtime for tests and chaos drills."""

    def __init__(self, kind: str = "wasm") -> None:
        self.kind = kind
        self.running: dict[str, WorkloadSpec] = {}
        self.stubborn: set[str] = set()      # ignore graceful stop
        self.unkillable: set[str] = set()    # ignore kill too
        self.leak: set[str] = set()          # terminate but do not release resources
        self.hang_launch = False
        self.calls: list[tuple[str, str]] = []

    def launch(self, spec: WorkloadSpec) -> str:
        self.calls.append(("launch", spec.name))
        if self.hang_launch:
            raise SupervisorError("E_RUNTIME", "launch timed out")
        self.running[spec.name] = spec
        return spec.name

    def stop(self, name: str, grace_s: float) -> None:
        self.calls.append(("stop", name))
        if name not in self.stubborn:
            self.running.pop(name, None)

    def kill(self, name: str) -> None:
        self.calls.append(("kill", name))
        if name not in self.unkillable:
            self.running.pop(name, None)

    def inspect(self, name: str) -> dict:
        return {"name": name, "running": name in self.running}

    def list(self) -> list[str]:
        return sorted(self.running)

    def reclaim_proof(self, name: str) -> ReclaimProof:
        gone = name not in self.running
        return ReclaimProof(name, gone, gone and name not in self.leak,
                            {"adapter": "fake", "kind": self.kind})


class ProcessAdapter:
    """Reference adapter over real OS processes (POSIX process groups)."""

    kind = "process"

    def __init__(self) -> None:
        self.procs: dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()

    def launch(self, spec: WorkloadSpec) -> str:
        if not spec.argv:
            raise SupervisorError("E_BAD_REQUEST", "process workload needs argv")
        p = subprocess.Popen(list(spec.argv), stdin=subprocess.DEVNULL,  # noqa: S603 - argv list, no shell
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=(os.name == "posix"))
        with self._lock:
            self.procs[spec.name] = p
        return str(p.pid)

    def _signal(self, name: str, sig: int) -> None:
        p = self.procs.get(name)
        if p is None or p.poll() is not None:
            return
        try:
            if os.name == "posix":
                os.killpg(p.pid, sig)
            else:
                p.terminate() if sig != getattr(signal, "SIGKILL", 9) else p.kill()
        except ProcessLookupError:
            pass

    def stop(self, name: str, grace_s: float) -> None:
        self._signal(name, signal.SIGTERM)
        p = self.procs.get(name)
        if p is not None:
            try:
                p.wait(timeout=max(0.0, grace_s))
            except subprocess.TimeoutExpired:
                pass

    def kill(self, name: str) -> None:
        self._signal(name, getattr(signal, "SIGKILL", signal.SIGTERM))
        p = self.procs.get(name)
        if p is not None:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass

    def inspect(self, name: str) -> dict:
        p = self.procs.get(name)
        return {"name": name, "running": bool(p and p.poll() is None),
                "pid": p.pid if p else None, "returncode": p.returncode if p else None}

    def list(self) -> list[str]:
        return sorted(n for n, p in self.procs.items() if p.poll() is None)

    def reclaim_proof(self, name: str) -> ReclaimProof:
        p = self.procs.get(name)
        if p is None:
            return ReclaimProof(name, True, True, {"adapter": "process", "note": "never launched"})
        exited = p.poll() is not None
        group_gone = True
        if os.name == "posix" and exited:
            try:
                os.killpg(p.pid, 0)
                group_gone = False
            except (ProcessLookupError, PermissionError):
                group_gone = True
        return ReclaimProof(name, exited, exited and group_gone,
                            {"adapter": "process", "pid": p.pid, "returncode": p.returncode,
                             "process_group_gone": group_gone})


class RuntimeManager:
    """Routes workloads to adapters by kind and enforces proven termination."""

    def __init__(self, adapters: dict[str, RuntimeAdapter]) -> None:
        unknown = set(adapters) - set(RUNTIME_KINDS)
        if unknown:
            raise SupervisorError("E_CONFIG", f"unknown runtime kinds {sorted(unknown)}")
        self.adapters = dict(adapters)
        self.placements: dict[str, str] = {}  # workload -> kind

    def adapter_for(self, name: str) -> RuntimeAdapter:
        kind = self.placements.get(name)
        if kind is None:
            raise SupervisorError("E_UNKNOWN_WORKLOAD", name)
        return self.adapters[kind]

    def launch(self, spec: WorkloadSpec) -> str:
        if spec.kind not in self.adapters:
            raise SupervisorError("E_RUNTIME", f"no adapter for kind {spec.kind!r}")
        handle = self.adapters[spec.kind].launch(spec)
        self.placements[spec.name] = spec.kind
        return handle

    def terminate(self, name: str, *, grace_s: float, force: bool) -> ReclaimProof:
        ad = self.adapter_for(name)
        ad.stop(name, grace_s)
        proof = ad.reclaim_proof(name)
        if not proof.terminated and force:
            ad.kill(name)
            proof = ad.reclaim_proof(name)
        if proof.proven:
            self.placements.pop(name, None)
        return proof

    def observed(self) -> dict[str, str]:
        """Workloads the runtimes report as running -> kind."""
        out: dict[str, str] = {}
        for kind, ad in self.adapters.items():
            for n in ad.list():
                out[n] = kind
        return out


def sleeper_argv(seconds: float = 60) -> tuple[str, ...]:
    return (sys.executable, "-c", f"import time; time.sleep({seconds})")


def _now() -> float:
    return time.monotonic()
