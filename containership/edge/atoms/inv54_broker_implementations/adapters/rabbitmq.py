"""RabbitMQ adapter over ``pika`` (component 14).

Mapping: dest -> fanout exchange ``inv54.<dest>``; group -> durable queue
``inv54.<dest>.<group>`` bound to it (every group receives every message = fan-out);
publisher confirms on; messages persistent (delivery_mode=2); position -> delivery tag;
ack -> basic_ack; un-acked messages are redelivered by the broker (``redelivered`` flag
preserved).  Replay is not a RabbitMQ classic-queue capability -> UNSUPPORTED_FEATURE.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from ..errors import (INVALID_ARGUMENT, PERMISSION_DENIED, PROVIDER_NOT_INSTALLED, PROVIDER_REJECTED,
                      PROVIDER_UNAVAILABLE, UNAUTHENTICATED, UNSUPPORTED_FEATURE, BrokerError)
from .base import Delivery

_EXC = {"AMQPConnectionError": PROVIDER_UNAVAILABLE, "StreamLostError": PROVIDER_UNAVAILABLE,
        "ConnectionClosedByBroker": PROVIDER_UNAVAILABLE, "ChannelClosedByBroker": PROVIDER_REJECTED,
        "ProbableAuthenticationError": UNAUTHENTICATED, "ProbableAccessDeniedError": PERMISSION_DENIED,
        "UnroutableError": PROVIDER_REJECTED, "NackError": PROVIDER_UNAVAILABLE}


def translate(exc: BaseException) -> BrokerError:
    return BrokerError(_EXC.get(type(exc).__name__, PROVIDER_REJECTED), "rabbitmq error",
                       provider_code=type(exc).__name__)


class RabbitMQAdapter:
    provider = "rabbitmq"
    features = frozenset({"fanout", "ack_redelivery"})

    def __init__(self, url: str | None = None, *, channel_factory: Callable[[], Any] | None = None) -> None:
        if channel_factory is None:
            if not url:
                raise BrokerError(INVALID_ARGUMENT, "rabbitmq requires an amqp(s):// URL")
            try:
                import pika  # type: ignore
            except ImportError as exc:
                raise BrokerError(PROVIDER_NOT_INSTALLED, "pip install 'inv54-broker-implementations[rabbitmq]'",
                                  provider="rabbitmq") from exc

            def channel_factory():
                conn = pika.BlockingConnection(pika.URLParameters(url))
                return conn.channel()
        try:
            self._ch = channel_factory()
            self._ch.confirm_delivery()
        except BrokerError:
            raise
        except Exception as exc:
            raise translate(exc) from exc
        self._declared: set[str] = set()

    def _declare(self, dest: str, group: str | None = None) -> str:
        ex = f"inv54.{dest}"
        if ex not in self._declared:
            self._ch.exchange_declare(exchange=ex, exchange_type="fanout", durable=True)
            self._declared.add(ex)
        if group is None:
            return ex
        q = f"{ex}.{group}"
        if q not in self._declared:
            self._ch.queue_declare(queue=q, durable=True)
            self._ch.queue_bind(queue=q, exchange=ex)
            self._declared.add(q)
        return q

    def publish(self, dest, value, *, key=None, dedup_id=None):
        ex = self._declare(dest)
        props = {"delivery_mode": 2, "content_type": "application/json", "message_id": dedup_id}
        try:
            try:
                import pika  # type: ignore
                props = pika.BasicProperties(**props)
            except ImportError:
                pass
            self._ch.basic_publish(exchange=ex, routing_key=key or "", body=json.dumps(value).encode(),
                                   properties=props, mandatory=False)
        except Exception as exc:
            raise translate(exc) from exc
        return dedup_id or "confirmed"

    def consume(self, dest, group, max_messages=10):
        q = self._declare(dest, group)
        out = []
        for _ in range(max_messages):
            method, _props, body = self._ch.basic_get(queue=q, auto_ack=False)
            if method is None:
                break
            out.append(Delivery(None, json.loads(body), str(method.delivery_tag), bool(method.redelivered)))
        return out

    def ack(self, dest, group, delivery):
        try:
            self._ch.basic_ack(delivery_tag=int(delivery.position))
        except Exception as exc:
            raise translate(exc) from exc

    def nack(self, dest, group, delivery, requeue=True):
        """Return an unacked delivery to the queue; the broker redelivers it with redelivered=True."""
        try:
            self._ch.basic_nack(delivery_tag=int(delivery.position), requeue=requeue)
        except Exception as exc:
            raise translate(exc) from exc

    def seek(self, dest, group, position):
        raise BrokerError(UNSUPPORTED_FEATURE, feature="replay", provider=self.provider)

    def close(self):
        try:
            self._ch.close()
        except Exception:
            pass
