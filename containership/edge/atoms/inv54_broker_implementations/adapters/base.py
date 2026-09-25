"""Provider-neutral adapter protocol (PK_BROKER_LOG/1 + PK_BROKER_FANOUT/1 subset)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from ..brokers import FanoutBroker, PartitionedLog
from ..errors import NOT_FOUND, UNSUPPORTED_FEATURE, BrokerError, classify

FEATURES = ("per_key_order", "replay", "independent_offsets", "fanout", "ack_redelivery", "dedup_window")


@dataclass
class Delivery:
    key: str | None
    value: Any
    position: str          # opaque provider position (offset, delivery tag, receipt handle)
    redelivered: bool = False


@runtime_checkable
class BrokerAdapter(Protocol):
    provider: str
    features: frozenset[str]

    def publish(self, dest: str, value: Any, *, key: str | None = None,
                dedup_id: str | None = None) -> str: ...
    def consume(self, dest: str, group: str, max_messages: int = 10) -> list[Delivery]: ...
    def ack(self, dest: str, group: str, delivery: Delivery) -> None: ...
    def seek(self, dest: str, group: str, position: str) -> None: ...
    def close(self) -> None: ...


def require(adapter: BrokerAdapter, feature: str) -> None:
    if feature not in adapter.features:
        raise BrokerError(UNSUPPORTED_FEATURE, feature=feature, provider=adapter.provider)


class ReferenceLogAdapter:
    """Adapter over the in-memory PartitionedLog; 'dest' = stream, positions = 'partition:offset'."""

    provider = "reference-log"
    features = frozenset({"per_key_order", "replay", "independent_offsets"})

    def __init__(self, partitions: int = 4) -> None:
        self._streams: dict[str, PartitionedLog] = {}
        self._parts = partitions
        self._cursor: dict[tuple[str, str], int] = {}

    def _log(self, dest: str) -> PartitionedLog:
        return self._streams.setdefault(dest, PartitionedLog(self._parts))

    def publish(self, dest, value, *, key=None, dedup_id=None):
        try:
            p, o = self._log(dest).append(key or "", value)
        except Exception as exc:
            raise classify(exc) from exc
        return f"{p}:{o}"

    def consume(self, dest, group, max_messages=10):
        log = self._log(dest)
        out: list[Delivery] = []
        for p in range(log.partitions):
            start = log.committed_offset(group, p)
            for i, (k, v) in enumerate(log.logs[p][start:start + max_messages - len(out)]):
                out.append(Delivery(k, v, f"{p}:{start + i}"))
            if len(out) >= max_messages:
                break
        return out

    def ack(self, dest, group, delivery):
        p, o = map(int, delivery.position.split(":"))
        log = self._log(dest)
        if o + 1 > log.committed_offset(group, p):
            log.seek(group, p, o + 1)

    def seek(self, dest, group, position):
        p, o = map(int, position.split(":"))
        try:
            self._log(dest).seek(group, p, o)
        except Exception as exc:
            raise classify(exc) from exc

    def close(self):
        pass


class ReferenceQueueAdapter:
    """Adapter over FanoutBroker semantics with ack/redelivery (queue-style providers)."""

    provider = "reference-queue"
    features = frozenset({"fanout", "ack_redelivery"})

    def __init__(self) -> None:
        self._b: dict[str, FanoutBroker] = {}
        self._inflight: dict[tuple[str, str], dict[str, Any]] = {}
        self._n = 0

    def _broker(self, dest):
        return self._b.setdefault(dest, FanoutBroker())

    def publish(self, dest, value, *, key=None, dedup_id=None):
        self._broker(dest).publish(value)
        self._n += 1
        return str(self._n)

    def consume(self, dest, group, max_messages=10):
        inbox = self._broker(dest).subscribe(group)
        infl = self._inflight.setdefault((dest, group), {})
        out = []
        for tag, v in list(infl.items())[:max_messages]:
            out.append(Delivery(None, v, tag, redelivered=True))
        while inbox and len(out) < max_messages:
            self._n += 1
            tag = f"t{self._n}"
            v = inbox.pop(0)
            infl[tag] = v
            out.append(Delivery(None, v, tag))
        return out

    def ack(self, dest, group, delivery):
        if self._inflight.get((dest, group), {}).pop(delivery.position, None) is None:
            raise BrokerError(NOT_FOUND, "unknown delivery tag")

    def seek(self, dest, group, position):
        raise BrokerError(UNSUPPORTED_FEATURE, feature="replay", provider=self.provider)

    def close(self):
        pass
