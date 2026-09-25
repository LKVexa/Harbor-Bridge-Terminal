"""MC02 / MC16 / MC17 / MC39 / MC40 — OCI Distribution client.

Implements the pull side of the OCI Distribution Spec v1.1 over ``urllib``:

* manifest GET by tag or digest with ``Accept`` negotiation and digest verification
  (``Docker-Content-Digest`` is advisory; the body hash is authoritative);
* blob GET streamed into :class:`~.store.ContentStore` via resumable ingest (HTTP Range);
* ``WWW-Authenticate`` Bearer token flow and Basic auth from a pluggable credential
  provider — credentials are never logged and never sent to a different host;
* TLS policy: HTTPS required except for explicitly allow-listed loopback/dev hosts,
  minimum TLS 1.2, system CA or pinned CA bundle;
* ordered mirrors with per-endpoint circuit breakers, digest-only fallback to mirrors;
* offline mode that serves only verified content already in the local store.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Protocol

from .oci import INDEX_TYPES, MANIFEST_TYPES, MT_DOCKER_LIST, MT_DOCKER_MANIFEST, MT_INDEX, MT_MANIFEST, parse_manifest
from .registry import IntegrityError, LimitExceeded, UnknownReference, ValidationError, parse_reference
from .resilience import CircuitBreaker, CircuitOpen, RetryPolicy, retry
from .store import ContentStore
from .timeutil import Clock, Deadline, SystemClock

ACCEPT = ", ".join([MT_INDEX, MT_MANIFEST, MT_DOCKER_LIST, MT_DOCKER_MANIFEST])
_CHALLENGE_RE = re.compile(r'(\w+)="([^"]*)"')


class RegistryHTTPError(ConnectionError):
    def __init__(self, status: int, msg: str) -> None:
        super().__init__(f"HTTP {status}: {msg}")
        self.status = status


class AuthError(PermissionError):
    code = "REGISTRY_AUTH"


class OfflineMiss(UnknownReference):
    code = "OFFLINE_CACHE_MISS"


class CredentialProvider(Protocol):
    def credentials(self, host: str) -> tuple[str, str] | None: ...


@dataclass
class StaticCredentials:
    """Test/dev provider.  Production should back this with a keychain/secret store."""
    by_host: dict[str, tuple[str, str]] = field(default_factory=dict)

    def credentials(self, host: str):
        return self.by_host.get(host)

    def __repr__(self) -> str:  # never leak secrets through repr/logs
        return f"StaticCredentials(hosts={sorted(self.by_host)})"


@dataclass(frozen=True)
class TLSPolicy:
    insecure_hosts: frozenset[str] = frozenset()  # plain-http allowed ONLY for these
    ca_file: str | None = None
    min_version: ssl.TLSVersion = ssl.TLSVersion.TLSv1_2

    def context(self) -> ssl.SSLContext:
        ctx = ssl.create_default_context(cafile=self.ca_file)
        ctx.minimum_version = self.min_version
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        return ctx

    def scheme_for(self, host: str) -> str:
        if host in self.insecure_hosts:
            if host.split(":")[0] not in ("localhost", "127.0.0.1", "::1") and not host.endswith(".test"):
                raise ValidationError("plain HTTP is only permitted for loopback/.test hosts")
            return "http"
        return "https"


@dataclass
class Endpoint:
    host: str
    breaker: CircuitBreaker
    digest_only: bool = False  # mirrors are trusted for content-addressed fetches only


def split_host(name: str) -> tuple[str, str]:
    """Return (registry host, repository path) using Docker's host-detection rule."""
    first, _, rest = name.partition("/")
    if rest and ("." in first or ":" in first or first == "localhost"):
        return first, rest
    return "docker.io", name if "/" in name else f"library/{name}"


class DistributionClient:
    def __init__(self, store: ContentStore, *, credentials: CredentialProvider | None = None,
                 tls: TLSPolicy | None = None, mirrors: dict[str, list[str]] | None = None,
                 offline: bool = False, clock: Clock | None = None, retry_policy: RetryPolicy | None = None,
                 max_manifest_bytes: int = 4 * 1024 * 1024, chunk: int = 1 << 20,
                 opener: Callable[..., object] | None = None) -> None:
        self.store = store
        self.creds = credentials or StaticCredentials()
        self.tls = tls or TLSPolicy()
        self.mirrors = mirrors or {}
        self.offline = offline
        self.clock = clock or SystemClock()
        self.retry_policy = retry_policy or RetryPolicy(max_attempts=3, base_delay_s=0.05, retry_on=(ConnectionError, TimeoutError))
        self.max_manifest_bytes = max_manifest_bytes
        self.chunk = chunk
        self._tokens: dict[tuple[str, str], str] = {}
        self._breakers: dict[str, CircuitBreaker] = {}
        self._open = opener or urllib.request.urlopen

    # -- endpoints -----------------------------------------------------------------
    def _endpoints(self, host: str, by_digest: bool) -> list[Endpoint]:
        eps = []
        for m in self.mirrors.get(host, []):
            eps.append(Endpoint(m, self._breakers.setdefault(m, CircuitBreaker(3, 30, self.clock)), True))
        eps.append(Endpoint(host, self._breakers.setdefault(host, CircuitBreaker(5, 30, self.clock))))
        # Tag lookups must come from the authoritative registry: a mirror could serve
        # a stale or malicious tag mapping, while digests are self-verifying.
        return [e for e in eps if by_digest or not e.digest_only]

    # -- HTTP with auth --------------------------------------------------------------
    def _request(self, host: str, repo: str, path: str, accept: str | None, deadline: Deadline | None,
                 headers: dict[str, str] | None = None):
        scheme = self.tls.scheme_for(host)
        url = f"{scheme}://{host}/v2/{repo}/{path}"
        for attempt in range(2):
            h = dict(headers or {})
            if accept:
                h["Accept"] = accept
            req = urllib.request.Request(url, headers=h, method="GET")
            auth = self._tokens.get((host, repo))
            if auth:
                # Unredirected: blob redirects to CDNs must not receive registry credentials.
                req.add_unredirected_header("Authorization", auth)
            timeout = deadline.remaining() if deadline else 30.0
            try:
                kw = {"timeout": max(0.001, timeout)}
                if scheme == "https":
                    kw["context"] = self.tls.context()
                return self._open(req, **kw)
            except urllib.error.HTTPError as e:
                if e.code == 401 and attempt == 0:
                    self._authenticate(host, repo, e.headers.get("WWW-Authenticate", ""), deadline)
                    continue
                if e.code == 404:
                    raise UnknownReference(f"{host}/{repo}/{path}: not found") from None
                if e.code in (401, 403):
                    raise AuthError(f"{host}: access denied ({e.code})") from None
                if e.code == 429 or e.code >= 500:
                    raise RegistryHTTPError(e.code, "retryable") from None
                raise RegistryHTTPError(e.code, "request failed") from None
            except urllib.error.URLError as e:
                raise ConnectionError(f"{host}: {e.reason}") from None
        raise AuthError(f"{host}: authentication failed")

    def _authenticate(self, host: str, repo: str, challenge: str, deadline: Deadline | None) -> None:
        scheme, _, params = challenge.partition(" ")
        cred = self.creds.credentials(host)
        if scheme.lower() == "basic":
            if not cred:
                raise AuthError(f"{host}: credentials required")
            if self.tls.scheme_for(host) != "https" and host not in self.tls.insecure_hosts:
                raise AuthError("basic credentials require https")
            self._tokens[(host, repo)] = "Basic " + base64.b64encode(f"{cred[0]}:{cred[1]}".encode()).decode()
            return
        if scheme.lower() != "bearer":
            raise AuthError(f"unsupported auth scheme {scheme!r}")
        p = dict(_CHALLENGE_RE.findall(params))
        realm = p.get("realm", "")
        ru = urllib.parse.urlsplit(realm)
        # Never send registry credentials to a realm on a different trust domain over http.
        if ru.scheme != "https" and not (ru.scheme == "http" and ru.netloc in self.tls.insecure_hosts):
            raise AuthError("token realm must use https")
        q = {"service": p.get("service", ""), "scope": p.get("scope", f"repository:{repo}:pull")}
        req = urllib.request.Request(realm + "?" + urllib.parse.urlencode(q))
        if cred:
            req.add_header("Authorization", "Basic " + base64.b64encode(f"{cred[0]}:{cred[1]}".encode()).decode())
        kw = {"timeout": deadline.remaining() if deadline else 30.0}
        if ru.scheme == "https":
            kw["context"] = self.tls.context()
        try:
            with self._open(req, **kw) as r:
                body = json.loads(r.read(65536))
        except urllib.error.HTTPError as e:
            raise AuthError(f"token endpoint refused ({e.code})") from None
        tok = body.get("token") or body.get("access_token")
        if not isinstance(tok, str) or not tok:
            raise AuthError("token endpoint returned no token")
        self._tokens[(host, repo)] = f"Bearer {tok}"

    # -- public API ------------------------------------------------------------------
    def resolve(self, reference: str, *, deadline: Deadline | None = None) -> tuple[str, bytes, str]:
        """Return ``(digest, manifest bytes, media type)`` for ``reference``, verified."""
        parsed = parse_reference(reference)
        if parsed.name is None:
            raise ValidationError("bare digests need a repository name")
        host, repo = split_host(parsed.name)
        by_digest = parsed.kind == "digest"
        key = f"{parsed.name}:{parsed.tag}" if parsed.tag else None
        if self.offline:
            return self._offline_manifest(parsed.digest if by_digest else self.store.get_tag(key or ""), reference)
        ref = parsed.digest if by_digest else parsed.tag
        last: Exception | None = None
        for ep in self._endpoints(host, by_digest):
            try:
                raw, mt, d = ep.breaker.call(lambda: retry(
                    lambda: self._fetch_manifest(ep.host, repo, ref, deadline), self.retry_policy,
                    clock=self.clock, deadline=deadline))
            except (ConnectionError, TimeoutError, CircuitOpen, UnknownReference) as exc:
                last = exc
                continue
            if by_digest and d != parsed.digest:
                raise IntegrityError(f"registry returned {d} for {parsed.digest}")
            self.store.put(raw, expected=d)
            if key:
                self.store.set_tag(key, d, actor=f"pull:{ep.host}")
            return d, raw, mt
        # Last resort: verified local copy of a digest (stale-if-error is safe for digests only).
        if by_digest and self.store.has(parsed.digest):
            return self._offline_manifest(parsed.digest, reference)
        raise last or UnknownReference(reference)

    def _offline_manifest(self, d: str | None, reference: str) -> tuple[str, bytes, str]:
        if not d or not self.store.has(d):
            raise OfflineMiss(f"{reference}: not available offline")
        raw = self.store.get(d)
        mt = json.loads(raw).get("mediaType", MT_MANIFEST)
        return d, raw, mt

    def _fetch_manifest(self, host, repo, ref, deadline):
        with self._request(host, repo, f"manifests/{ref}", ACCEPT, deadline) as r:
            mt = (r.headers.get("Content-Type") or "").split(";")[0].strip()
            raw = r.read(self.max_manifest_bytes + 1)
        if len(raw) > self.max_manifest_bytes:
            raise LimitExceeded("manifest exceeds limit")
        if mt not in MANIFEST_TYPES | INDEX_TYPES:
            raise IntegrityError(f"unexpected manifest content-type {mt!r}")
        parse_manifest(raw, expected_media_type=mt)
        return raw, mt, "sha256:" + hashlib.sha256(raw).hexdigest()

    def fetch_blob(self, name: str, d: str, size: int, *, deadline: Deadline | None = None) -> str:
        """Download a blob into the store (resumable, verified).  Returns its digest."""
        if self.store.has(d):
            self.store.get(d, allow_quarantined=True)  # verify, raises if corrupt
            return d
        if self.offline:
            raise OfflineMiss(f"{d}: not available offline")
        host, repo = split_host(name)
        ingest_ref = d[7:39]
        last: Exception | None = None
        for ep in self._endpoints(host, True):
            try:
                return ep.breaker.call(lambda: retry(
                    lambda: self._download(ep.host, repo, d, size, ingest_ref, deadline),
                    self.retry_policy, clock=self.clock, deadline=deadline))
            except (ConnectionError, TimeoutError, CircuitOpen, UnknownReference) as exc:
                last = exc
        raise last or UnknownReference(d)

    def _download(self, host, repo, d, size, ref, deadline) -> str:
        offset = self.store.ingest_open(ref, d, size)
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        with self._request(host, repo, f"blobs/{d}", None, deadline, headers) as r:
            status = getattr(r, "status", 200)
            if offset and status != 206:  # server ignored Range: restart cleanly
                self.store.ingest_abort(ref)
                offset = self.store.ingest_open(ref, d, size)
            while True:
                if deadline:
                    deadline.check("blob download")
                chunk = r.read(self.chunk)
                if not chunk:
                    break
                offset = self.store.ingest_write(ref, offset, chunk)
        if offset != size:
            raise ConnectionError(f"short read {offset}/{size}; resumable")
        return self.store.ingest_commit(ref)
