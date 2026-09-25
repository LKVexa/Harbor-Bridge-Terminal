"""HashiCorp Vault adapter (checklist #15, #16, #18, #44).

Standard library only (no ``hvac`` dependency) so the supply chain stays small.
Supports:

* KV v2 (read latest / pinned version, CAS write, metadata, destroy) and KV v1 (read/write)
* Vault Enterprise namespaces (``X-Vault-Namespace``)
* Auth: static token (dev only), AppRole, Kubernetes service-account JWT
* Token lifecycle: lookup-self TTL tracking and renew-self before expiry
* Dynamic-secret leases: ``sys/leases/renew`` and ``sys/leases/revoke``
* ``sys/health`` mapping (sealed / standby / uninitialised)
* TLS: HTTPS required unless ``allow_insecure_http`` is set for loopback tests;
  TLS >= 1.2, CA bundle pinning, optional client certificate (mTLS)

Compatibility (docs/architecture/compatibility-matrix.md): Vault server 1.15-1.18
KV engine v1/v2, HTTP API ``/v1``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import ssl
import threading
import time
from typing import Callable
import urllib.error
import urllib.parse
import urllib.request

from ..secretvalue import SecretValue
from .base import (ProviderConflict, ProviderDenied, ProviderError, ProviderHealth,
                   ProviderNotFound, ProviderSecret, ProviderUnavailable)

SUPPORTED_SERVER_VERSIONS = ("1.15", "1.16", "1.17", "1.18")
MAX_RESPONSE_BYTES = 1_048_576


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes


Transport = Callable[[str, str, dict, bytes | None, float], HttpResponse]


def urllib_transport(ssl_context: ssl.SSLContext | None) -> Transport:
    def _send(method: str, url: str, headers: dict, body: bytes | None, timeout: float) -> HttpResponse:
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
                data = resp.read(MAX_RESPONSE_BYTES + 1)
                return HttpResponse(resp.status, data)
        except urllib.error.HTTPError as exc:
            return HttpResponse(exc.code, exc.read(MAX_RESPONSE_BYTES + 1))
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            raise ProviderUnavailable(f"transport failure: {type(exc).__name__}") from None
    return _send


def build_tls_context(ca_file: str | None = None, client_cert: str | None = None,
                      client_key: str | None = None) -> ssl.SSLContext:
    ctx = ssl.create_default_context(cafile=ca_file)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    if client_cert:
        ctx.load_cert_chain(client_cert, client_key)
    return ctx


@dataclass
class TokenAuth:
    """Static token.  Development and break-glass only."""
    token: SecretValue

    def login(self, adapter: "VaultProvider") -> tuple[SecretValue, float | None]:
        return self.token, None


@dataclass
class AppRoleAuth:
    role_id: str
    secret_id: SecretValue
    mount: str = "approle"

    def login(self, adapter: "VaultProvider") -> tuple[SecretValue, float | None]:
        body = {"role_id": self.role_id, "secret_id": self.secret_id.reveal()}
        data = adapter._request("POST", f"auth/{self.mount}/login", body, auth=False)
        auth = data.get("auth") or {}
        return SecretValue(auth["client_token"]), float(auth.get("lease_duration", 0)) or None


@dataclass
class KubernetesAuth:
    role: str
    jwt_path: str = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    mount: str = "kubernetes"

    def login(self, adapter: "VaultProvider") -> tuple[SecretValue, float | None]:
        with open(self.jwt_path, "r", encoding="utf-8") as fh:
            jwt = fh.read().strip()
        data = adapter._request("POST", f"auth/{self.mount}/login", {"role": self.role, "jwt": jwt}, auth=False)
        auth = data.get("auth") or {}
        return SecretValue(auth["client_token"]), float(auth.get("lease_duration", 0)) or None


@dataclass
class VaultProvider:
    address: str
    auth: object
    mount: str = "secret"
    kv_version: int = 2
    namespace: str | None = None
    timeout_s: float = 2.0
    ssl_context: ssl.SSLContext | None = None
    allow_insecure_http: bool = False
    transport: Transport | None = None
    clock: Callable[[], float] = time.monotonic
    renew_fraction: float = 0.67
    name: str = "vault"
    _token: SecretValue | None = field(default=None, init=False, repr=False)
    _token_expires: float | None = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        parsed = urllib.parse.urlparse(self.address)
        if parsed.scheme not in ("https", "http"):
            raise ValueError("vault address must be http(s)")
        if parsed.scheme == "http":
            loopback = parsed.hostname in ("127.0.0.1", "localhost", "::1")
            if not (self.allow_insecure_http and loopback):
                raise ValueError("plaintext HTTP to Vault is refused (encryption in transit required)")
        if self.kv_version not in (1, 2):
            raise ValueError("kv_version must be 1 or 2")
        if self.transport is None:
            ctx = self.ssl_context if parsed.scheme == "https" else None
            if parsed.scheme == "https" and ctx is None:
                ctx = build_tls_context()
            self.transport = urllib_transport(ctx)
        self.address = self.address.rstrip("/")

    # ------------------------------------------------------------------ transport
    def _ensure_token(self) -> SecretValue:
        with self._lock:
            now = self.clock()
            if self._token is None or (self._token_expires is not None and now >= self._token_expires):
                token, ttl = self.auth.login(self)
                self._token = token
                self._token_expires = None if ttl is None else now + ttl * self.renew_fraction
            return self._token

    def _request(self, method: str, path: str, body: dict | None = None, *, auth: bool = True,
                 ok_statuses: tuple[int, ...] = (200, 204)) -> dict:
        headers = {"Content-Type": "application/json", "User-Agent": "inv55-secrets/4.3.0"}
        if self.namespace:
            headers["X-Vault-Namespace"] = self.namespace
        if auth:
            headers["X-Vault-Token"] = self._ensure_token().reveal()
        payload = None if body is None else json.dumps(body).encode()
        url = f"{self.address}/v1/{path.lstrip('/')}"
        resp = self.transport(method, url, headers, payload, self.timeout_s)
        if len(resp.body) > MAX_RESPONSE_BYTES:
            raise ProviderError("vault response exceeds size limit")
        if resp.status in ok_statuses:
            if not resp.body:
                return {}
            try:
                return json.loads(resp.body)
            except ValueError:
                raise ProviderError("vault returned malformed JSON") from None
        if resp.status == 404:
            raise ProviderNotFound(path)
        if resp.status in (401, 403):
            with self._lock:
                self._token = None   # force re-login next call
            raise ProviderDenied(f"vault denied {method} {path}")
        if resp.status == 400 and b"check-and-set" in resp.body:
            raise ProviderConflict(path)
        if resp.status in (429, 500, 502, 503, 504):
            raise ProviderUnavailable(f"vault status {resp.status}")
        raise ProviderError(f"vault status {resp.status}")

    def _kv(self, kind: str, name: str) -> str:
        quoted = urllib.parse.quote(name, safe="/-_.:")
        if self.kv_version == 1:
            return f"{self.mount}/{quoted}"
        return f"{self.mount}/{kind}/{quoted}"

    # ------------------------------------------------------------------ provider API
    def read(self, name: str, version: int | None = None) -> ProviderSecret:
        path = self._kv("data", name)
        if version is not None and self.kv_version == 2:
            path += f"?version={int(version)}"
        raw = self._request("GET", path)
        data = raw.get("data") or {}
        dyn_lease = raw.get("lease_id") or None
        dyn_ttl = float(raw.get("lease_duration") or 0) or None
        if self.kv_version == 2:
            meta = data.get("metadata") or {}
            if meta.get("destroyed") or meta.get("deletion_time"):
                raise ProviderNotFound(f"{name}@{meta.get('version')}")
            fields = data.get("data") or {}
            v = int(meta.get("version", version or 0))
        else:
            fields, v = data, 1
        if "value" not in fields or not isinstance(fields["value"], str):
            raise ProviderError("secret payload lacks string field 'value'")
        return ProviderSecret(name, v, SecretValue(fields["value"]), provider_lease_id=dyn_lease,
                              provider_ttl_s=dyn_ttl)

    def write(self, name: str, value: SecretValue, cas: int | None = None) -> int:
        if self.kv_version == 1:
            self._request("POST", self._kv("data", name), {"value": value.reveal()})
            return 1
        body: dict = {"data": {"value": value.reveal()}}
        if cas is not None:
            body["options"] = {"cas": int(cas)}
        data = self._request("POST", self._kv("data", name), body).get("data") or {}
        return int(data["version"])

    def metadata(self, name: str) -> dict:
        if self.kv_version == 1:
            raise ProviderError("metadata unsupported on KV v1")
        data = self._request("GET", self._kv("metadata", name)).get("data") or {}
        return {"current_version": data.get("current_version"),
                "destroyed": sorted(int(k) for k, v in (data.get("versions") or {}).items() if v.get("destroyed"))}

    def destroy_version(self, name: str, version: int) -> None:
        if self.kv_version == 1:
            raise ProviderError("destroy unsupported on KV v1")
        self._request("POST", self._kv("destroy", name), {"versions": [int(version)]})

    def renew(self, provider_lease_id: str, increment_s: float) -> float:
        data = self._request("PUT", "sys/leases/renew", {"lease_id": provider_lease_id,
                                                          "increment": int(increment_s)})
        return float(data.get("lease_duration", 0))

    def revoke(self, provider_lease_id: str) -> None:
        self._request("PUT", "sys/leases/revoke", {"lease_id": provider_lease_id})

    def renew_self(self) -> float:
        data = self._request("POST", "auth/token/renew-self", {})
        ttl = float((data.get("auth") or {}).get("lease_duration", 0))
        with self._lock:
            self._token_expires = self.clock() + ttl * self.renew_fraction if ttl else None
        return ttl

    def health(self) -> ProviderHealth:
        try:
            # 429 = standby, 472/473 = DR/perf standby, 501 = uninitialised, 503 = sealed
            data = self._request("GET", "sys/health", auth=False,
                                 ok_statuses=(200, 429, 472, 473, 501, 503))
        except ProviderError as exc:
            return ProviderHealth(False, detail=type(exc).__name__)
        sealed = bool(data.get("sealed"))
        version = data.get("version")
        supported = isinstance(version, str) and version.startswith(SUPPORTED_SERVER_VERSIONS)
        # DR secondaries (standbycode 472) cannot serve KV reads -> not reachable for our purposes
        dr_secondary = data.get("replication_dr_mode") == "secondary"
        return ProviderHealth(reachable=not sealed and not dr_secondary and bool(data.get("initialized", True)),
                              sealed=sealed,
                              version=version, detail="" if supported else "unsupported_server_version")
