"""INV-23 primitive state model (pure stdlib; no pk_core dependency).

This is the process-local state machine.  Host evidence comes from
``probe.probe_host()`` (MC-03) and cross-process ownership from
``claim.ClaimManager`` (MC-04/05); ``VirtPrimitive.from_probe`` bridges the two.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock

USABLE, PRESENT_DISABLED, ABSENT, CLAIMED = "usable", "present-disabled", "absent", "claimed"


class PrimitiveUnavailable(RuntimeError):
    """Raised when the virtualization primitive cannot be claimed for use."""


@dataclass
class VirtPrimitive:
    """The host CPU's virtualization extension, as probed rather than as advertised."""

    host: str
    cpuid_present: bool = False
    firmware_enabled: bool = False
    device_openable: bool = False
    nesting_depth: int = 0  # 0 = bare metal, 1 = we are a guest, ...
    holder: str | None = None
    _lock: RLock = field(default_factory=RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.host, str) or not self.host.strip():
            raise ValueError("host must be a non-empty string")
        self.host = self.host.strip()
        for name in ("cpuid_present", "firmware_enabled", "device_openable"):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be bool")
        if type(self.nesting_depth) is not int or self.nesting_depth < 0:
            raise ValueError(f"nesting_depth must be a non-negative int, got {self.nesting_depth!r}")
        if self.holder is not None:
            if not isinstance(self.holder, str) or not self.holder.strip():
                raise ValueError("holder must be None or a non-empty string")
            self.holder = self.holder.strip()

    def _state_unlocked(self) -> str:
        if not self.cpuid_present:
            return ABSENT
        if not self.firmware_enabled or not self.device_openable:
            return PRESENT_DISABLED
        if self.holder is not None:
            return CLAIMED
        return USABLE

    def state(self) -> str:
        """Return a coherent usability snapshot; CPUID alone is never proof."""
        with self._lock:
            return self._state_unlocked()

    def claim(self, holder: str, *, max_nesting: int = 1) -> dict:
        if not isinstance(holder, str) or not holder.strip():
            raise ValueError("holder must be a non-empty string")
        holder = holder.strip()
        if type(max_nesting) is not int or max_nesting < 0:
            raise ValueError(f"max_nesting must be a non-negative int, got {max_nesting!r}")
        with self._lock:
            state = self._state_unlocked()
            if state != USABLE:
                raise PrimitiveUnavailable(f"{self.host}: virtualization primitive is {state}")
            if self.nesting_depth > max_nesting:
                raise PrimitiveUnavailable(f"{self.host}: nesting depth {self.nesting_depth} exceeds the permitted {max_nesting}")
            self.holder = holder
            return {
                "schema": "PK_VIRT_CLAIM/1",
                "host": self.host,
                "holder": holder,
                "nesting_depth": self.nesting_depth,
                "bare_metal": self.nesting_depth == 0,
            }

    def release(self, holder: str | None = None) -> None:
        """Release a claim only when the active holder proves ownership.

        An unclaimed primitive is a no-op.  For a claimed primitive, omitting the
        holder is rejected so an unrelated caller cannot clear another VMM's claim.
        """
        with self._lock:
            if self.holder is None:
                return
            if not isinstance(holder, str) or not holder.strip():
                raise PrimitiveUnavailable(f"{self.host}: release requires the active holder identity")
            holder = holder.strip()
            if holder != self.holder:
                raise PrimitiveUnavailable(f"{self.host}: held by {self.holder!r}, cannot be released by {holder!r}")
            self.holder = None

    def report(self) -> dict:
        with self._lock:
            state = self._state_unlocked()
            return {
                "schema": "PK_VIRT_PRIMITIVE/1",
                "host": self.host,
                "state": state,
                "nesting_depth": self.nesting_depth,
                "bare_metal": self.nesting_depth == 0 and state in (USABLE, CLAIMED),
            }

    @classmethod
    def from_probe(cls, result) -> VirtPrimitive:
        """Build a model from a real ``ProbeResult``; never upgrades an unproven host.

        An indeterminate probe maps to ``present-disabled`` when CPU capability was seen,
        otherwise ``absent`` -- never to ``usable``.  Unknown nesting depth maps to 1
        (virtualized, depth unknown) so it can never read as bare metal.
        """
        depth = result.nesting_depth
        if depth is None:
            depth = 1 if result.virtualized is not False else 0
        return cls(
            result.host,
            cpuid_present=bool(result.cpu_capable),
            firmware_enabled=result.state == "usable" or bool(result.firmware_enabled),
            device_openable=result.state == "usable",
            nesting_depth=depth,
        )
