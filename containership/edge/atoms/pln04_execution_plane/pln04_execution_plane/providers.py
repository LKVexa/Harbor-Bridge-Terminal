"""Execution-tier provider layer (M03, M04, M10, M13, M40).

PLN-04 chooses the boundary; a *provider* creates it.  This module defines:

* ``ProviderRequest`` - immutable request (``PK_PROVIDER_REQUEST/1``) carrying
  workload, tenant, tier, policy digest, artifact digest, idempotency key,
  deadline and fencing epoch.
* ``LIFECYCLE`` - the provider-instance state machine, independent from the
  admission decision.
* ``ExecutionProvider`` - the contract every provider implements, including
  stale-epoch rejection and a zeroization receipt.
* ``ProviderRegistry`` - one approved provider per tier, no implicit fallback.
* ``ProcessProvider`` - a *real* POSIX process-tier provider (rlimits, new
  session, empty environment, private scratch dir, overwrite-then-delete
  zeroization).
* ``WasmProvider`` - explicit Wasm binding over the ``wasmtime`` CLI with fuel
  and memory limits and no pre-opened directories; unavailable (and therefore
  never attestable) when the runtime is absent.
* ``CommandProvider`` - JSON-over-stdio adapter for operator-supplied
  unikernel/microVM/VM drivers (e.g. a Firecracker or QEMU wrapper).
* ``ReferenceProvider`` - deterministic in-memory contract double with fault
  injection; refused by the ``production`` profile.
"""
from __future__ import annotations

import json
from collections import deque
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Callable, Mapping

from .errors import PlaneError
from .runtime import TIERS

# --------------------------------------------------------------------------- lifecycle (M13)

LIFECYCLE: Mapping[str, frozenset[str]] = MappingProxyType({
    "requested": frozenset({"reserved", "failed"}),
    "reserved": frozenset({"provisioning", "failed", "terminated"}),
    "provisioning": frozenset({"starting", "failed"}),
    "starting": frozenset({"active", "failed"}),
    "active": frozenset({"stopping", "quarantined", "orphaned"}),
    "quarantined": frozenset({"stopping"}),
    "orphaned": frozenset({"stopping"}),
    "stopping": frozenset({"zeroizing", "failed"}),
    "failed": frozenset({"zeroizing", "stopping"}),
    "zeroizing": frozenset({"terminated", "failed"}),
    "terminated": frozenset(),
})
TERMINAL = frozenset({"terminated"})
RESOURCE_HOLDING = frozenset({"provisioning", "starting", "active", "quarantined", "orphaned", "stopping", "failed", "zeroizing"})


def check_transition(current: str, target: str) -> None:
    if target not in LIFECYCLE.get(current, frozenset()):
        raise PlaneError("PLN04-STATE-004", details={"from_state": current, "to_state": target})


# --------------------------------------------------------------------------- request/response types

@dataclass(frozen=True, slots=True)
class Resources:
    cpu_milli: int = 1000
    memory_mib: int = 256

    def __post_init__(self) -> None:
        for name in ("cpu_milli", "memory_mib"):
            v = getattr(self, name)
            if not isinstance(v, int) or isinstance(v, bool) or v < 1:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    workload: str
    tenant: str
    tier: str
    policy_digest: str
    artifact_digest: str
    idempotency_key: str
    deadline_ns: int
    epoch: int
    resources: Resources = Resources()
    command: tuple[str, ...] = ()

    def envelope(self) -> dict:
        return {
            "schema": "PK_PROVIDER_REQUEST/1", "workload": self.workload, "tenant": self.tenant,
            "tier": self.tier, "policy_digest": self.policy_digest, "artifact_digest": self.artifact_digest,
            "idempotency_key": self.idempotency_key, "deadline_ns": self.deadline_ns, "epoch": self.epoch,
            "resources": {"cpu_milli": self.resources.cpu_milli, "memory_mib": self.resources.memory_mib},
        }


@dataclass(frozen=True, slots=True)
class ProviderInstance:
    provider_instance_id: str
    workload: str
    tier: str
    epoch: int
    provider: str
    provider_version: str
    started_ns: int


@dataclass(frozen=True, slots=True)
class ZeroizeReceipt:
    workload: str
    epoch: int
    method: str
    verified: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    tier: str
    available: bool
    isolation: tuple[str, ...]
    reason: str = ""


# --------------------------------------------------------------------------- base contract (M03)

class ExecutionProvider:
    """Common provider contract.  Subclasses implement the ``_do_*`` hooks.

    The base class enforces: tier match, deadline, stale-epoch rejection,
    idempotent start (same key => same instance), idempotent stop/destroy,
    bounded concurrency, and that zeroization produces a receipt.
    """

    tier: str = ""
    name: str = ""
    version: str = "0"
    reference: bool = False  # test doubles set True; production profile refuses them

    def __init__(self, *, max_concurrency: int = 64) -> None:
        if self.tier not in TIERS:
            raise ValueError(f"provider declares unknown tier {self.tier!r}")
        self._lock = threading.RLock()
        self._sem = threading.BoundedSemaphore(max_concurrency)
        self._epochs: dict[str, int] = {}
        # Epochs are globally monotonic (store.LeaseManager), so after a verified
        # zeroization the per-workload entry is pruned and its epoch raises a floor:
        # a stale command below the floor is still rejected, memory stays bounded.
        self._epoch_floor = 0
        self._by_key: dict[str, ProviderInstance] = {}
        self._live: dict[str, ProviderInstance] = {}
        # Starts whose outcome is unknown (exception or crash inside the hook).
        # They may hold resources, so stop/zeroize/list_instances include them:
        # an interrupted start can never leak an invisible instance.
        self._pending: dict[str, ProviderInstance] = {}

    # ---- hooks
    def probe(self) -> ProviderCapabilities:
        raise NotImplementedError

    def _do_start(self, request: ProviderRequest) -> str:
        raise NotImplementedError

    def _do_stop(self, workload: str, instance_id: str) -> None:
        raise NotImplementedError

    def _do_zeroize(self, workload: str, instance_id: str) -> tuple[str, bool, str]:
        raise NotImplementedError

    def _do_alive(self, workload: str, instance_id: str) -> bool:
        raise NotImplementedError

    # ---- fencing
    def _fence(self, workload: str, epoch: int) -> None:
        if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 1:
            raise PlaneError("PLN04-STATE-002", details={"workload": workload, "epoch": epoch})
        with self._lock:
            highest = self._epochs.get(workload, self._epoch_floor)
            if epoch < highest:
                raise PlaneError("PLN04-STATE-002", details={"workload": workload, "epoch": epoch, "expected_epoch": highest})
            self._epochs[workload] = epoch

    # ---- public API
    def start(self, request: ProviderRequest, clock_ns: Callable[[], int] = time.monotonic_ns) -> ProviderInstance:
        if request.tier != self.tier:
            raise PlaneError("PLN04-PROV-002", details={"tier": request.tier, "provider": self.name})
        if clock_ns() > request.deadline_ns:
            raise PlaneError("PLN04-TIME-001", details={"workload": request.workload})
        self._fence(request.workload, request.epoch)
        with self._lock:
            prior = self._by_key.get(request.idempotency_key)
            if prior is not None:
                if prior.workload != request.workload or prior.epoch != request.epoch:
                    raise PlaneError("PLN04-CONF-002", details={"workload": request.workload})
                return prior
            live = self._live.get(request.workload)
            if live is not None:
                # at most one live instance per workload inside a provider
                raise PlaneError("PLN04-STATE-002", details={"workload": request.workload, "epoch": request.epoch,
                                                             "expected_epoch": live.epoch, "reason": "already live"})
        if not self._sem.acquire(timeout=max(0.0, (request.deadline_ns - clock_ns()) / 1e9)):
            raise PlaneError("PLN04-TIME-001", details={"workload": request.workload, "reason": "provider concurrency"})
        with self._lock:
            self._pending[request.workload] = ProviderInstance("pending", request.workload, self.tier, request.epoch,
                                                               self.name, self.version, time.time_ns())
        try:
            try:
                instance_id = self._do_start(request)
            except PlaneError:
                raise
            except Exception as exc:  # provider-specific failure -> stable code
                raise PlaneError("PLN04-PROV-001", details={"provider": self.name, "workload": request.workload}, cause=exc) from None
            inst = ProviderInstance(instance_id, request.workload, self.tier, request.epoch, self.name, self.version, time.time_ns())
            with self._lock:
                self._by_key[request.idempotency_key] = inst
                self._live[request.workload] = inst
                self._pending.pop(request.workload, None)
            return inst
        finally:
            self._sem.release()

    def _held(self, workload: str) -> ProviderInstance | None:
        with self._lock:
            return self._live.get(workload) or self._pending.get(workload)

    def stop(self, workload: str, epoch: int) -> bool:
        self._fence(workload, epoch)
        inst = self._held(workload)
        if inst is None:
            return False
        try:
            self._do_stop(workload, inst.provider_instance_id)
        except PlaneError:
            raise
        except Exception as exc:
            raise PlaneError("PLN04-PROV-001", details={"provider": self.name, "workload": workload}, cause=exc) from None
        return True

    def zeroize(self, workload: str, epoch: int) -> ZeroizeReceipt:
        self._fence(workload, epoch)
        inst = self._held(workload)
        if inst is None:
            return ZeroizeReceipt(workload, epoch, "absent", True, "no resources held")
        method, verified, detail = self._do_zeroize(workload, inst.provider_instance_id)
        if verified:
            with self._lock:
                self._live.pop(workload, None)
                self._pending.pop(workload, None)
                self._epoch_floor = max(self._epoch_floor, self._epochs.pop(workload, epoch))
                for key in [k for k, v in self._by_key.items() if v.workload == workload]:
                    del self._by_key[key]
        return ZeroizeReceipt(workload, epoch, method, verified, detail)

    def observe(self, workload: str) -> str:
        inst = self._held(workload)
        if inst is None:
            return "absent"
        return "running" if self._do_alive(workload, inst.provider_instance_id) else "exited"

    def list_instances(self) -> tuple[ProviderInstance, ...]:
        with self._lock:
            return tuple(self._live.values()) + tuple(p for w, p in self._pending.items() if w not in self._live)


# --------------------------------------------------------------------------- registry

class ProviderRegistry:
    def __init__(self, *, allow_reference: bool) -> None:
        self._providers: dict[str, ExecutionProvider] = {}
        self._allow_reference = allow_reference
        self._lock = threading.Lock()

    def register(self, provider: ExecutionProvider) -> None:
        if provider.reference and not self._allow_reference:
            raise PlaneError("PLN04-PROV-002", details={"provider": provider.name, "reason": "reference provider refused by profile"})
        with self._lock:
            if provider.tier in self._providers:
                raise ValueError(f"duplicate provider for tier {provider.tier!r}")
            self._providers[provider.tier] = provider

    def get(self, tier: str) -> ExecutionProvider:
        provider = self._providers.get(tier)
        if provider is None:
            raise PlaneError("PLN04-PROV-002", details={"tier": tier})
        return provider

    def tiers(self) -> tuple[str, ...]:
        return tuple(t for t in TIERS if t in self._providers)

    def snapshot(self) -> list[dict]:
        out = []
        for tier in self.tiers():
            p = self._providers[tier]
            cap = p.probe()
            out.append({"tier": tier, "provider": p.name, "version": p.version, "reference": p.reference,
                        "available": cap.available, "isolation": list(cap.isolation), "reason": cap.reason})
        return out


# --------------------------------------------------------------------------- reference provider

class ReferenceProvider(ExecutionProvider):
    """Deterministic in-memory provider with fault injection (tests/contract suite only)."""

    reference = True
    version = "ref-1"

    def __init__(self, tier: str, **kw) -> None:
        self.tier = tier
        self.name = f"reference-{tier}"
        super().__init__(**kw)
        self.fail_start = 0
        self.fail_stop = 0
        self.zeroize_unverifiable = False
        self.start_delay_s = 0.0
        self.resources: dict[str, bytearray] = {}
        self.calls: deque[tuple[str, str]] = deque(maxlen=10000)

    def probe(self) -> ProviderCapabilities:
        return ProviderCapabilities(self.tier, True, ("reference-only",), "reference provider: no real isolation")

    def _do_start(self, request: ProviderRequest) -> str:
        self.calls.append(("start", request.workload))
        if self.start_delay_s:
            time.sleep(self.start_delay_s)
        if self.fail_start:
            self.fail_start -= 1
            raise OSError("injected start failure")
        self.resources[request.workload] = bytearray(os.urandom(64))
        return f"{self.name}:{request.workload}:{request.epoch}"

    def _do_stop(self, workload: str, instance_id: str) -> None:
        self.calls.append(("stop", workload))
        if self.fail_stop:
            self.fail_stop -= 1
            raise OSError("injected stop failure")

    def _do_zeroize(self, workload: str, instance_id: str) -> tuple[str, bool, str]:
        self.calls.append(("zeroize", workload))
        buf = self.resources.get(workload)
        if buf is not None:
            buf[:] = b"\x00" * len(buf)
            clean = not any(buf)
            if self.zeroize_unverifiable:
                return "overwrite", False, "injected: verification unavailable"
            del self.resources[workload]
            return "overwrite+verify", clean, "buffer overwritten and read back as zero"
        return "absent", True, ""

    def _do_alive(self, workload: str, instance_id: str) -> bool:
        return workload in self.resources


# --------------------------------------------------------------------------- process provider (real, POSIX)

class ProcessProvider(ExecutionProvider):
    """Runs the workload command as a child process with enforced limits (M10 partial).

    Enforced: RLIMIT_AS (memory), RLIMIT_CPU, RLIMIT_NOFILE, RLIMIT_NPROC (fork
    bombs), RLIMIT_CORE=0, new session, empty environment, private 0700 scratch
    directory as cwd.  NOT enforced (needs a sandbox such as seccomp/landlock/
    namespaces or a stronger tier): syscall filtering, network isolation,
    filesystem view restriction.  That is why ``process`` only satisfies the
    ``trusted`` class.
    """

    tier = "process"
    name = "posix-process"
    version = "1.0.0"

    def __init__(self, *, scratch_root: str | None = None, max_nofile: int = 64, max_nproc: int = 64, **kw) -> None:
        super().__init__(**kw)
        self._root = scratch_root or tempfile.gettempdir()
        self._max_nofile = max_nofile
        self._max_nproc = max_nproc
        self._procs: dict[str, tuple[subprocess.Popen, str]] = {}

    def probe(self) -> ProviderCapabilities:
        try:
            import resource  # noqa: F401
        except ImportError:
            return ProviderCapabilities(self.tier, False, (), "resource module unavailable (non-POSIX)")
        return ProviderCapabilities(self.tier, True, ("rlimits", "session", "empty-env", "private-scratch"))

    def _do_start(self, request: ProviderRequest) -> str:
        import resource
        if not request.command:
            raise ValueError("process tier requires a command")
        scratch = tempfile.mkdtemp(prefix="pln04-", dir=self._root)
        os.chmod(scratch, 0o700)
        mem = request.resources.memory_mib * 1024 * 1024
        cpu_s = max(1, request.resources.cpu_milli // 1000 * 60)
        nofile, nproc = self._max_nofile, self._max_nproc

        def limits() -> None:  # runs in the child before exec
            resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s))
            resource.setrlimit(resource.RLIMIT_NOFILE, (nofile, nofile))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            try:
                resource.setrlimit(resource.RLIMIT_NPROC, (nproc, nproc))
            except (ValueError, OSError):
                pass

        proc = subprocess.Popen(list(request.command), cwd=scratch, env={"HOME": scratch, "PATH": "/usr/bin:/bin"},
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                preexec_fn=limits, start_new_session=True, close_fds=True)
        self._procs[request.workload] = (proc, scratch)
        return f"pid:{proc.pid}"

    def _do_stop(self, workload: str, instance_id: str) -> None:
        import signal
        entry = self._procs.get(workload)
        if entry is None:
            return
        proc, _ = entry
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=5)
            except (ProcessLookupError, PermissionError):
                pass
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)

    def _do_zeroize(self, workload: str, instance_id: str) -> tuple[str, bool, str]:
        entry = self._procs.get(workload)
        if entry is None:
            return "absent", True, ""
        proc, scratch = entry
        if proc.poll() is None:
            return "scratch-overwrite", False, "process still running"
        for dirpath, _, files in os.walk(scratch):
            for name in files:
                path = os.path.join(dirpath, name)
                try:
                    size = os.path.getsize(path)
                    with open(path, "r+b") as fh:
                        fh.write(b"\x00" * size)
                        fh.flush()
                        os.fsync(fh.fileno())
                except OSError:
                    pass
        shutil.rmtree(scratch, ignore_errors=True)
        gone = not os.path.exists(scratch)
        if gone:
            self._procs.pop(workload, None)
        return "scratch-overwrite+unlink", gone, "process memory released to kernel on exit; scratch overwritten and removed"

    def _do_alive(self, workload: str, instance_id: str) -> bool:
        entry = self._procs.get(workload)
        return entry is not None and entry[0].poll() is None


# --------------------------------------------------------------------------- wasm provider (M04)

class WasmProvider(ProcessProvider):
    """Explicit Wasm binding via the ``wasmtime`` CLI (fuel + memory caps, no pre-opens, no env).

    The command's first element must be the module path; its digest is
    checked by the plane's artifact policy before start.
    """

    tier = "wasm"
    name = "wasmtime-cli"
    version = "cli"

    def __init__(self, *, wasmtime: str | None = None, fuel: int = 10_000_000_000, **kw) -> None:
        super().__init__(**kw)
        self._bin = wasmtime or shutil.which("wasmtime")
        self._fuel = fuel

    def probe(self) -> ProviderCapabilities:
        if not self._bin:
            return ProviderCapabilities(self.tier, False, (), "wasmtime runtime not installed")
        try:
            out = subprocess.run([self._bin, "--version"], capture_output=True, text=True, timeout=5)
            self.version = out.stdout.strip() or "unknown"
        except (OSError, subprocess.TimeoutExpired):
            return ProviderCapabilities(self.tier, False, (), "wasmtime not executable")
        return ProviderCapabilities(self.tier, True, ("wasm-sandbox", "fuel", "memory-cap", "no-preopens", "rlimits"))

    def _do_start(self, request: ProviderRequest) -> str:
        if not self._bin:
            raise OSError("wasmtime not installed")
        if not request.command:
            raise ValueError("wasm tier requires a module path")
        module, *args = request.command
        mem_bytes = request.resources.memory_mib * 1024 * 1024
        cmd = (self._bin, "run", "-W", f"max-memory-size={mem_bytes}", "-W", f"fuel={self._fuel}", module, *args)
        return super()._do_start(ProviderRequest(**{**{f: getattr(request, f) for f in request.__slots__}, "command": cmd}))


# --------------------------------------------------------------------------- command provider (unikernel/microvm/vm)

class CommandProvider(ExecutionProvider):
    """Adapter for operator-supplied drivers speaking JSON on stdin/stdout.

    ``driver`` is invoked as ``driver <op>`` with the provider request (or
    ``{"workload","instance_id","epoch"}``) on stdin and must print one JSON
    object: ``{"ok": true, "instance_id": ...}`` / ``{"ok": true, "alive": bool}``
    / ``{"ok": true, "zeroized": bool, "method": ...}``.  Timeouts and non-JSON
    output are provider failures.
    """

    def __init__(self, tier: str, driver: tuple[str, ...], *, name: str, version: str, timeout_s: float = 60.0, **kw) -> None:
        self.tier, self.name, self.version = tier, name, version
        super().__init__(**kw)
        self._driver = tuple(driver)
        self._timeout = timeout_s

    def _call(self, op: str, payload: dict) -> dict:
        proc = subprocess.run([*self._driver, op], input=json.dumps(payload), capture_output=True, text=True, timeout=self._timeout)
        if proc.returncode != 0:
            raise OSError(f"driver {op} exited {proc.returncode}")
        result = json.loads(proc.stdout.strip().splitlines()[-1])
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise OSError(f"driver {op} reported failure")
        return result

    def probe(self) -> ProviderCapabilities:
        try:
            r = self._call("probe", {"tier": self.tier})
            return ProviderCapabilities(self.tier, bool(r.get("available")), tuple(r.get("isolation", ())), str(r.get("reason", "")))
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            return ProviderCapabilities(self.tier, False, (), f"driver probe failed: {type(exc).__name__}")

    def _do_start(self, request: ProviderRequest) -> str:
        return str(self._call("start", request.envelope())["instance_id"])

    def _do_stop(self, workload: str, instance_id: str) -> None:
        self._call("stop", {"workload": workload, "instance_id": instance_id})

    def _do_zeroize(self, workload: str, instance_id: str) -> tuple[str, bool, str]:
        r = self._call("zeroize", {"workload": workload, "instance_id": instance_id})
        return str(r.get("method", "driver")), r.get("zeroized") is True, str(r.get("detail", ""))

    def _do_alive(self, workload: str, instance_id: str) -> bool:
        return self._call("observe", {"workload": workload, "instance_id": instance_id}).get("alive") is True
