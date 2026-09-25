"""G13-MC-011 policy distribution client/controller.

Pull-based: a ``Fetcher`` returns the newest signed envelope (or ``None`` if
unchanged).  The controller is idempotent (same digest -> no-op), retries with
capped exponential backoff and full jitter, honours cancellation, and never
bypasses verification/anti-replay/controls -- it calls ``PolicyService.load``
(or ``stage`` when separation of duties requires a human activator).
"""
from __future__ import annotations

import hashlib
import random
import ssl
import threading
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from .errors import DependencyUnavailable, PolicyError


class Fetcher(Protocol):
    def fetch(self, *, timeout: float) -> bytes | None: ...


@dataclass
class FileFetcher:
    path: Path

    def fetch(self, *, timeout: float) -> bytes | None:
        try:
            return Path(self.path).read_bytes()
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise DependencyUnavailable(f"file fetch failed: {exc}") from exc


@dataclass
class HttpsFetcher:
    """Authenticated HTTPS pull.  TLS verification is always on; plain http is refused."""
    url: str
    bearer_token: Callable[[], str]
    ca_file: str | None = None
    max_bytes: int = 2_097_152
    _etag: str | None = None

    def __post_init__(self) -> None:
        if not self.url.startswith("https://"):
            raise ValueError("distribution endpoint must be https://")

    def fetch(self, *, timeout: float) -> bytes | None:
        ctx = ssl.create_default_context(cafile=self.ca_file)
        req = urllib.request.Request(self.url, headers={"Authorization": f"Bearer {self.bearer_token()}",
                                                        "Accept": "application/json"})
        if self._etag:
            req.add_header("If-None-Match", self._etag)
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                data = resp.read(self.max_bytes + 1)
                if len(data) > self.max_bytes:
                    raise DependencyUnavailable("distribution payload exceeds limit")
                self._etag = resp.headers.get("ETag")
                return data
        except urllib.error.HTTPError as exc:
            if exc.code == 304:
                return None
            raise DependencyUnavailable(f"distribution HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise DependencyUnavailable(f"distribution unreachable: {type(exc).__name__}") from exc


@dataclass
class DistributionController:
    service: Any
    fetcher: Fetcher
    principal: Any
    interval_s: float = 30.0
    timeout_s: float = 10.0
    backoff_base_s: float = 1.0
    backoff_max_s: float = 300.0
    mode: str = "load"                 # "load" | "stage"
    rng: random.Random = field(default_factory=random.Random)
    failures: int = 0
    last_digest: str | None = None
    history: list[dict[str, Any]] = field(default_factory=list)

    def next_delay(self) -> float:
        if self.failures == 0:
            return self.interval_s
        cap = min(self.backoff_max_s, self.backoff_base_s * (2 ** min(self.failures, 20)))
        return self.rng.uniform(0, cap)            # full jitter

    def poll_once(self) -> str:
        try:
            data = self.fetcher.fetch(timeout=self.timeout_s)
        except PolicyError as exc:
            self.failures += 1
            self.history.append({"result": "fetch-error", "code": exc.code})
            self.service.metrics.inc("distribution_failures")
            return "fetch-error"
        if data is None:
            self.failures = 0
            return "unchanged"
        digest = hashlib.sha256(data).hexdigest()
        if digest == self.last_digest:
            self.failures = 0
            return "unchanged"
        try:
            if self.mode == "stage":
                self.service.stage(self.principal, data)
            else:
                self.service.load(self.principal, data, reason="distribution")
        except PolicyError as exc:
            # a rejected bundle is not retried until a *different* one arrives
            self.last_digest = digest
            self.history.append({"result": "rejected", "code": exc.code})
            self.service.metrics.inc("distribution_rejections", code=exc.code)
            return "rejected"
        self.last_digest = digest
        self.failures = 0
        self.history.append({"result": "applied"})
        return "applied"

    def run(self, stop: threading.Event) -> None:
        while not stop.is_set():
            self.poll_once()
            stop.wait(self.next_delay())
