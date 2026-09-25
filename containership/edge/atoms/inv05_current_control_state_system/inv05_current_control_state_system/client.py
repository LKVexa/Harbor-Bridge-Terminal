"""Reference client: deadlines, retries with backoff+jitter, idempotency, watch
resume, and the normative list-then-watch algorithm (MC-017-05, MC-026).

Retry policy (MC-026-03/06):
    attempt budget ``max_attempts`` (default 5) and time budget ``budget_s``;
    delay = min(cap, base * 2**(attempt-1)) with *full jitter*; a server
    ``retry_after_s`` hint is a floor.  Only ``retryable`` errors are retried,
    and a mutating txn is retried only when it carries a ``request_id``
    (token-idempotent); otherwise the caller must re-read and decide.

Normative list-then-watch (race-free, survives compaction)::

    loop:
        snap_rev, items = list_all(prefix)            # every page at ONE revision
        watch(prefix, start_revision = snap_rev + 1)
        for frame in stream:
            events   -> apply; resume = frame.revision + 1
            progress -> resume = frame.revision + 1
            canceled(COMPACTED)                -> goto loop  (relist)
            canceled(SLOW_CONSUMER|DRAINING|*) -> reconnect watch at resume
"""
from __future__ import annotations

import http.client
import json
import random
import ssl
import time
import uuid
from typing import Any, Callable, Iterator

from .errors import StateError, from_wire


class Client:
    def __init__(self, host: str, port: int, *, ssl_context: ssl.SSLContext | None = None, token: str | None = None,
                 max_attempts: int = 5, base_delay: float = 0.05, max_delay: float = 2.0, budget_s: float = 15.0,
                 timeout_s: float = 10.0, rng: random.Random | None = None,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.host, self.port, self.ctx, self.token = host, port, ssl_context, token
        self.max_attempts, self.base, self.cap, self.budget, self.timeout = max_attempts, base_delay, max_delay, budget_s, timeout_s
        self.rng = rng or random.Random()
        self.sleep = sleep
        self.retries = 0

    def _conn(self, timeout: float | None = None) -> http.client.HTTPConnection:
        if self.ctx:
            return http.client.HTTPSConnection(self.host, self.port, context=self.ctx, timeout=timeout or self.timeout)
        return http.client.HTTPConnection(self.host, self.port, timeout=timeout or self.timeout)

    def _headers(self, attempt: int, rid: str, deadline_ms: int | None, ns: str | None) -> dict[str, str]:
        h = {"content-type": "application/json", "x-request-id": rid, "x-cstate-attempt": str(attempt)}
        if self.token:
            h["authorization"] = f"Bearer {self.token}"
        if deadline_ms:
            h["x-cstate-deadline-ms"] = str(deadline_ms)
        if ns:
            h["x-cstate-namespace"] = ns
        return h

    def call(self, path: str, body: dict[str, Any] | None = None, *, idempotent: bool = True,
             deadline_ms: int | None = None, namespace: str | None = None, method: str = "POST") -> Any:
        rid = uuid.uuid4().hex
        start = time.monotonic()
        attempt = 0
        while True:
            attempt += 1
            try:
                c = self._conn()
                payload = json.dumps(body or {}).encode() if method == "POST" else None
                c.request(method, path, body=payload, headers=self._headers(attempt, rid, deadline_ms, namespace))
                r = c.getresponse()
                data = r.read()
                c.close()
                if r.status == 200:
                    ctype = r.getheader("content-type", "")
                    return json.loads(data) if ctype.startswith("application/json") else data.decode()
                err = from_wire(json.loads(data).get("error", {}))
            except (ConnectionError, OSError, http.client.HTTPException) as exc:
                from .errors import Unavailable
                err = Unavailable(f"transport error: {type(exc).__name__}")
            if not (err.spec.retryable and idempotent) or attempt >= self.max_attempts:
                raise err
            delay = self.rng.uniform(0, min(self.cap, self.base * 2 ** (attempt - 1)))
            delay = max(delay, float(err.details.get("retry_after_s", 0) or 0))
            if time.monotonic() - start + delay > self.budget:
                raise err
            self.retries += 1
            self.sleep(delay)

    # convenience ---------------------------------------------------------------
    def txn(self, compare=(), success=(), failure=(), request_id: str | None = None, **kw: Any) -> dict[str, Any]:
        body: dict[str, Any] = {"schema": "cstate.txn/1.1", "compare": list(compare), "success": list(success),
                                "failure": list(failure)}
        if request_id:
            body["request_id"] = request_id
        mutating = any(("put" in o or "delete" in o) for o in list(success) + list(failure))
        return self.call("/v1/txn", body, idempotent=(not mutating) or bool(request_id), **kw)

    def range(self, key: str, **kw: Any) -> dict[str, Any]:
        return self.call("/v1/range", {"schema": "cstate.range/1.1", "key": key, **kw})

    def list_all(self, prefix: str = "") -> tuple[int, list[dict[str, Any]]]:
        items: list[dict[str, Any]] = []
        body: dict[str, Any] = {"schema": "cstate.range/1.1", "key": prefix, "prefix": True, "limit": 500}
        while True:
            r = self.call("/v1/range", body)
            items += r["kvs"]
            if not r["more"]:
                return r["revision"], items
            body = {"schema": "cstate.range/1.1", "key": prefix, "prefix": True, "limit": 500,
                    "page_token": r["next_token"]}

    def watch(self, prefix: str = "", start_revision: int = 0, progress_ms: int = 1000,
              timeout_s: float = 60.0) -> Iterator[dict[str, Any]]:
        c = self._conn(timeout=timeout_s)
        body = json.dumps({"schema": "cstate.watch/1.1", "prefix": prefix, "start_revision": start_revision,
                           "progress_interval_ms": progress_ms}).encode()
        c.request("POST", "/v1/watch", body=body, headers=self._headers(1, uuid.uuid4().hex, None, None))
        r = c.getresponse()
        if r.status != 200:
            raise from_wire(json.loads(r.read()).get("error", {}))
        try:
            while True:
                line = r.readline()
                if not line:
                    return
                if line.strip():
                    yield json.loads(line)
        finally:
            c.close()


class Mirror:
    """Local cache kept consistent with a prefix via the normative algorithm."""

    def __init__(self, client: Client, prefix: str = "") -> None:
        self.client, self.prefix = client, prefix
        self.items: dict[str, Any] = {}
        self.revision = 0
        self.relists = 0

    def relist(self) -> None:
        rev, items = self.client.list_all(self.prefix)
        self.items = {kv["key"]: kv["value"] for kv in items}
        self.revision = rev
        self.relists += 1

    def run(self, until: Callable[["Mirror"], bool], max_reconnects: int = 20) -> None:
        self.relist()
        reconnects = 0
        while not until(self) and reconnects <= max_reconnects:
            try:
                for f in self.client.watch(self.prefix, self.revision + 1, progress_ms=200, timeout_s=10):
                    if f["type"] == "events":
                        for e in f["events"]:
                            if e["kind"] in ("DELETE", "EXPIRE"):
                                self.items.pop(e["key"], None)
                            else:
                                self.items[e["key"]] = e["value"]
                        self.revision = f["revision"]
                    elif f["type"] == "progress":
                        self.revision = max(self.revision, f["revision"])
                    elif f["type"] == "canceled":
                        if f.get("error", {}).get("code") == "CSTATE_COMPACTED":
                            self.relist()
                        break
                    if until(self):
                        return
            except StateError as exc:
                if exc.code == "CSTATE_COMPACTED":
                    self.relist()
                elif not exc.spec.retryable:
                    raise
            except (OSError, http.client.HTTPException):
                pass
            reconnects += 1
