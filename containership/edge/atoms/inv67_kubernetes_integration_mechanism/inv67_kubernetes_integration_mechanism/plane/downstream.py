"""Downstream scheduler/runtime adapter (item 14).

Wire envelope ``PK_K8S_PLACE/1`` carries: the translated request, the
application identity, an idempotency key (attempt id), the fencing token, and
a deadline. ``RuntimeAdapter`` is the protocol SCH-01/INV-68 must satisfy.
``InMemoryRuntime`` is the reference downstream used by tests: idempotent
``place``, ``cancel`` and ``observe``, fencing enforcement and outage
injection. A real SCH-01 endpoint is not in this archive.
"""
from __future__ import annotations

import threading
from typing import Protocol

from .leader import FenceGuard
from .lifecycle import PlaneError, State

PLACE_SCHEMA = "PK_K8S_PLACE/1"


def envelope(request: dict, identity: dict, idem_key: str, fence: int, deadline_s: float = 30.0) -> dict:
    return {"schema": PLACE_SCHEMA, "idempotencyKey": idem_key, "fencingToken": fence,
            "deadlineSeconds": deadline_s, "identity": identity, "request": request}


class RuntimeAdapter(Protocol):
    def place(self, env: dict) -> str: ...
    def cancel(self, app_id: str, fence: int) -> None: ...
    def observe(self, app_id: str) -> dict: ...


class InMemoryRuntime:
    def __init__(self):
        self._lock = threading.Lock()
        self.fence = FenceGuard()
        self.placements: dict[str, dict] = {}      # app_id -> record
        self.by_key: dict[str, str] = {}
        self.launches = 0
        self.down = False
        self.fail_next_place = 0

    def _gate(self):
        if self.down:
            raise PlaneError("INV67_DOWNSTREAM_UNAVAILABLE", "runtime unreachable")

    def place(self, env: dict) -> str:
        with self._lock:
            self._gate()
            if env.get("schema") != PLACE_SCHEMA:
                raise PlaneError("INV67_INCOMPATIBLE", "unknown placement schema")
            if not self.fence.admit(env["fencingToken"]):
                raise PlaneError("INV67_NOT_LEADER", "stale fencing token")
            if self.fail_next_place:
                self.fail_next_place -= 1
                raise PlaneError("INV67_DOWNSTREAM_UNAVAILABLE", "injected placement failure")
            key = env["idempotencyKey"]
            if key in self.by_key:
                return self.by_key[key]
            app = env["identity"]["appId"]
            cur = self.placements.get(app)
            if cur and cur["state"] not in (State.CANCELLED.value, State.FAILED.value, State.SUCCEEDED.value):
                # A new generation replaces the old placement.
                cur["state"] = State.CANCELLED.value
            self.placements[app] = {"key": key, "state": State.PLACED.value,
                                    "units": {u["name"]: State.PLACED.value for u in env["request"]["units"]}}
            self.by_key[key] = app
            self.launches += 1
            return app

    def cancel(self, app_id: str, fence: int) -> None:
        with self._lock:
            self._gate()
            if not self.fence.admit(fence):
                raise PlaneError("INV67_NOT_LEADER", "stale fencing token")
            rec = self.placements.get(app_id)
            if rec:
                rec["state"] = State.CANCELLED.value
                rec["units"] = {k: State.CANCELLED.value for k in rec["units"]}

    def observe(self, app_id: str) -> dict:
        with self._lock:
            self._gate()
            rec = self.placements.get(app_id)
            if rec is None:
                return {"found": False}
            return {"found": True, "key": rec["key"], "state": rec["state"], "units": dict(rec["units"])}

    # test driver: simulate the runtime progressing
    def advance(self, app_id: str, unit_state: State, unit: str | None = None):
        with self._lock:
            rec = self.placements[app_id]
            for k in rec["units"]:
                if unit is None or k == unit:
                    rec["units"][k] = unit_state.value
            from .lifecycle import aggregate_units
            rec["state"] = aggregate_units([State(s) for s in rec["units"].values()]).value
