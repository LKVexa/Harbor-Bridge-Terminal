# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Enforcement backends (GAP-004).

``SemanticModelBackend`` is the dependency-free Python model. It is labelled
``enforcement="semantic-model"`` and is *refused* whenever a caller requires
hardware enforcement. ``CheriHardwareBackend`` is the adapter contract for a
real CHERI backend (CheriBSD/Morello or CHERI-RISC-V via a native helper). It
only reports ``available`` when discovery returns ``present`` *and* a native
helper is configured; otherwise it fails closed with BACKEND_UNAVAILABLE.
No code path here emulates hardware and calls it hardware.
"""
from __future__ import annotations

import os
import shutil
from typing import Iterable, Protocol

from .core import Capability
from .discovery import PRESENT, probe_cheri
from .errors import BackendUnavailable, HardwareRequired

MODEL, HARDWARE = "semantic-model", "cheri-hardware"


class Backend(Protocol):
    name: str
    enforcement: str

    def available(self) -> dict: ...
    def mint(self, base: int, length: int, permissions: Iterable[str]) -> Capability: ...


class SemanticModelBackend:
    name = "python-semantic-model"
    enforcement = MODEL

    def available(self) -> dict:
        return {"backend": self.name, "enforcement": self.enforcement, "available": True,
                "reason": "pure-Python semantic model (NOT hardware enforcement)"}

    def mint(self, base, length, permissions):
        return Capability(base, length, frozenset(permissions))


class CheriHardwareBackend:
    """Adapter to a native CHERI helper (``INV30_CHERI_HELPER`` → executable path).

    The helper protocol (docs/CHERI_BACKEND.md) is: JSON request on stdin, JSON
    response on stdout, compiled pure-capability with CHERI Clang. It is not
    bundled: building it needs a CHERI toolchain and CHERI hardware/emulator.
    """

    name = "cheri-native-helper"
    enforcement = HARDWARE

    def __init__(self, helper: str | None = None, probe=probe_cheri):
        self.helper = helper if helper is not None else os.environ.get("INV30_CHERI_HELPER", "")
        self._probe = probe

    def available(self) -> dict:
        hw = self._probe()
        helper_ok = bool(self.helper) and shutil.which(self.helper) is not None or (
            bool(self.helper) and os.path.isfile(self.helper) and os.access(self.helper, os.X_OK))
        ok = hw["state"] == PRESENT and helper_ok
        reason = "ok" if ok else (
            f"hardware {hw['state']} ({hw['signal']})" if hw["state"] != PRESENT else "native helper not configured")
        return {"backend": self.name, "enforcement": self.enforcement, "available": ok, "reason": reason}

    def mint(self, base, length, permissions):
        st = self.available()
        if not st["available"]:
            raise BackendUnavailable(f"CHERI backend unavailable: {st['reason']}")
        # A native mint would return a sealed handle to a real tagged capability.
        raise BackendUnavailable("CHERI native helper protocol not implemented in this build")


def available_backends() -> list[dict]:
    return [SemanticModelBackend().available(), CheriHardwareBackend().available()]


def select_backend(*, require_hardware: bool, mode: str, hardware: CheriHardwareBackend | None = None):
    """Pick a backend, failing closed. Production + require_hardware never yields the model."""
    if mode not in ("development", "staging", "production"):
        raise ValueError(f"unknown mode {mode!r}")
    hw = hardware or CheriHardwareBackend()
    st = hw.available()
    if st["available"]:
        return hw
    if require_hardware:
        raise HardwareRequired(f"hardware capability enforcement required but unavailable: {st['reason']}")
    if mode == "production":
        # Production may run the model only for workloads that did not ask for this tier,
        # and every record it emits carries enforcement="semantic-model".
        return SemanticModelBackend()
    return SemanticModelBackend()
