"""AWS SQS adapter over ``boto3`` (component 15).

Mapping: dest -> queue name (``.fifo`` suffix selects FIFO); key -> MessageGroupId (FIFO
per-group ordering); dedup_id -> MessageDeduplicationId (FIFO 5-minute window);
group -> *one queue per consumer group* (``<dest>-<group>``; SNS fan-out to those queues
is an operator concern documented in docs/PROVIDER_MATRIX.md); position -> receipt
handle; ack -> DeleteMessage; un-acked messages reappear after the visibility timeout.
Credentials come from the standard AWS provider chain/IAM role; never from config inline.
"""
from __future__ import annotations

import json
from typing import Any

from ..errors import (INVALID_ARGUMENT, NOT_FOUND, PERMISSION_DENIED, PROVIDER_NOT_INSTALLED, PROVIDER_REJECTED,
                      PROVIDER_UNAVAILABLE, QUOTA_EXCEEDED, UNAUTHENTICATED, UNSUPPORTED_FEATURE, BrokerError)
from .base import Delivery

_CODES = {"AWS.SimpleQueueService.NonExistentQueue": NOT_FOUND, "QueueDoesNotExist": NOT_FOUND,
          "AccessDenied": PERMISSION_DENIED, "AccessDeniedException": PERMISSION_DENIED,
          "InvalidClientTokenId": UNAUTHENTICATED, "ExpiredToken": UNAUTHENTICATED,
          "ThrottlingException": QUOTA_EXCEEDED, "RequestThrottled": QUOTA_EXCEEDED,
          "ServiceUnavailable": PROVIDER_UNAVAILABLE, "InternalError": PROVIDER_UNAVAILABLE,
          "InvalidParameterValue": INVALID_ARGUMENT, "MissingParameter": INVALID_ARGUMENT,
          "ReceiptHandleIsInvalid": INVALID_ARGUMENT}


def translate(exc: BaseException) -> BrokerError:
    code = getattr(exc, "response", {}).get("Error", {}).get("Code", type(exc).__name__)
    if type(exc).__name__ in ("EndpointConnectionError", "ConnectTimeoutError", "ReadTimeoutError"):
        return BrokerError(PROVIDER_UNAVAILABLE, "sqs endpoint", provider_code=type(exc).__name__)
    return BrokerError(_CODES.get(code, PROVIDER_REJECTED), "sqs error", provider_code=code)


class SQSAdapter:
    provider = "sqs"
    features = frozenset({"ack_redelivery", "dedup_window"})

    def __init__(self, *, region: str | None = None, client: Any | None = None,
                 visibility_timeout_s: int = 30, wait_time_s: int = 1) -> None:
        if client is None:
            try:
                import boto3  # type: ignore
            except ImportError as exc:
                raise BrokerError(PROVIDER_NOT_INSTALLED, "pip install 'inv54-broker-implementations[sqs]'",
                                  provider="sqs") from exc
            client = boto3.client("sqs", region_name=region)
        if not 0 <= visibility_timeout_s <= 43200:
            raise BrokerError(INVALID_ARGUMENT, "visibility timeout 0..43200")
        self._c = client
        self._vt, self._wait = visibility_timeout_s, wait_time_s
        self._urls: dict[str, str] = {}
        self._groups: dict[str, list[str]] = {}

    def _url(self, name: str) -> str:
        if name not in self._urls:
            attrs = {"FifoQueue": "true", "ContentBasedDeduplication": "false"} if name.endswith(".fifo") else {}
            try:
                self._urls[name] = self._c.create_queue(QueueName=name, Attributes=attrs)["QueueUrl"]
            except Exception as exc:
                raise translate(exc) from exc
        return self._urls[name]

    @staticmethod
    def _qname(dest: str, group: str) -> str:
        if dest.endswith(".fifo"):
            return f"{dest[:-5]}-{group}.fifo"
        return f"{dest}-{group}"

    def publish(self, dest, value, *, key=None, dedup_id=None):
        """Send to every registered group queue (client-side fan-out, one SendMessage each).

        Not atomic across groups: a failure after the first send raises with the list of
        queues already written in ``details.sent`` so the caller can retry with the same
        dedup_id (FIFO dedup makes the retry effect-idempotent within 5 minutes).
        """
        targets = [self._qname(dest, g) for g in self._groups.get(dest, [])] or [dest]
        if dest.endswith(".fifo") and not dedup_id:
            raise BrokerError(INVALID_ARGUMENT, "FIFO queues require dedup_id (content dedup disabled)")
        ids, sent = [], []
        for q in targets:
            kw: dict[str, Any] = {"QueueUrl": self._url(q), "MessageBody": json.dumps(value)}
            if dest.endswith(".fifo"):
                kw["MessageGroupId"] = key or "default"
                kw["MessageDeduplicationId"] = dedup_id
            try:
                ids.append(self._c.send_message(**kw)["MessageId"])
                sent.append(q)
            except Exception as exc:
                err = translate(exc)
                err.details["sent"] = ",".join(sent)
                raise err from exc
        return ids[0]

    def consume(self, dest, group, max_messages=10):
        if group not in self._groups.setdefault(dest, []):
            self._groups[dest].append(group)
        try:
            r = self._c.receive_message(QueueUrl=self._url(self._qname(dest, group)),
                                        MaxNumberOfMessages=min(10, max_messages), VisibilityTimeout=self._vt,
                                        WaitTimeSeconds=self._wait,
                                        AttributeNames=["ApproximateReceiveCount", "MessageGroupId"])
        except Exception as exc:
            raise translate(exc) from exc
        out = []
        for m in r.get("Messages", []):
            cnt = int(m.get("Attributes", {}).get("ApproximateReceiveCount", "1"))
            out.append(Delivery(m.get("Attributes", {}).get("MessageGroupId"), json.loads(m["Body"]),
                                m["ReceiptHandle"], redelivered=cnt > 1))
        return out

    def ack(self, dest, group, delivery):
        try:
            self._c.delete_message(QueueUrl=self._url(self._qname(dest, group)), ReceiptHandle=delivery.position)
        except Exception as exc:
            raise translate(exc) from exc

    def seek(self, dest, group, position):
        raise BrokerError(UNSUPPORTED_FEATURE, feature="replay", provider=self.provider)

    def close(self):
        pass
