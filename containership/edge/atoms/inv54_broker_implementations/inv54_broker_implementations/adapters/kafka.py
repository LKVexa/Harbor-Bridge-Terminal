"""Kafka adapter over ``confluent-kafka`` (component 13).

Mapping: dest -> topic; key -> message key (Kafka's default partitioner keeps per-key
order); group -> consumer group with ``enable.auto.commit=false`` so offsets are committed
only on ``ack`` (at-least-once); position -> ``partition:offset``; seek -> assign+seek.
Idempotent producer (``enable.idempotence=true``, ``acks=all``) is always on.
Security: SASL/SSL settings come from resolved secret references, never inline.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from ..errors import (INVALID_ARGUMENT, OFFSET_OUT_OF_RANGE, PERMISSION_DENIED, PROVIDER_NOT_INSTALLED,
                      PROVIDER_REJECTED, PROVIDER_UNAVAILABLE, UNAUTHENTICATED, BrokerError)
from .base import Delivery

# librdkafka error names -> INV-54 codes
_ERRMAP = {
    "_TRANSPORT": PROVIDER_UNAVAILABLE, "_ALL_BROKERS_DOWN": PROVIDER_UNAVAILABLE,
    "_TIMED_OUT": PROVIDER_UNAVAILABLE, "NOT_LEADER_FOR_PARTITION": PROVIDER_UNAVAILABLE,
    "LEADER_NOT_AVAILABLE": PROVIDER_UNAVAILABLE, "REQUEST_TIMED_OUT": PROVIDER_UNAVAILABLE,
    "OFFSET_OUT_OF_RANGE": OFFSET_OUT_OF_RANGE,
    "TOPIC_AUTHORIZATION_FAILED": PERMISSION_DENIED, "GROUP_AUTHORIZATION_FAILED": PERMISSION_DENIED,
    "SASL_AUTHENTICATION_FAILED": UNAUTHENTICATED, "_AUTHENTICATION": UNAUTHENTICATED,
    "MSG_SIZE_TOO_LARGE": INVALID_ARGUMENT, "INVALID_MSG": INVALID_ARGUMENT,
}


def translate(err: Any) -> BrokerError:
    name = err.name() if hasattr(err, "name") else str(err)
    return BrokerError(_ERRMAP.get(name, PROVIDER_REJECTED), "kafka error", provider_code=name)


def build_config(endpoints: list[str], *, tls: dict[str, Any] | None = None,
                 sasl: dict[str, Any] | None = None) -> dict[str, Any]:
    if not endpoints:
        raise BrokerError(INVALID_ARGUMENT, "kafka requires bootstrap endpoints")
    c: dict[str, Any] = {"bootstrap.servers": ",".join(endpoints), "enable.idempotence": True, "acks": "all",
                         "enable.auto.commit": False, "auto.offset.reset": "earliest"}
    if tls and tls.get("enabled"):
        c["security.protocol"] = "SASL_SSL" if sasl else "SSL"
        c["ssl.endpoint.identification.algorithm"] = "https"
        if tls.get("ca_file"):
            c["ssl.ca.location"] = tls["ca_file"]
    elif sasl:
        c["security.protocol"] = "SASL_PLAINTEXT"
    if sasl:
        c["sasl.mechanism"] = sasl.get("mechanism", "SCRAM-SHA-512")
        c["sasl.username"] = sasl["username"]
        c["sasl.password"] = sasl["password"].reveal().decode()  # Secret, resolved at activation
    return c


class KafkaAdapter:
    provider = "kafka"
    features = frozenset({"per_key_order", "replay", "independent_offsets"})

    def __init__(self, config: dict[str, Any], *, producer_factory: Callable | None = None,
                 consumer_factory: Callable | None = None, flush_timeout_s: float = 10.0) -> None:
        if producer_factory is None or consumer_factory is None:
            try:
                import confluent_kafka as ck  # type: ignore
            except ImportError as exc:
                raise BrokerError(PROVIDER_NOT_INSTALLED, "pip install 'inv54-broker-implementations[kafka]'",
                                  provider="kafka") from exc
            producer_factory = producer_factory or ck.Producer
            consumer_factory = consumer_factory or ck.Consumer
        self._cfg = config
        self._consumer_factory = consumer_factory
        self._producer = producer_factory({k: v for k, v in config.items()
                                           if k not in ("enable.auto.commit", "auto.offset.reset")})
        self._consumers: dict[str, Any] = {}
        self._flush_timeout = flush_timeout_s

    def _consumer(self, group: str, dest: str):
        c = self._consumers.get(group)
        if c is None:
            c = self._consumer_factory({**{k: v for k, v in self._cfg.items()
                                           if k not in ("enable.idempotence", "acks")}, "group.id": group})
            c.subscribe([dest])
            self._consumers[group] = c
        return c

    def publish(self, dest, value, *, key=None, dedup_id=None):
        result: dict[str, Any] = {}

        def cb(err, msg):
            if err is not None:
                result["err"] = err
            else:
                result["pos"] = f"{msg.partition()}:{msg.offset()}"
        try:
            self._producer.produce(dest, value=json.dumps(value).encode(), key=(key or "").encode(),
                                   on_delivery=cb)
        except BufferError as exc:
            raise BrokerError(PROVIDER_UNAVAILABLE, "producer queue full") from exc
        remaining = self._producer.flush(self._flush_timeout)
        if "err" in result:
            raise translate(result["err"])
        if remaining or "pos" not in result:
            raise BrokerError(PROVIDER_UNAVAILABLE, "delivery not confirmed within timeout")
        return result["pos"]

    def consume(self, dest, group, max_messages=10):
        c = self._consumer(group, dest)
        msgs = c.consume(num_messages=max_messages, timeout=1.0)
        out = []
        for m in msgs:
            if m.error():
                raise translate(m.error())
            k = m.key()
            out.append(Delivery(k.decode() if k else None, json.loads(m.value()), f"{m.partition()}:{m.offset()}"))
        return out

    def ack(self, dest, group, delivery):
        from_tp = self._tp(dest, delivery.position, plus_one=True)
        try:
            self._consumer(group, dest).commit(offsets=[from_tp], asynchronous=False)
        except Exception as exc:
            raise translate(getattr(exc, "args", [exc])[0]) from exc

    def seek(self, dest, group, position):
        try:
            self._consumer(group, dest).seek(self._tp(dest, position))
        except BrokerError:
            raise
        except Exception as exc:
            raise translate(getattr(exc, "args", [exc])[0]) from exc

    def _tp(self, dest, position, plus_one=False):
        try:
            p, o = map(int, position.split(":"))
        except Exception:
            raise BrokerError(INVALID_ARGUMENT, "position must be 'partition:offset'") from None
        try:
            from confluent_kafka import TopicPartition  # type: ignore
        except ImportError:
            from types import SimpleNamespace as TopicPartition  # fake-client path
            return TopicPartition(topic=dest, partition=p, offset=o + (1 if plus_one else 0))
        return TopicPartition(dest, p, o + (1 if plus_one else 0))

    def close(self):
        self._producer.flush(self._flush_timeout)
        for c in self._consumers.values():
            c.close()
