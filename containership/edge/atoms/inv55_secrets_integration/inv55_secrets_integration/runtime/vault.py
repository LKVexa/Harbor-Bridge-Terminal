"""HashiCorp Vault KV v2 adapter (checklist #15, #16, #44).

Stdlib only (``urllib`` + ``ssl``).  Tested against an in-process HTTP double
that speaks the documented KV v2 wire format (``tests/fake_vault.py``); it has
NOT been certified against a real Vault server - see COMPATIBILITY.md.

Transport rules (fail closed):
* ``https`` is required.  Plain ``http`` is accepted only when
  ``allow_insecure_loopback=True`` AND the host is a loopback literal; this is
  the test lane and is refused by :mod:`config` for any ``environment`` other
  than ``test``.
* TLS >= 1.2, hostname verification on, optional CA bundle and client
  certificate (mTLS).
* The Vault token is held in a non-string ``_SecretValue``; it is never logged.
* Responses larger than ``max_response_bytes`` are rejected.
"""
from __future__ import annotations

import ipaddress
import json
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from ..reference import _SecretValue
from .errors import INV55Error
from .provider import ProviderHealth, ProviderSecret, SecretProvider

SUPPORTED_VAULT_API = "v1"          # HTTP API path prefix
KV_ENGINE_VERSION = 2
TESTED_AGAINST = ("fake_vault KV v2 double (tests/fake_vault.py)",)
PATH_SAFE = "/-_.:"


def _is_loopback(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class VaultAuth:
    """Base class: obtains and renews a client token."""

    def login(self, adapter: "VaultKV2Provider") -> tuple[_SecretValue, float | None]:
        raise NotImplementedError


class StaticTokenAuth(VaultAuth):
    def __init__(self, token: str, ttl_s: float | None = None):
        self._token, self._ttl = _SecretValue(token), ttl_s

    def login(self, adapter):
        return self._token, self._ttl


class AppRoleAuth(VaultAuth):
    def __init__(self, role_id: str, secret_id: str, mount: str = "approle"):
        self.role_id, self._secret_id, self.mount = role_id, _SecretValue(secret_id), mount

    def login(self, adapter):
        body = adapter._request("POST", f"auth/{self.mount}/login",
                                {"role_id": self.role_id, "secret_id": self._secret_id._reveal()},
                                authenticated=False)
        auth = body.get("auth") or {}
        tok = auth.get("client_token")
        if not isinstance(tok, str) or not tok:
            raise INV55Error("INV55-E-UNAUTHENTICATED", "approle login returned no token")
        return _SecretValue(tok), float(auth.get("lease_duration") or 0) or None


class VaultKV2Provider(SecretProvider):
    name = "vault-kv2"

    def __init__(self, address: str, *, mount: str = "secret", auth: VaultAuth, namespace: str | None = None,
                 ca_file: str | None = None, client_cert: tuple[str, str] | None = None,
                 allow_insecure_loopback: bool = False, max_response_bytes: int = 1 << 20,
                 renew_margin_s: float = 30.0, clock=time.monotonic):
        u = urllib.parse.urlsplit(address)
        if u.scheme == "http":
            if not (allow_insecure_loopback and _is_loopback(u.hostname or "")):
                raise INV55Error("INV55-E-CONFIG", "plain http refused outside the loopback test lane")
            self._ctx = None
        elif u.scheme == "https":
            ctx = ssl.create_default_context(cafile=ca_file)
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            ctx.check_hostname = True
            ctx.verify_mode = ssl.CERT_REQUIRED
            if client_cert:
                ctx.load_cert_chain(*client_cert)
            self._ctx = ctx
        else:
            raise INV55Error("INV55-E-CONFIG", "vault address must be https")
        if not mount or any(c not in PATH_SAFE and not c.isalnum() for c in mount):
            raise INV55Error("INV55-E-CONFIG", "invalid mount")
        self.address = address.rstrip("/")
        self.mount, self.namespace, self.auth = mount.strip("/"), namespace, auth
        self.max_response_bytes, self.renew_margin_s, self.clock = max_response_bytes, renew_margin_s, clock
        self._token: _SecretValue | None = None
        self._token_expiry: float | None = None
        self._lock = threading.Lock()

    # -- transport ---------------------------------------------------------
    def _ensure_token(self):
        with self._lock:
            now = self.clock()
            if self._token is None or (self._token_expiry is not None and now >= self._token_expiry - self.renew_margin_s):
                tok, ttl = self.auth.login(self)
                self._token = tok
                self._token_expiry = (now + ttl) if ttl else None
            return self._token

    def _request(self, method, path, payload=None, *, authenticated=True, timeout_s=5.0, ok=(200, 204)):
        path = path.lstrip("/")
        url = f"{self.address}/{SUPPORTED_VAULT_API}/{path}"
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self.namespace:
            req.add_header("X-Vault-Namespace", self.namespace)
        if authenticated:
            req.add_header("X-Vault-Token", self._ensure_token()._reveal())
        try:
            with urllib.request.urlopen(req, timeout=timeout_s, context=self._ctx) as resp:
                raw = resp.read(self.max_response_bytes + 1)
                status = resp.status
        except urllib.error.HTTPError as e:
            status = e.code
            try:
                raw = e.read(self.max_response_bytes + 1) or b""
            finally:
                e.close()
        except (socket.timeout, TimeoutError):
            raise INV55Error("INV55-E-DEADLINE", f"{method} {path} timed out") from None
        except (urllib.error.URLError, ConnectionError, ssl.SSLError) as e:
            raise INV55Error("INV55-E-PROVIDER-UNAVAILABLE", f"transport: {type(e).__name__}") from None
        if len(raw) > self.max_response_bytes:
            raise INV55Error("INV55-E-PROVIDER-UNAVAILABLE", "response exceeds max_response_bytes")
        if status in ok:
            if not raw:
                return {}
            try:
                return json.loads(raw)
            except ValueError:
                raise INV55Error("INV55-E-PROVIDER-UNAVAILABLE", "malformed provider JSON") from None
        if status in (403, 404):
            if status == 403 and authenticated:
                with self._lock:
                    self._token = None   # force re-login next call
            raise INV55Error("INV55-E-DENIED", f"vault {status}")
        if status == 400:
            raise INV55Error("INV55-E-INVALID-REQUEST", "vault 400")
        if status == 412:
            raise INV55Error("INV55-E-CONFLICT", "vault cas mismatch")
        raise INV55Error("INV55-E-PROVIDER-UNAVAILABLE", f"vault {status}")

    @staticmethod
    def _q(name: str) -> str:
        return urllib.parse.quote(name, safe="/")

    # -- SecretProvider ----------------------------------------------------
    def read(self, name, version=None, *, timeout_s):
        q = f"?version={int(version)}" if version else ""
        body = self._request("GET", f"{self.mount}/data/{self._q(name)}{q}", timeout_s=timeout_s)
        d = (body.get("data") or {})
        meta = d.get("metadata") or {}
        if meta.get("destroyed") or meta.get("deletion_time"):
            raise INV55Error("INV55-E-VERSION-RETIRED", "version destroyed/deleted")
        inner = d.get("data")
        if not isinstance(inner, dict) or not isinstance(inner.get("value"), str):
            raise INV55Error("INV55-E-PROVIDER-UNAVAILABLE", "kv payload lacks string field 'value'")
        v = meta.get("version")
        if not isinstance(v, int) or v < 1:
            raise INV55Error("INV55-E-PROVIDER-UNAVAILABLE", "kv payload lacks version")
        return ProviderSecret(name, v, _SecretValue(inner["value"]), body.get("lease_id") or None,
                              float(body.get("lease_duration") or 0) or None)

    def write(self, name, value, *, cas, timeout_s):
        payload = {"data": {"value": value}}
        if cas is not None:
            payload["options"] = {"cas": int(cas)}
        body = self._request("POST", f"{self.mount}/data/{self._q(name)}", payload, timeout_s=timeout_s)
        v = (body.get("data") or {}).get("version")
        if not isinstance(v, int):
            raise INV55Error("INV55-E-PROVIDER-UNAVAILABLE", "write returned no version")
        return v

    def metadata(self, name, *, timeout_s):
        body = self._request("GET", f"{self.mount}/metadata/{self._q(name)}", timeout_s=timeout_s)
        d = body.get("data") or {}
        return {"current_version": d.get("current_version"),
                "destroyed": sorted(int(k) for k, v in (d.get("versions") or {}).items() if v.get("destroyed"))}

    def destroy_version(self, name, version, *, timeout_s):
        self._request("POST", f"{self.mount}/destroy/{self._q(name)}", {"versions": [int(version)]}, timeout_s=timeout_s)

    def revoke_lease(self, provider_lease_id, *, timeout_s):
        self._request("PUT", "sys/leases/revoke", {"lease_id": provider_lease_id}, timeout_s=timeout_s)

    def health(self, *, timeout_s):
        try:
            body = self._request("GET", "sys/health", authenticated=False, timeout_s=timeout_s,
                                 ok=(200, 429, 472, 473, 501, 503))
        except INV55Error as e:
            return ProviderHealth(False, None, e.code)
        sealed = bool(body.get("sealed"))
        ok = bool(body.get("initialized")) and not sealed
        return ProviderHealth(ok, sealed, "sealed" if sealed else ("ok" if ok else "uninitialised"), body.get("version"))
