"""Shared probe-evidence model and the single promotion gate.

Every production probe returns ``ProbeEvidence``. Only ``promote()`` turns
evidence into a report state, and it returns ``present`` only when the
evidence carries capability-specific *proof* (kind in PROOF_KINDS). An
observation (device node exists, name match, driver loaded) is never proof.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
import subprocess
import time
from typing import Any, Callable, Mapping, Sequence

from ..capabilities import ABSENT, PRESENT, UNPROBED
from .errors import Code, Gap02Error

#: evidence kinds that may promote to present
PROOF_KINDS = frozenset({"runtime-call", "kernel-attribute", "api-bit", "attested"})
#: evidence kinds that can never promote to present
OBSERVATION_KINDS = frozenset({"observation", "name-match", "driver-presence", "heuristic", "cache"})

MAX_OUTPUT = 1_000_000


@dataclass
class ProbeEvidence:
    capability: str
    result: bool | None            # True proven, False proven-absent, None unknown
    kind: str                      # PROOF_KINDS or OBSERVATION_KINDS
    source: str                    # authoritative source identifier
    facts: dict[str, Any] = field(default_factory=dict)
    error: str | None = None       # Code value when result is None
    latency_ms: float = 0.0

    def __post_init__(self) -> None:
        if self.kind not in PROOF_KINDS | OBSERVATION_KINDS:
            raise ValueError(f"unknown evidence kind {self.kind!r}")
        if self.result is not None and not isinstance(self.result, bool):
            raise ValueError("result must be bool or None")

    def to_dict(self) -> dict[str, Any]:
        return {"capability": self.capability, "result": self.result, "kind": self.kind,
                "source": self.source, "facts": self.facts, "error": self.error,
                "latency_ms": round(self.latency_ms, 3)}


def promote(ev: ProbeEvidence) -> str:
    """The only evidence→state mapping. Fail closed."""
    if ev.result is True and ev.kind in PROOF_KINDS and ev.error is None:
        return PRESENT
    if ev.result is False and ev.kind in PROOF_KINDS and ev.error is None:
        return ABSENT
    return UNPROBED


def unknown(capability: str, code: Code, source: str, detail: str = "", **facts: Any) -> ProbeEvidence:
    f = dict(facts)
    if detail:
        f["detail"] = detail[:256]
    return ProbeEvidence(capability, None, "observation", source, f, error=code.value)


# ---------------------------------------------------------------- host access
class Host:
    """Injectable host-access seam. Production reads the real OS; fixtures
    (tests, the fixture lab) substitute files/commands. All access is bounded."""

    def __init__(self, files: Mapping[str, str] | None = None,
                 commands: Mapping[tuple[str, ...], tuple[int, str]] | None = None,
                 system: str | None = None, machine: str | None = None,
                 denied: Sequence[str] = (), timeout_paths: Sequence[str] = ()):
        self._files = dict(files) if files is not None else None
        self._commands = dict(commands) if commands is not None else None
        self._denied = set(denied)
        self._timeouts = set(timeout_paths)
        import platform
        self.system = system or platform.system()
        self.machine = (machine or platform.machine() or "").lower()

    @property
    def is_fixture(self) -> bool:
        return self._files is not None

    def read(self, path: str, limit: int = 131_072) -> str | None:
        if path in self._denied:
            raise Gap02Error(Code.PRIVILEGE_DENIED, path)
        if self._files is not None:
            v = self._files.get(path)
            return None if v is None else v[:limit]
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as h:
                return h.read(limit)
        except PermissionError as e:
            raise Gap02Error(Code.PRIVILEGE_DENIED, path) from e
        except OSError:
            return None

    def exists(self, path: str) -> bool:
        if self._files is not None:
            return path in self._files or any(k.startswith(path.rstrip("/") + "/") for k in self._files)
        return os.path.exists(path)

    def listdir(self, path: str) -> list[str]:
        if self._files is not None:
            pre = path.rstrip("/") + "/"
            return sorted({k[len(pre):].split("/", 1)[0] for k in self._files if k.startswith(pre)})
        try:
            return sorted(os.listdir(path))[:4096]
        except OSError:
            return []

    def access(self, path: str, mode: int) -> bool:
        if path in self._denied:
            return False
        if self._files is not None:
            return path in self._files
        return os.access(path, mode)

    def run(self, argv: Sequence[str], timeout: float = 2.0) -> tuple[int, str]:
        """Fixed absolute-path command, no shell, bounded output and time."""
        argv = tuple(argv)
        if not argv or not os.path.isabs(argv[0]):
            raise Gap02Error(Code.CONFIG_INVALID, "command must be absolute path")
        if argv[0] in self._timeouts:
            raise Gap02Error(Code.TIMEOUT, argv[0])
        if self._commands is not None:
            if argv not in self._commands:
                raise Gap02Error(Code.PROBE_UNAVAILABLE, argv[0])
            rc, out = self._commands[argv]
            return rc, out[:MAX_OUTPUT]
        if not os.path.isfile(argv[0]):
            raise Gap02Error(Code.PROBE_UNAVAILABLE, argv[0])
        try:
            cp = subprocess.run(list(argv), capture_output=True, text=True, timeout=timeout,
                                shell=False, stdin=subprocess.DEVNULL, check=False)
        except subprocess.TimeoutExpired as e:
            raise Gap02Error(Code.TIMEOUT, argv[0]) from e
        except OSError as e:
            raise Gap02Error(Code.DRIVER_ERROR, f"{argv[0]}: {type(e).__name__}") from e
        return cp.returncode, (cp.stdout or "")[:MAX_OUTPUT]


def timed(fn: Callable[[], ProbeEvidence], capability: str, source: str) -> ProbeEvidence:
    """Run a probe body; map every exception to a coded, unprobed evidence."""
    t0 = time.perf_counter()
    try:
        ev = fn()
    except Gap02Error as e:
        ev = unknown(capability, e.code, source, e.detail)
    except Exception as e:  # noqa: BLE001 — fail closed, stay observable
        from .errors import classify
        ev = unknown(capability, classify(e), source, f"{type(e).__name__}: {e}")
    ev.latency_ms = (time.perf_counter() - t0) * 1000
    return ev
