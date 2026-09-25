"""Execution backends and the killable isolation boundary (C025, C031, C056).

``ProcessExecutor`` runs every operation in a fresh, single-use child process
(fork-free ``spawn`` start method, so no parent state is inherited).  Guest
execution is pre-empted by wall clock: the child is killed when the deadline
passes.  Host capabilities stay in the parent: the child sends
``(name, argument)`` over a pipe and the parent calls the real callback on a
bounded worker thread with its own per-call timeout, so neither a runaway guest
nor a hung host callback can hold the run past its deadline.

``WasmBackend`` is the seam for the ADR-0001 production engine (wasmtime, pinned
in ``requirements/wasm.lock``).  If the pinned engine is not importable at the
pinned version it fails closed with ``backend unavailable``; it never falls back
to the reference VM in a prod-like profile.
"""
from __future__ import annotations

import concurrent.futures as cf
import multiprocessing as mp
import threading
import time

from . import runtime

_CTX = mp.get_context("spawn")
MAX_HOST_CALLS_PER_RUN = 1_000


class _HostProxy:
    def __init__(self, conn):
        self.conn = conn

    def __call__(self, argument):
        self.conn.send(("call", self.name, argument))
        kind, payload = self.conn.recv()
        if kind == "ok":
            return payload
        raise RuntimeError(payload)   # class name only; runtime maps to "host error: RuntimeError"


def _child_warm(conn):
    """Pre-started single-use worker: blocks for exactly one job, runs it, exits."""
    try:
        msg = conn.recv()
    except EOFError:
        return
    if msg[0] != "job":
        return
    _child(conn, *msg[1:])


def _child(conn, program, limits, caps):
    host = {}
    for name in caps:
        p = _HostProxy(conn)
        p.name = name
        host[name] = p
    try:
        res = runtime.run(program, caps=caps, host=host, **limits)
        conn.send(("done", res))
    except BaseException as exc:  # pragma: no cover - defensive
        conn.send(("crash", type(exc).__name__))
    finally:
        conn.close()


class ProcessExecutor:
    """``warm`` > 0 keeps that many *unused* single-use workers pre-started (C066).
    A warm worker has never run guest code, so per-operation fresh-instance
    isolation is preserved; only interpreter start-up leaves the critical path."""
    name = "reference-vm/process"

    def __init__(self, host_workers: int = 4, warm: int = 0):
        self._pool = cf.ThreadPoolExecutor(max_workers=host_workers, thread_name_prefix="inv70-host")
        self.warm_target = warm
        self._warm: list = []
        self._wlock = threading.Lock()
        self._refill()

    def _spawn_warm(self):
        parent, child = _CTX.Pipe()
        proc = _CTX.Process(target=_child_warm, args=(child,), daemon=True)
        proc.start()
        child.close()
        return proc, parent

    def _refill(self):
        with self._wlock:
            self._warm = [(p, c) for p, c in self._warm if p.is_alive()]
            need = self.warm_target - len(self._warm)
        for _ in range(max(0, need)):
            w = self._spawn_warm()
            with self._wlock:
                self._warm.append(w)

    def _take(self, program, limits, caps):
        with self._wlock:
            w = self._warm.pop() if self._warm else None
        if w is not None:
            proc, parent = w
            try:
                parent.send(("job", program, limits, caps))
                if self.warm_target:
                    threading.Thread(target=self._refill, daemon=True).start()
                return proc, parent
            except (BrokenPipeError, OSError):
                proc.kill()
        parent, child = _CTX.Pipe()
        proc = _CTX.Process(target=_child, args=(child, program, limits, caps), daemon=True)
        proc.start()
        child.close()
        return proc, parent

    def execute(self, program, *, limits: dict, caps: frozenset, host: dict, wall_clock_s: float,
                host_call_timeout_s: float, cancel=None) -> dict:
        t0 = time.monotonic()
        proc, parent = self._take(program, limits, sorted(caps))
        calls = 0
        try:
            while True:
                remaining = wall_clock_s - (time.monotonic() - t0)
                if cancel is not None and cancel.cancelled:
                    return {"trap": "cancelled", "fuel": -1}
                if remaining <= 0:
                    return {"trap": "deadline exceeded", "fuel": -1}
                if not parent.poll(min(remaining, 0.05)):
                    if not proc.is_alive() and not parent.poll(0):
                        return {"trap": "worker crashed", "fuel": -1}
                    continue
                try:
                    msg = parent.recv()
                except EOFError:
                    return {"trap": "worker crashed", "fuel": -1}
                if msg[0] == "done":
                    return msg[1]
                if msg[0] == "crash":
                    return {"trap": "worker crashed", "fuel": -1}
                _, name, arg = msg
                calls += 1
                if calls > MAX_HOST_CALLS_PER_RUN:
                    return {"trap": "host call budget exceeded", "fuel": -1}
                fn = host.get(name) if name in caps else None
                if fn is None:
                    parent.send(("err", "unbound"))
                    continue
                fut = self._pool.submit(fn, arg)
                try:
                    out = fut.result(timeout=max(0.0, min(host_call_timeout_s, wall_clock_s - (time.monotonic() - t0))))
                    parent.send(("ok", out))
                except cf.TimeoutError:
                    fut.cancel()
                    return {"trap": "host call timeout", "fuel": -1}
                except Exception:
                    parent.send(("err", "host"))
        finally:
            if proc.is_alive():
                proc.kill()
            proc.join(1)
            parent.close()

    def close(self):
        self.warm_target = 0
        with self._wlock:
            for p, c in self._warm:
                p.kill()
            self._warm = []
        self._pool.shutdown(wait=False, cancel_futures=True)


class InlineExecutor:
    """Dev-only profile: no wall-clock pre-emption.  Config forbids it in prod/edge."""
    name = "reference-vm/inline"

    def execute(self, program, *, limits, caps, host, wall_clock_s, host_call_timeout_s, cancel=None):
        return runtime.run(program, caps=caps, host=host, **limits)

    def close(self):
        pass


# ------------------------------------------------------------------ C031 seam
WASM_ENGINE = "wasmtime"
WASM_ENGINE_PINNED = None   # filled from requirements/wasm.lock


def _load_pin(path=None):
    import pathlib
    p = pathlib.Path(path or pathlib.Path(__file__).parent / "requirements" / "wasm.lock")
    for line in p.read_text().splitlines():
        line = line.strip()
        if line.startswith(WASM_ENGINE + "=="):
            return line.split("==", 1)[1].split()[0]
    return None


class WasmBackend:
    """Per-operation Wasm execution: fresh Store per run, fuel + epoch deadline,
    StoreLimits for memory/tables/instances, no WASI, imports only for granted
    capabilities.  Requires the pinned engine; otherwise ``available`` is False."""
    name = "wasm"

    def __init__(self):
        self.pinned = _load_pin()
        self.reason = None
        try:
            import wasmtime  # noqa: F401
        except ModuleNotFoundError:
            self.engine = None
            self.reason = "engine not installed"
            return
        ver = getattr(wasmtime, "__version__", None)
        if self.pinned is None or ver != self.pinned:
            self.engine = None
            self.reason = f"engine version {ver} != pinned {self.pinned}"
            return
        self.engine = wasmtime

    @property
    def available(self) -> bool:
        return self.engine is not None

    def execute(self, module_bytes, *, limits, caps, host, wall_clock_s, host_call_timeout_s, cancel=None):
        if not self.available:
            return {"trap": "backend unavailable", "fuel": 0}
        wt = self.engine
        cfg = wt.Config()
        cfg.consume_fuel = True
        cfg.epoch_interruption = True
        eng = wt.Engine(cfg)
        try:
            module = wt.Module(eng, module_bytes)
        except Exception:
            return {"trap": "invalid module", "fuel": 0}
        store = wt.Store(eng)
        store.set_limits(memory_size=limits["max_memory_bytes"], table_elements=1024, instances=1,
                         tables=1, memories=1)
        store.set_fuel(limits["fuel"])
        store.set_epoch_deadline(1)
        import threading
        timer = threading.Timer(wall_clock_s, eng.increment_epoch)
        timer.start()
        try:
            linker = wt.Linker(eng)
            for imp in module.imports:
                if imp.module != "inv70" or imp.name not in caps or imp.name not in host:
                    return {"trap": f"capability denied: {imp.name}", "fuel": 0}
                fn = host[imp.name]
                linker.define_func("inv70", imp.name, wt.FuncType([wt.ValType.i64()], [wt.ValType.i64()]),
                                   lambda x, _fn=fn: int(_fn(int(x))))
            inst = linker.instantiate(store, module)
            run = inst.exports(store).get("run")
            if run is None:
                return {"trap": "invalid module", "fuel": 0}
            try:
                val = run(store)
            except wt.Trap as t:
                msg = str(t).lower()
                reason = "out of fuel" if "fuel" in msg else "deadline exceeded" if "interrupt" in msg else "guest trap"
                return {"trap": reason, "fuel": limits["fuel"] - store.get_fuel()}
            return {"ok": val, "fuel": limits["fuel"] - store.get_fuel()}
        finally:
            timer.cancel()
