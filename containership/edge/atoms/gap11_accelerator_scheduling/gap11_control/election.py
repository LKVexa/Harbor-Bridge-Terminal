"""GAP11-P0-03 HA controller ownership / leader election, integrated with P0-02 fencing.

Leadership is a record in the durable store (``ctl/leader``) acquired by CAS.
Each successful acquisition increments ``epoch``; the epoch *is* the fencing token.
Every controller mutation is committed with ``fence=("controller", epoch)`` so the
store itself rejects a deposed leader's writes (``STALE_FENCE``), independent of
whether that leader has noticed it lost authority. Leadership expiry is measured on
the store's monotonic clock; controllers additionally stop mutating ``safety_margin``
seconds before their own view of expiry (clock-skew bound, see DESIGN_RECORDS).
"""
from __future__ import annotations

from typing import Any

from .common import ControlError, Telemetry
from .store import LeaseStore, Provenance

LEADER_KEY = "ctl/leader"
FENCE_RESOURCE = "controller"


class LeaderElector:
    def __init__(self, store: LeaseStore, controller_id: str, *, ttl: float = 10.0,
                 safety_margin: float = 2.0, telemetry: Telemetry | None = None) -> None:
        if not controller_id:
            raise ValueError("controller_id required")
        if safety_margin <= 0 or safety_margin >= ttl:
            raise ValueError("0 < safety_margin < ttl required")
        self.store = store
        self.id = controller_id
        self.ttl = ttl
        self.margin = safety_margin
        self.tel = telemetry or Telemetry(store.clock)
        self.epoch: int | None = None
        self._expires: float = 0.0

    def _record(self) -> tuple[int, dict[str, Any]] | None:
        return self.store.get(LEADER_KEY)

    def try_acquire(self) -> bool:
        now = self.store.clock.monotonic()
        cur = self._record()
        rev = 0 if cur is None else cur[0]
        if cur is not None:
            holder = cur[1]
            if holder["holder"] != self.id and holder["expires"] > now:
                return False
            new_epoch = holder["epoch"] + (0 if holder["holder"] == self.id and holder["expires"] > now else 1)
        else:
            new_epoch = 1
        record = {"holder": self.id, "epoch": new_epoch, "expires": now + self.ttl}
        try:
            self.store.commit([{"op": "put", "key": LEADER_KEY, "value": record}], pre={LEADER_KEY: rev},
                              prov=Provenance(f"elect-{self.id}-{new_epoch}-{now}", self.id, new_epoch, "LEADER_ACQUIRE"),
                              fence=(FENCE_RESOURCE, new_epoch))
        except ControlError as exc:
            self.tel.emit("election", "acquire", code=exc.code, severity="WARN", detail=self.id)
            return False
        changed = self.epoch != new_epoch
        self.epoch, self._expires = new_epoch, now + self.ttl
        if changed:
            self.tel.emit("election", "leader_change", controller_epoch=new_epoch, detail=self.id)
        return True

    renew = try_acquire

    def is_leader(self) -> bool:
        """Local view, conservative by ``safety_margin``; the store fence is the real guard."""
        return self.epoch is not None and self.store.clock.monotonic() < self._expires - self.margin

    def require(self) -> int:
        if not self.is_leader():
            raise ControlError("NOT_LEADER", controller=self.id)
        return self.epoch  # type: ignore[return-value]

    def step_down(self) -> None:
        cur = self._record()
        if cur and cur[1]["holder"] == self.id and self.epoch is not None:
            rec = dict(cur[1], expires=0.0)
            try:
                self.store.commit([{"op": "put", "key": LEADER_KEY, "value": rec}], pre={LEADER_KEY: cur[0]},
                                  prov=Provenance(f"stepdown-{self.id}-{self.epoch}", self.id, self.epoch, "LEADER_STEP_DOWN"),
                                  fence=(FENCE_RESOURCE, self.epoch))
            except ControlError:
                pass
        self.epoch = None
