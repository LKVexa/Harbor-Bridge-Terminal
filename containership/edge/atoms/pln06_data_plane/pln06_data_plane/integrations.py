"""#14 #54-#58 adjacent-layer integration SPIs and reference fixtures.

Each adjacent system is reached through a small versioned protocol.  The
``Reference*`` classes are executable in-repo fixtures used by the integration
suite; they are **not** the real GAP-13/GAP-14/PLN-03 services.  Binding to
the real services is tracked as waivers W-005..W-007 in ``WAIVERS.json``.
"""
from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Protocol

from .data_plane import _StructuredError
from .security import KeyRing, canonical

GAP13_PROTOCOL = "PK_GAP13_POLICY/1"
GAP14_PROTOCOL = "PK_GAP14_GRAVITY/1"
PLN03_PROTOCOL = "PK_PLN03_HANDOFF/1"


class PolicyUnavailable(_StructuredError, RuntimeError):
    code = "PK_POLICY_UNAVAILABLE"
    retryable = True


class PolicyInvalid(_StructuredError, PermissionError):
    code = "PK_POLICY_INVALID"


class HandoffFailed(_StructuredError, RuntimeError):
    code = "PK_RUNTIME_HANDOFF_FAILED"
    retryable = True


class PolicySource(Protocol):
    def fetch(self) -> Mapping[str, object]: ...


class GravitySource(Protocol):
    def hint(self, tenant: str, workload: str, destination: str) -> Mapping[str, object]: ...


class DistributedRuntime(Protocol):
    def handoff(self, decision: Mapping[str, object], receipt: Mapping[str, object]) -> Mapping[str, object]: ...


# ------------------------------------------------------------------ GAP-13
class ReferencePolicyService:
    """Signs residency documents like a GAP-13 policy engine would."""

    def __init__(self, keyring: KeyRing, residency: Mapping[str, list[str]], revision: str = "r1", serial: int = 1,
                 clock: Callable[[], float] = time.time):
        self._keys = keyring
        self.residency = {k: list(v) for k, v in residency.items()}
        self.revision = revision
        self.serial = serial
        self.down = False
        self._clock = clock

    def fetch(self) -> Mapping[str, object]:
        if self.down:
            raise PolicyUnavailable("GAP-13 unreachable")
        body = {"protocol": GAP13_PROTOCOL, "revision": self.revision, "serial": self.serial, "issued": self._clock(),
                "residency": self.residency}
        kid, mac = self._keys.sign(canonical(body))
        return {"body": body, "kid": kid, "mac": mac}


class PolicyClient:
    """Fetches, authenticates and version-checks authoritative policy; serves last verified copy
    only while younger than ``max_age`` (degraded mode), then fails closed."""

    def __init__(self, source: PolicySource, keyring: KeyRing, *, max_age: float = 300.0,
                 clock: Callable[[], float] = time.time):
        self._src = source
        self._keys = keyring
        self._max_age = max_age
        self._clock = clock
        self.current: dict[str, object] | None = None
        self.fetched_at = 0.0
        self.degraded = False

    def refresh(self) -> dict[str, object]:
        try:
            doc = self._src.fetch()
        except PolicyUnavailable:
            self.degraded = True
            return self.get()
        body = dict(doc["body"])  # type: ignore[arg-type, call-overload]
        if not self._keys.verify(str(doc["kid"]), canonical(body), str(doc["mac"])):
            raise PolicyInvalid("policy signature invalid")
        if body.get("protocol") != GAP13_PROTOCOL:
            raise PolicyInvalid("unsupported policy protocol", protocol=body.get("protocol"))
        if self.current is not None and int(body["serial"]) < int(self.current["serial"]):  # type: ignore[call-overload]
            raise PolicyInvalid("policy rollback/downgrade refused", offered=body["serial"],
                                current=self.current["serial"])
        self.current, self.fetched_at, self.degraded = body, self._clock(), False
        return body

    def get(self) -> dict[str, object]:
        if self.current is None:
            raise PolicyUnavailable("no verified policy available")
        if self._clock() - self.fetched_at > self._max_age:
            raise PolicyUnavailable("verified policy too old; failing closed",
                                    age=self._clock() - self.fetched_at, max_age=self._max_age)
        return self.current


# ------------------------------------------------------------------ GAP-14
class ReferenceGravityService:
    def __init__(self, keyring: KeyRing, hints: Mapping[tuple[str, str], str]):
        self._keys = keyring
        self._hints = dict(hints)

    def hint(self, tenant: str, workload: str, destination: str) -> Mapping[str, object]:
        body = {"protocol": GAP14_PROTOCOL, "tenant": tenant, "workload": workload, "destination": destination,
                "locality": self._hints.get((tenant, destination), "auto")}
        kid, mac = self._keys.sign(canonical(body))
        return {"body": body, "kid": kid, "mac": mac}


def verified_locality(doc: Mapping[str, object], keyring: KeyRing, *, tenant: str, destination: str) -> str:
    """Return the hinted locality only if authentic and bound to this request; else ``auto``.

    Gravity is advisory: it can only change locality (which can only *promote*
    a tier), never destination or residency.
    """
    try:
        body = dict(doc["body"])  # type: ignore[arg-type, call-overload]
        if not keyring.verify(str(doc["kid"]), canonical(body), str(doc["mac"])):
            return "auto"
    except Exception:  # noqa: BLE001 - untrusted hint must never break admission
        return "auto"
    if body.get("tenant") != tenant or body.get("destination") != destination:
        return "auto"
    return str(body.get("locality", "auto"))


# ------------------------------------------------------------------ PLN-03
class ReferenceRuntime:
    """Records hand-offs like PLN-03 would; can be told to fail."""

    def __init__(self) -> None:
        self.accepted: list[dict[str, object]] = []
        self.fail_next = 0

    def handoff(self, decision: Mapping[str, object], receipt: Mapping[str, object]) -> Mapping[str, object]:
        if self.fail_next:
            self.fail_next -= 1
            raise HandoffFailed("PLN-03 rejected hand-off")
        rec = {"protocol": PLN03_PROTOCOL, "transfer_id": decision.get("transfer_id"),
               "root": receipt.get("manifest_root"), "adapter": receipt.get("adapter")}
        self.accepted.append(rec)
        return {"ok": True, **rec}
