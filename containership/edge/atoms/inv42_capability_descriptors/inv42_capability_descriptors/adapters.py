"""MC-005 - adjacent-layer adapters (contract-level; real sibling layers bind here).

* :class:`InProcessCapabilitySource` - INV-41 upstream.  Accepts an in-process
  capability reference that declares its ``capability_type`` and turns it into
  an authenticated descriptor.  Only objects satisfying the protocol pass.
* :class:`SystemInterfaceBoundary` - INV-13 downstream.  Byte-level ABI edge:
  bounded UTF-8 JSON in, typed result dict out; never raises across the ABI and
  never echoes bearer material in errors.
"""
from __future__ import annotations

import json
from typing import Protocol, runtime_checkable

try:
    from . import descriptors as _d
    from .outcomes import classify
except ImportError:
    import descriptors as _d  # type: ignore
    from outcomes import classify  # type: ignore

MAX_ABI_BYTES = 1024


@runtime_checkable
class Capability(Protocol):
    capability_type: str


class InProcessCapabilitySource:
    def __init__(self, table):
        self.table = table

    def export(self, capability) -> dict:
        if not isinstance(capability, Capability):
            raise TypeError("INV-41 capability must declare capability_type")
        return self.table.open(capability.capability_type, capability).to_wire()


class SystemInterfaceBoundary:
    def __init__(self, table):
        self.table = table

    def call(self, op: str, payload: bytes, *, expect: str | None = None) -> dict:
        try:
            if not isinstance(payload, (bytes, bytearray)) or len(payload) > MAX_ABI_BYTES:
                raise _d.InvalidDescriptor("ABI payload must be bytes <= %d" % MAX_ABI_BYTES)
            try:
                wire = json.loads(bytes(payload).decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                raise _d.InvalidDescriptor("ABI payload is not UTF-8 JSON") from None
            fd = self.table.from_wire(wire)
            if op == "resolve":
                self.table.resolve(fd, expect=expect)
                return {"ok": True, "number": fd.number, "type": fd.resource_type}
            if op == "close":
                self.table.close(fd)
                return {"ok": True, "number": fd.number, "closed": True}
            raise _d.InvalidDescriptor("unknown ABI operation")
        except Exception as exc:  # noqa: BLE001 - ABI boundary must not leak exceptions
            o = classify(exc)
            return {"ok": False, "code": o.code, "class": o.klass}
