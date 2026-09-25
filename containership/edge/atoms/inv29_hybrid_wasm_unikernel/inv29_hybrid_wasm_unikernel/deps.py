"""Dependency boundary for INV-29 (MC001..MC006, MC067, MC068, MC082).

INV-29 consumes five external elements.  Each is reached only through a narrow
``Adapter`` that exposes exactly the capability INV-29 needs, reports a stable
dependency state, and is wrapped in timeout / bounded retry / circuit-breaker
logic.  Any state other than ``AVAILABLE`` is a refusal on the admission path.

The ``*TestDouble`` classes are deterministic fixtures for unit, contract and
chaos testing.  They are **not** the real dependencies and are never counted as
certification evidence for MC001..MC006; the gate marks those BLOCKED_EXTERNAL
until a real integration run is retained.
"""
from __future__ import annotations

import concurrent.futures as _cf
import importlib
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional

AVAILABLE = "AVAILABLE"
ABSENT = "ABSENT"
INCOMPATIBLE = "INCOMPATIBLE"
DEGRADED = "DEGRADED"
UNAVAILABLE = "UNAVAILABLE"  # temporarily: timeout, open circuit, transient error
STATES = (AVAILABLE, ABSENT, INCOMPATIBLE, DEGRADED, UNAVAILABLE)

#: machine-readable dependency manifest (also emitted as dependencies.lock.json)
DEPENDENCIES = {
    "pk_core": {"kind": "runtime", "required": True, "api": "pk_core.contract/1",
                "min_version": "4.0.0", "max_major": 4, "priority": "P0"},
    "INV-11": {"kind": "element", "required": True, "api": "check_link/classify", "priority": "P0"},
    "INV-27": {"kind": "element", "required": True, "api": "sealed-image attestation", "priority": "P0"},
    "INV-44": {"kind": "element", "required": True, "api": "hardened-module attestation", "priority": "P0"},
    "PLN-04": {"kind": "element", "required": True, "api": "admission callback", "priority": "P0"},
    "INV-30": {"kind": "element", "required": False, "api": "hardware capability layer", "priority": "P2"},
}


class DependencyUnavailable(PermissionError):
    code = "INV29-E-DEPENDENCY"

    def __init__(self, name: str, state: str, detail: str = ""):
        self.dependency, self.state = name, state
        super().__init__(f"{self.code}: {name} is {state}{': ' + detail if detail else ''}")


@dataclass
class Health:
    name: str
    state: str
    version: Optional[str] = None
    detail: str = ""
    latency_ms: float = 0.0

    def as_dict(self) -> dict:
        return {"name": self.name, "state": self.state, "version": self.version,
                "detail": self.detail[:256], "latency_ms": round(self.latency_ms, 3)}


class CircuitBreaker:
    """Closed -> open after ``threshold`` consecutive failures; half-open after ``cooldown``."""

    def __init__(self, threshold: int = 3, cooldown_s: float = 30.0, clock: Callable[[], float] = time.monotonic):
        self.threshold, self.cooldown_s, self.clock = threshold, cooldown_s, clock
        self._fails = 0
        self._opened_at: Optional[float] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._opened_at is None:
                return "closed"
            return "half-open" if self.clock() - self._opened_at >= self.cooldown_s else "open"

    def allow(self) -> bool:
        return self.state != "open"

    def success(self) -> None:
        with self._lock:
            self._fails, self._opened_at = 0, None

    def failure(self) -> None:
        with self._lock:
            self._fails += 1
            if self._fails >= self.threshold:
                self._opened_at = self.clock()


_POOL = _cf.ThreadPoolExecutor(max_workers=8, thread_name_prefix="inv29-dep")


class Adapter:
    """Wraps one dependency call with timeout, bounded retry and a circuit breaker."""

    name = "abstract"

    def __init__(self, *, timeout_s: float = 2.0, retries: int = 1, breaker: Optional[CircuitBreaker] = None):
        self.timeout_s, self.retries = timeout_s, retries
        self.breaker = breaker or CircuitBreaker()

    def probe(self) -> Health:  # pragma: no cover - overridden
        return Health(self.name, ABSENT)

    def call(self, fn: Callable, *args, **kwargs):
        if not self.breaker.allow():
            raise DependencyUnavailable(self.name, UNAVAILABLE, "circuit open")
        last: Optional[BaseException] = None
        for _ in range(self.retries + 1):
            fut = _POOL.submit(fn, *args, **kwargs)
            try:
                result = fut.result(timeout=self.timeout_s)
            except _cf.TimeoutError:
                fut.cancel()
                last = TimeoutError(f"{self.name} timed out after {self.timeout_s}s")
                self.breaker.failure()
                continue
            except PermissionError:
                # a *decision* from the dependency (refusal) is not a transport failure; never retried
                self.breaker.success()
                raise
            except Exception as exc:  # malformed response, crash, connection loss
                last = exc
                self.breaker.failure()
                continue
            self.breaker.success()
            return result
        raise DependencyUnavailable(self.name, UNAVAILABLE, f"{type(last).__name__}: {last}")


# ------------------------------------------------------------------ pk_core


def _vtuple(v: str) -> tuple:
    return tuple(int(x) for x in v.split(".")[:3])


def pk_core_status() -> Health:
    """Startup compatibility assertion for pk_core (MC001).  Never raises."""
    t0 = time.perf_counter()
    try:
        mod = importlib.import_module("pk_core")
    except ModuleNotFoundError:
        return Health("pk_core", ABSENT, None, "pk_core not importable", (time.perf_counter() - t0) * 1e3)
    except Exception as exc:  # corrupt install
        return Health("pk_core", INCOMPATIBLE, None, f"import failed: {type(exc).__name__}")
    version = getattr(mod, "__version__", None)
    spec = DEPENDENCIES["pk_core"]
    try:
        vt = _vtuple(str(version))
    except Exception:
        return Health("pk_core", INCOMPATIBLE, str(version), "unparseable version")
    if vt < _vtuple(spec["min_version"]) or vt[0] > spec["max_major"]:
        return Health("pk_core", INCOMPATIBLE, str(version),
                      f"requires >= {spec['min_version']} and major <= {spec['max_major']}")
    for sub in ("contract", "checklist", "component", "integration"):
        try:
            importlib.import_module(f"pk_core.{sub}")
        except Exception:
            return Health("pk_core", INCOMPATIBLE, str(version), f"pk_core.{sub} missing")
    return Health("pk_core", AVAILABLE, str(version), "", (time.perf_counter() - t0) * 1e3)


def require_pk_core() -> None:
    h = pk_core_status()
    if h.state != AVAILABLE:
        raise DependencyUnavailable("pk_core", h.state, h.detail)


# ------------------------------------------------------------------ test doubles


class AttestorTestDouble(Adapter):
    """Deterministic stand-in for INV-27 (sealed image) or INV-44 (hardened module).

    ``mode`` injects faults: ok | timeout | malformed | crash | revoked | absent.
    """

    def __init__(self, name: str, claim: str, keyring, key_id: str, *, mode: str = "ok",
                 clock: Callable[[], float] = time.time, **kw):
        super().__init__(**kw)
        self.name, self.claim, self.keyring, self.key_id, self.mode, self.clock = name, claim, keyring, key_id, mode, clock

    def probe(self) -> Health:
        if self.mode == "absent":
            return Health(self.name, ABSENT)
        if not self.breaker.allow():
            return Health(self.name, UNAVAILABLE, detail="circuit open")
        return Health(self.name, DEGRADED if self.mode != "ok" else AVAILABLE, "test-double")

    def _attest(self, subject: str) -> dict:
        from .admission import issue_attestation
        if self.mode == "timeout":
            time.sleep(self.timeout_s * 3)
        if self.mode == "crash":
            raise ConnectionError("dependency connection lost")
        if self.mode == "malformed":
            return {"claim": self.claim}
        if self.mode == "absent":
            raise ModuleNotFoundError(self.name)
        att = issue_attestation(self.keyring, self.key_id, self.claim, subject, now=int(self.clock()))
        if self.mode == "revoked":
            self.keyring.revoke(self.key_id)
        return att

    def attest(self, subject: str) -> dict:
        return self.call(self._attest, subject)


class ExecutionPlaneTestDouble:
    """Stand-in for PLN-04: records admitted compositions, rejects unsigned ones."""

    name = "PLN-04"

    def __init__(self, keyring, signing_key_id: str):
        self.keyring, self.signing_key_id = keyring, signing_key_id
        self.admitted, self._lock = [], threading.Lock()

    def submit(self, record: dict) -> str:
        from .admission import verify_record
        verify_record(self.keyring, record, expected_key_id=self.signing_key_id)
        with self._lock:
            self.admitted.append(record["admission"]["nonce"])
        return "scheduled"


def dependency_report(extra: Optional[Dict[str, Adapter]] = None) -> dict:
    """Aggregate dependency status (the /dependencies endpoint body)."""
    out = {"pk_core": pk_core_status().as_dict()}
    for name in ("INV-11", "INV-27", "INV-44", "PLN-04", "INV-30"):
        adapter = (extra or {}).get(name)
        if adapter is not None:
            out[name] = adapter.probe().as_dict()
        else:
            try:
                from pk_core.integration import resolve  # type: ignore
                mod = resolve(name)
            except Exception:
                mod = None
            out[name] = Health(name, AVAILABLE if mod else ABSENT).as_dict()
    required_ok = all(out[n]["state"] == AVAILABLE for n, s in DEPENDENCIES.items() if s["required"])
    return {"dependencies": out, "all_required_available": required_ok}
