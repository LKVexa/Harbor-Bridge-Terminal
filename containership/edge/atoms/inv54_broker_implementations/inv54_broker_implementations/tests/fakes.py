"""In-process fake provider clients.

They emulate only the client-library surface each adapter calls, with the provider's
documented semantics (Kafka keyed partitioning + committed offsets, RabbitMQ fanout
exchange + unacked redelivery, SQS visibility timeout + FIFO dedup).  They verify the
*adapter's mapping and error translation*; they are not evidence about the real services.
"""
from __future__ import annotations

import itertools
import zlib
from types import SimpleNamespace


# ------------------------------------------------------------------ Kafka
class KafkaError:
    def __init__(self, name):
        self._n = name

    def name(self):
        return self._n


class _Cluster:
    def __init__(self, partitions=3):
        self.topics: dict[str, list[list[tuple[bytes, bytes]]]] = {}
        self.committed: dict[tuple[str, str, int], int] = {}
        self.partitions = partitions
        self.fail_next: str | None = None


class FakeProducer:
    def __init__(self, cluster: _Cluster):
        self.c = cluster
        self._pending = []

    def produce(self, topic, value, key, on_delivery):
        parts = self.c.topics.setdefault(topic, [[] for _ in range(self.c.partitions)])
        if self.c.fail_next:
            err, self.c.fail_next = KafkaError(self.c.fail_next), None
            self._pending.append((on_delivery, err, None))
            return
        p = zlib.crc32(key) % len(parts)
        parts[p].append((key, value))
        msg = SimpleNamespace(partition=lambda p=p: p, offset=lambda o=len(parts[p]) - 1: o)
        self._pending.append((on_delivery, None, msg))

    def flush(self, timeout=None):
        for cb, err, msg in self._pending:
            cb(err, msg)
        self._pending.clear()
        return 0


class FakeConsumer:
    def __init__(self, cluster: _Cluster, group: str):
        self.c, self.group, self.topic = cluster, group, None
        self.pos: dict[int, int] = {}

    def subscribe(self, topics):
        self.topic = topics[0]

    def consume(self, num_messages, timeout):
        parts = self.c.topics.setdefault(self.topic, [[] for _ in range(self.c.partitions)])
        out = []
        for p, log in enumerate(parts):
            start = self.pos.get(p, self.c.committed.get((self.group, self.topic, p), 0))
            for i in range(start, min(len(log), start + num_messages - len(out))):
                k, v = log[i]
                out.append(SimpleNamespace(error=lambda: None, key=lambda k=k: k, value=lambda v=v: v,
                                           partition=lambda p=p: p, offset=lambda i=i: i))
                self.pos[p] = i + 1
        return out

    def commit(self, offsets, asynchronous):
        for tp in offsets:
            self.c.committed[(self.group, tp.topic, tp.partition)] = tp.offset

    def seek(self, tp):
        parts = self.c.topics.get(tp.topic, [])
        if tp.partition >= len(parts) or tp.offset > len(parts[tp.partition]):
            raise Exception(KafkaError("OFFSET_OUT_OF_RANGE"))
        self.pos[tp.partition] = tp.offset
        self.c.committed[(self.group, tp.topic, tp.partition)] = tp.offset

    def close(self):
        pass


def kafka_factories(cluster=None):
    cluster = cluster or _Cluster()
    return cluster, (lambda cfg: FakeProducer(cluster)), (lambda cfg: FakeConsumer(cluster, cfg["group.id"]))


# ------------------------------------------------------------------ RabbitMQ
class AMQPConnectionError(Exception):
    pass


class ChannelClosedByBroker(Exception):
    pass


class FakeChannel:
    def __init__(self):
        self.exchanges: dict[str, set[str]] = {}
        self.queues: dict[str, list] = {}
        self.unacked: dict[int, tuple[str, bytes]] = {}
        self.redelivered: set[int] = set()
        self.tags = itertools.count(1)
        self.down = False
        self.confirms = False

    def confirm_delivery(self):
        self.confirms = True

    def exchange_declare(self, exchange, exchange_type, durable):
        assert exchange_type == "fanout" and durable
        self.exchanges.setdefault(exchange, set())

    def queue_declare(self, queue, durable):
        self.queues.setdefault(queue, [])

    def queue_bind(self, queue, exchange):
        self.exchanges[exchange].add(queue)

    def basic_publish(self, exchange, routing_key, body, properties, mandatory):
        if self.down:
            raise AMQPConnectionError()
        for q in self.exchanges[exchange]:
            self.queues[q].append((body, False))

    def basic_get(self, queue, auto_ack):
        # unacked messages stay with the consumer until ack, nack(requeue) or channel loss
        if not self.queues.get(queue):
            return None, None, None
        body, redelivered = self.queues[queue].pop(0)
        tag = next(self.tags)
        self.unacked[tag] = (queue, body)
        return SimpleNamespace(delivery_tag=tag, redelivered=redelivered), None, body

    def basic_ack(self, delivery_tag):
        if delivery_tag not in self.unacked:
            raise ChannelClosedByBroker("PRECONDITION_FAILED - unknown delivery tag")
        self.unacked.pop(delivery_tag)

    def basic_nack(self, delivery_tag, requeue):
        q, body = self.unacked.pop(delivery_tag)
        if requeue:
            self.queues[q].insert(0, (body, True))

    def close(self):
        pass


# ------------------------------------------------------------------ SQS
class ClientError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class FakeSQS:
    def __init__(self, clock=None):
        self.q: dict[str, list[dict]] = {}
        self.dedup: dict[tuple[str, str], float] = {}
        self.now = 0.0
        self.ids = itertools.count(1)
        self.throttle = False

    def create_queue(self, QueueName, Attributes):
        self.q.setdefault(QueueName, [])
        return {"QueueUrl": f"https://sqs.fake/{QueueName}"}

    def _q(self, url):
        name = url.rsplit("/", 1)[1]
        if name not in self.q:
            raise ClientError("AWS.SimpleQueueService.NonExistentQueue")
        return self.q[name]

    def send_message(self, QueueUrl, MessageBody, MessageGroupId=None, MessageDeduplicationId=None):
        if self.throttle:
            raise ClientError("ThrottlingException")
        q = self._q(QueueUrl)
        if MessageDeduplicationId:
            k = (QueueUrl, MessageDeduplicationId)
            if k in self.dedup and self.now - self.dedup[k] < 300:
                return {"MessageId": "dup"}
            self.dedup[k] = self.now
        mid = str(next(self.ids))
        q.append({"MessageId": mid, "Body": MessageBody, "group": MessageGroupId, "visible_at": 0.0,
                  "count": 0, "handle": None})
        return {"MessageId": mid}

    def receive_message(self, QueueUrl, MaxNumberOfMessages, VisibilityTimeout, WaitTimeSeconds, AttributeNames):
        out = []
        for m in self._q(QueueUrl):
            if len(out) >= MaxNumberOfMessages:
                break
            if m["visible_at"] <= self.now:
                m["count"] += 1
                m["visible_at"] = self.now + VisibilityTimeout
                m["handle"] = f"rh-{m['MessageId']}-{m['count']}"
                out.append({"Body": m["Body"], "ReceiptHandle": m["handle"],
                            "Attributes": {"ApproximateReceiveCount": str(m["count"]),
                                           **({"MessageGroupId": m["group"]} if m["group"] else {})}})
        return {"Messages": out} if out else {}

    def delete_message(self, QueueUrl, ReceiptHandle):
        q = self._q(QueueUrl)
        for i, m in enumerate(q):
            if m["handle"] == ReceiptHandle:
                del q[i]
                return {}
        raise ClientError("ReceiptHandleIsInvalid")
