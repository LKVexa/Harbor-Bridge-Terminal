"""GAP02-MC-14 probe executor/service loop, MC-38 crash/restart/resume,
MC-37 circuit breaker integration, MC-40 resource ceilings (per-probe deadline,
bounded concurrency), MC-39 quarantine honouring.

Probes run in a bounded thread pool with a per-probe deadline and a sweep
deadline. A wedged probe is abandoned (its capability becomes unprobed with
TIMEOUT); it can never block publication of the sweep.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import json
import os
import tempfile
import threading
import time
from typing import Callable, Iterable

from .breaker import CircuitBreaker
from .errors import Code
from .evidence import ProbeEvidence, unknown
from .quarantine import QuarantineRegistry
from .sweep import SnapshotStore, SweepBuilder

ProbeFn = Callable[[], list[ProbeEvidence]]


class StateFile:
    """MC-38: durable, atomically-replaced resume state (sequence only — never
    capability claims; a restart always re-probes)."""

    def __init__(self, path: str):
        self.path = path

    def load(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as h:
                d = json.loads(h.read(65536))
            return {"sequence": int(d["sequence"]), "boot_id": str(d["boot_id"])}
        except (OSError, ValueError, KeyError, TypeError):
            return {"sequence": 0, "boot_id": ""}

    def save(self, sequence: int, boot_id: str) -> None:
        d = os.path.dirname(os.path.abspath(self.path))
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".gap02state")
        with os.fdopen(fd, "w", encoding="utf-8") as h:
            json.dump({"sequence": sequence, "boot_id": boot_id}, h)
            h.flush()
            os.fsync(h.fileno())
        os.replace(tmp, self.path)


class ProbeExecutor:
    def __init__(self, node: str, probes: dict[str, tuple[ProbeFn, tuple[str, ...]]], *,
                 store: SnapshotStore | None = None, max_concurrency: int = 4,
                 probe_timeout: float = 3.0, sweep_deadline: float = 20.0,
                 clock: Callable[[], int] = lambda: int(time.time()),
                 state: StateFile | None = None, boot_id: str = "",
                 quarantine: QuarantineRegistry | None = None,
                 on_event: Callable[[str, dict], None] = lambda k, d: None):
        self.node, self.probes = node, probes
        self.store = store or SnapshotStore()
        self.pool = ThreadPoolExecutor(max_workers=max_concurrency, thread_name_prefix="gap02-probe")
        self.probe_timeout, self.sweep_deadline = probe_timeout, sweep_deadline
        self.clock, self.state, self.boot_id = clock, state, boot_id
        self.quarantine = quarantine or QuarantineRegistry()
        self.breakers = {name: CircuitBreaker(name) for name in probes}
        self.on_event = on_event
        st = state.load() if state else {"sequence": 0, "boot_id": ""}
        # resume: keep sequence monotonic within the same boot; new boot restarts epoch space
        self.sequence = st["sequence"] if st["boot_id"] == boot_id else 0
        self._hot: set[str] = set()
        self._stop = threading.Event()
        self._lock = threading.Lock()

    def declared(self) -> tuple[str, ...]:
        return tuple(c for _, caps in self.probes.values() for c in caps)

    def notify_hotplug(self, probe_names: Iterable[str]) -> None:
        with self._lock:
            self._hot.update(n for n in probe_names if n in self.probes)

    def sweep(self):
        now = self.clock()
        self.sequence += 1
        b = SweepBuilder(self.node, self.declared(), now, self.sequence)
        futs = {}
        for name, (fn, caps) in self.probes.items():
            if self.quarantine.is_quarantined(name):
                for c in caps:
                    b.add(unknown(c, Code.QUARANTINED, name))
                continue
            br = self.breakers[name]
            if not br.allow(time.monotonic()):
                for c in caps:
                    b.add(unknown(c, Code.CIRCUIT_OPEN, name))
                continue
            started: dict = {}

            def job(fn=fn, started=started):
                started["t"] = time.monotonic()
                return fn()
            futs[self.pool.submit(job)] = (name, caps, started)
        end = time.monotonic() + self.sweep_deadline
        pending = set(futs)
        while pending:
            left = end - time.monotonic()
            if left <= 0:
                break
            done, pending = wait(pending, timeout=min(left, self.probe_timeout), return_when=FIRST_COMPLETED)
            for f in done:
                name, caps, started = futs[f]
                took = time.monotonic() - started.get("t", time.monotonic())
                try:
                    evs = f.result()
                    ok = took <= self.probe_timeout
                    if not ok:
                        evs = [unknown(c, Code.TIMEOUT, name, f"late {took:.2f}s") for c in caps]
                except Exception as e:  # noqa: BLE001
                    ok, evs = False, [unknown(c, Code.INTERNAL, name, type(e).__name__) for c in caps]
                self.breakers[name].record(ok and all(e.error is None for e in evs), time.monotonic())
                for ev in evs:
                    b.add(ev)
                self.on_event("probe.completed", {"probe": name, "ok": ok, "latency_s": round(took, 4)})
            for f in list(pending):
                name, caps, started = futs[f]
                if "t" in started and time.monotonic() - started["t"] > self.probe_timeout:
                    pending.discard(f)
                    f.cancel()
                    self.breakers[name].record(False, time.monotonic())
                    for c in caps:
                        b.add(unknown(c, Code.TIMEOUT, name, "deadline exceeded; abandoned"))
                    self.on_event("probe.timeout", {"probe": name})
        for f in pending:  # sweep deadline hit
            name, caps, _ = futs[f]
            for c in caps:
                if c not in b.report.results:
                    b.add(unknown(c, Code.TIMEOUT, name, "sweep deadline"))
        snap = b.seal()
        self.store.publish(snap)
        if self.state:
            self.state.save(self.sequence, self.boot_id)
        self.on_event("sweep.published", {"generation": snap.generation, "sequence": snap.sequence})
        return snap

    def run(self, interval: float, *, max_sweeps: int | None = None) -> None:
        n = 0
        while not self._stop.is_set():
            self.sweep()
            n += 1
            if max_sweeps is not None and n >= max_sweeps:
                break
            deadline = time.monotonic() + interval
            while time.monotonic() < deadline and not self._stop.is_set():
                with self._lock:
                    if self._hot:
                        self._hot.clear()
                        break
                self._stop.wait(0.05)

    def stop(self) -> None:
        self._stop.set()
        self.pool.shutdown(wait=False, cancel_futures=True)
