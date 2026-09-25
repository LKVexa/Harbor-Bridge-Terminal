"""Reference PK_TOPO_* client (MC-019): builds canonical envelopes, applies
the retry policy only to retryable outcomes and always sends an idempotency
key on mutations so retries are safe."""
from __future__ import annotations

import itertools
import secrets
from typing import Any
from collections.abc import Callable

from . import errors, wire
from .resilience import RetryPolicy, retry_call


class Client:
    def __init__(self, transport: Callable[[bytes], bytes], tenant: str, credential: Callable[[], str],
                 *, retry: RetryPolicy | None = None, sleep: Callable[[float], None] | None = None):
        self.transport, self.tenant, self.credential = transport, tenant, credential
        self.retry = retry or RetryPolicy()
        self._sleep = sleep
        self._ids = itertools.count(1)

    def _rid(self) -> str:
        return f"req-{secrets.token_hex(4)}-{next(self._ids):06d}"

    def call(self, protocol: str, op: str, body: dict[str, Any], *, idempotent: bool = False,
             deadline_ms: int | None = None, traceparent: str | None = None) -> dict[str, Any]:
        rid = self._rid()
        idem = f"idem-{secrets.token_hex(8)}" if idempotent else None

        def attempt() -> dict[str, Any]:
            env: dict[str, Any] = {"protocol": protocol, "op": op, "tenant": self.tenant, "request_id": rid,
                                   "credential": self.credential(), "body": body}
            if idem:
                env["idempotency_key"] = idem
            if deadline_ms:
                env["deadline_ms"] = deadline_ms
            if traceparent:
                env["traceparent"] = traceparent
            resp = wire.decode(self.transport(wire.encode(env)))
            err = resp.get("error")
            if err:
                code = errors.registry().get(err["code"], errors.INTERNAL)
                raise errors.TopoError(code, err["message"], err.get("details", {}), err.get("retry_after_ms"))
            return resp

        if self._sleep is not None:
            return retry_call(attempt, self.retry, sleep=self._sleep)
        return retry_call(attempt, self.retry)

    # convenience ------------------------------------------------------------
    def apply(self, mutations: list[dict[str, Any]], expected_revision: int | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"mutations": mutations}
        if expected_revision is not None:
            body["expected_revision"] = expected_revision
        return self.call("PK_TOPO_GRAPH/1", "apply", body, idempotent=True)

    def get(self) -> dict[str, Any]:
        return self.call("PK_TOPO_GRAPH/1", "get", {})

    def resolve(self, origin: str, capability: str, **constraints: Any) -> dict[str, Any]:
        explain = constraints.pop("explain", False)
        body: dict[str, Any] = {"origin": origin, "capability": capability}
        if constraints:
            body["constraints"] = constraints
        if explain:
            body["explain"] = True
        return self.call("PK_TOPO_NEAREST/1", "resolve", body)

    def status(self, site: str, cloud: str | None = None) -> dict[str, Any]:
        body = {"site": site} | ({"cloud": cloud} if cloud else {})
        return self.call("PK_TOPO_PARTITION/1", "status", body)

    def acquire(self, site: str, candidate: str) -> dict[str, Any]:
        return self.call("PK_TOPO_PARTITION/1", "acquire", {"site": site, "candidate": candidate}, idempotent=True)

    def renew(self, site: str, candidate: str, token: int) -> dict[str, Any]:
        return self.call("PK_TOPO_PARTITION/1", "renew", {"site": site, "candidate": candidate, "fencing_token": token},
                         idempotent=True)

    def validate_token(self, site: str, token: int) -> dict[str, Any]:
        return self.call("PK_TOPO_PARTITION/1", "validate_token", {"site": site, "fencing_token": token})
