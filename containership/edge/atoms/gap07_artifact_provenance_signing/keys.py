"""Production key-custody contract and KMS/HSM provider adapters (v6).

``KeyCustody`` exposes sign / public-key / metadata / health operations and
never returns private-key bytes.  Provider adapters translate the normalized
``KeyRef`` into AWS KMS, Azure Key Vault / Managed HSM, Google Cloud KMS,
HashiCorp Vault Transit and PKCS#11 calls on an *injected, already
authenticated* client (workload identity is the caller's responsibility; no
adapter accepts static credentials).  ``ResilientCustody`` adds timeouts,
bounded retries for transient failures only, a circuit breaker, idempotent
request correlation and - critically - verifies every returned signature
against the pinned public key before releasing it, so an alias that silently
moved to another key version is detected (KEY_MISMATCH) instead of trusted.

The adapters are written against the providers' documented SDK surfaces and
are exercised here with faithful fakes.  Live-provider conformance runs are
an estate integration step (see MISSING_COMPONENTS.md / TRACEABILITY.json).
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol

from . import algorithms as algs
from .errors import GapError, fail

PROTECTION_LEVELS = ("software", "hsm", "external-hsm", "tpm")


@dataclass(frozen=True)
class KeyRef:
    """Normalized, namespace-qualified key identity."""

    provider: str          # aws-kms | azure-kv | gcp-kms | vault-transit | pkcs11 | tpm | software
    tenant: str
    site: str
    environment: str
    name: str              # provider key id / alias / label
    version: str           # pinned provider key version - aliases never float
    algorithm: str
    region: str = ""
    protection_level: str = "hsm"

    @property
    def kid(self) -> str:
        """Globally unique key id: ``tenant/site/env/provider:name@version``."""
        return f"{self.tenant}/{self.site}/{self.environment}/{self.provider}:{self.name}@{self.version}"

    def __post_init__(self) -> None:
        for fld in ("provider", "tenant", "site", "environment", "name", "version", "algorithm"):
            v = getattr(self, fld)
            if not isinstance(v, str) or not v or any(c in v for c in "\x00\n\r") or len(v) > 256:
                raise ValueError(f"KeyRef.{fld} invalid")
        if self.protection_level not in PROTECTION_LEVELS:
            raise ValueError("unknown protection level")
        algs.get(self.algorithm, profile=algs.PROFILE_REFERENCE)


@dataclass(frozen=True)
class KeyMetadata:
    ref: KeyRef
    enabled: bool
    exportable: bool
    protection_level: str
    public_key_spki: bytes
    allowed_algorithms: frozenset[str]
    extra: Mapping[str, Any] = field(default_factory=dict)


class KeyCustody(Protocol):
    def sign(self, ref: KeyRef, message: bytes, *, request_id: str) -> bytes: ...
    def public_key(self, ref: KeyRef) -> bytes: ...
    def metadata(self, ref: KeyRef) -> KeyMetadata: ...
    def health(self, ref: KeyRef) -> dict[str, Any]: ...


class ProviderTransient(Exception):
    """Adapter-internal: throttling/timeout/outage (retryable)."""


class ProviderPermanent(Exception):
    """Adapter-internal: disabled/deleted/denied/invalid (not retryable)."""


class ProviderMismatch(ProviderPermanent):
    """Adapter-internal: provider answered for a different key/version/algorithm."""


# --------------------------------------------------------------- software (dev)

class SoftwareKeyCustody:
    """In-process custody for tests/dev.  Protection level 'software'.

    Keys are generated internally and there is deliberately no API to read
    them.  A production custody policy (``require_protection``) refuses it.
    """

    provider = "software"

    def __init__(self) -> None:
        self.__keys: dict[str, Any] = {}
        self.__disabled: set[str] = set()
        self._lock = threading.Lock()

    def __repr__(self) -> str:
        return f"SoftwareKeyCustody(keys={len(self.__keys)})"

    def create(self, ref: KeyRef) -> bytes:
        if ref.provider != "software" or ref.protection_level != "software":
            raise ValueError("software custody only creates provider=software, protection_level=software keys")
        with self._lock:
            if ref.kid in self.__keys:
                raise fail("KEY_ID_COLLISION", "key id already exists", kid=ref.kid)
            self.__keys[ref.kid] = algs.generate_private_key(ref.algorithm)
            return algs.spki(self.__keys[ref.kid].public_key())

    def disable(self, ref: KeyRef) -> None:
        self.__disabled.add(ref.kid)

    def _key(self, ref: KeyRef):
        if ref.kid in self.__disabled:
            raise ProviderPermanent("key disabled")
        try:
            return self.__keys[ref.kid]
        except KeyError as exc:
            raise ProviderPermanent("no such key") from exc

    def sign(self, ref: KeyRef, message: bytes, *, request_id: str) -> bytes:
        return algs.software_signer(ref.algorithm, self._key(ref))(message)

    def public_key(self, ref: KeyRef) -> bytes:
        return algs.spki(self._key(ref).public_key())

    def metadata(self, ref: KeyRef) -> KeyMetadata:
        key = self._key(ref)
        return KeyMetadata(ref, True, False, "software", algs.spki(key.public_key()), frozenset({ref.algorithm}))

    def health(self, ref: KeyRef) -> dict[str, Any]:
        self._key(ref)
        return {"ok": True, "provider": "software"}


# ---------------------------------------------------------- provider adapters

_AWS_ALG = {"ecdsa-p256-sha256": "ECDSA_SHA_256", "ecdsa-p384-sha384": "ECDSA_SHA_384",
            "rsa-pss-sha256-3072": "RSASSA_PSS_SHA_256", "rsa-pss-sha384-4096": "RSASSA_PSS_SHA_384",
            "ed25519": "ED25519_SHA_512"}
_AWS_TRANSIENT = {"ThrottlingException", "KMSInternalException", "DependencyTimeoutException", "LimitExceededException"}


def _err_code(exc: Exception) -> str:
    resp = getattr(exc, "response", None)
    if isinstance(resp, Mapping):
        return str(resp.get("Error", {}).get("Code", ""))
    return type(exc).__name__


class AwsKmsCustody:
    """AWS KMS via an injected ``boto3.client('kms')`` bound to workload identity."""

    provider = "aws-kms"

    def __init__(self, client: Any):
        self._c = client

    def _call(self, fn: Callable[[], Any]) -> Any:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - classify provider errors
            code = _err_code(exc)
            if code in _AWS_TRANSIENT or isinstance(exc, (TimeoutError, ConnectionError)):
                raise ProviderTransient(code) from exc
            raise ProviderPermanent(code) from exc

    def _key_id(self, ref: KeyRef) -> str:
        # AWS asymmetric keys have no user-visible versions; the pinned
        # "version" is the concrete key id so aliases can never redirect.
        return ref.version

    def sign(self, ref: KeyRef, message: bytes, *, request_id: str) -> bytes:
        kw = {"MessageType": "RAW"}  # KMS hashes; message is the length-delimited signed bytes
        resp = self._call(lambda: self._c.sign(KeyId=self._key_id(ref), Message=message,
                                               SigningAlgorithm=_AWS_ALG[ref.algorithm], **kw))
        if resp.get("KeyId", "").split("/")[-1] != self._key_id(ref).split("/")[-1]:
            raise ProviderMismatch("KMS answered with a different key id")
        if resp.get("SigningAlgorithm") != _AWS_ALG[ref.algorithm]:
            raise ProviderMismatch("KMS answered with a different algorithm")
        return bytes(resp["Signature"])

    def public_key(self, ref: KeyRef) -> bytes:
        return bytes(self._call(lambda: self._c.get_public_key(KeyId=self._key_id(ref)))["PublicKey"])

    def metadata(self, ref: KeyRef) -> KeyMetadata:
        md = self._call(lambda: self._c.describe_key(KeyId=self._key_id(ref)))["KeyMetadata"]
        pub = self._call(lambda: self._c.get_public_key(KeyId=self._key_id(ref)))
        origin = md.get("Origin", "AWS_KMS")
        level = "external-hsm" if origin in ("AWS_CLOUDHSM", "EXTERNAL_KEY_STORE") else "hsm"
        allowed = {a for a, v in _AWS_ALG.items() if v in set(pub.get("SigningAlgorithms", []))}
        return KeyMetadata(ref, md.get("KeyState") == "Enabled" and md.get("Enabled", False), False, level,
                           bytes(pub["PublicKey"]), frozenset(allowed), {"key_state": md.get("KeyState"), "origin": origin})

    def health(self, ref: KeyRef) -> dict[str, Any]:
        md = self._call(lambda: self._c.describe_key(KeyId=self._key_id(ref)))["KeyMetadata"]
        return {"ok": md.get("KeyState") == "Enabled", "provider": self.provider, "key_state": md.get("KeyState")}


class GcpKmsCustody:
    """Google Cloud KMS via injected ``kms_v1.KeyManagementServiceClient``."""

    provider = "gcp-kms"
    _PROT = {1: "software", 2: "hsm", 3: "external-hsm", 4: "external-hsm"}

    def __init__(self, client: Any):
        self._c = client

    def _name(self, ref: KeyRef) -> str:
        return f"{ref.name}/cryptoKeyVersions/{ref.version}"

    def _call(self, fn: Callable[[], Any]) -> Any:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            name = type(exc).__name__
            if name in {"ServiceUnavailable", "DeadlineExceeded", "TooManyRequests", "ResourceExhausted", "InternalServerError"} or isinstance(exc, (TimeoutError, ConnectionError)):
                raise ProviderTransient(name) from exc
            raise ProviderPermanent(name) from exc

    def sign(self, ref: KeyRef, message: bytes, *, request_id: str) -> bytes:
        if ref.algorithm == "ed25519":
            req = {"name": self._name(ref), "data": message}
        else:
            h = hashlib.sha384 if "sha384" in ref.algorithm else hashlib.sha256
            req = {"name": self._name(ref), "digest": {h().name: h(message).digest()}}
        resp = self._call(lambda: self._c.asymmetric_sign(request=req))
        if getattr(resp, "name", self._name(ref)) != self._name(ref):
            raise ProviderMismatch("KMS answered for a different key version")
        return bytes(resp.signature)

    def public_key(self, ref: KeyRef) -> bytes:
        from cryptography.hazmat.primitives import serialization
        pem = self._call(lambda: self._c.get_public_key(request={"name": self._name(ref)})).pem
        return algs.spki(serialization.load_pem_public_key(pem.encode() if isinstance(pem, str) else pem))

    def metadata(self, ref: KeyRef) -> KeyMetadata:
        v = self._call(lambda: self._c.get_crypto_key_version(request={"name": self._name(ref)}))
        return KeyMetadata(ref, int(getattr(v, "state", 0)) == 1, False, self._PROT.get(int(getattr(v, "protection_level", 0)), "software"),
                           self.public_key(ref), frozenset({ref.algorithm}), {"state": int(getattr(v, "state", 0))})

    def health(self, ref: KeyRef) -> dict[str, Any]:
        v = self._call(lambda: self._c.get_crypto_key_version(request={"name": self._name(ref)}))
        return {"ok": int(getattr(v, "state", 0)) == 1, "provider": self.provider}


class AzureKeyVaultCustody:
    """Azure Key Vault / Managed HSM via injected ``KeyClient`` + CryptographyClient factory."""

    provider = "azure-kv"
    _ALG = {"ecdsa-p256-sha256": "ES256", "ecdsa-p384-sha384": "ES384", "rsa-pss-sha256-3072": "PS256", "rsa-pss-sha384-4096": "PS384"}

    def __init__(self, key_client: Any, crypto_client_factory: Callable[[str], Any]):
        self._kc = key_client
        self._cf = crypto_client_factory

    def _call(self, fn: Callable[[], Any]) -> Any:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            status = getattr(exc, "status_code", None)
            if status in (408, 429, 500, 502, 503, 504) or isinstance(exc, (TimeoutError, ConnectionError)):
                raise ProviderTransient(str(status)) from exc
            raise ProviderPermanent(str(status or type(exc).__name__)) from exc

    def sign(self, ref: KeyRef, message: bytes, *, request_id: str) -> bytes:
        if ref.algorithm not in self._ALG:
            raise ProviderPermanent("algorithm not supported by Azure Key Vault")
        h = hashlib.sha384 if "sha384" in ref.algorithm else hashlib.sha256
        key = self._call(lambda: self._kc.get_key(ref.name, version=ref.version))
        res = self._call(lambda: self._cf(key.id).sign(self._ALG[ref.algorithm], h(message).digest()))
        if not str(getattr(res, "key_id", key.id)).endswith(ref.version):
            raise ProviderMismatch("Key Vault answered for a different key version")
        sig = bytes(res.signature)
        if ref.algorithm.startswith("ecdsa"):  # JOSE r||s -> DER
            from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
            n = len(sig) // 2
            sig = encode_dss_signature(int.from_bytes(sig[:n], "big"), int.from_bytes(sig[n:], "big"))
        return sig

    def public_key(self, ref: KeyRef) -> bytes:
        key = self._call(lambda: self._kc.get_key(ref.name, version=ref.version))
        return _jwk_to_spki(key.key)

    def metadata(self, ref: KeyRef) -> KeyMetadata:
        key = self._call(lambda: self._kc.get_key(ref.name, version=ref.version))
        props = key.properties
        kty = str(getattr(key.key, "kty", ""))
        level = "hsm" if kty.endswith("-HSM") else "software"
        return KeyMetadata(ref, bool(props.enabled), bool(getattr(props, "exportable", False)), level,
                           _jwk_to_spki(key.key), frozenset({ref.algorithm}), {"kty": kty})

    def health(self, ref: KeyRef) -> dict[str, Any]:
        key = self._call(lambda: self._kc.get_key(ref.name, version=ref.version))
        return {"ok": bool(key.properties.enabled), "provider": self.provider}


def _jwk_to_spki(jwk: Any) -> bytes:
    from cryptography.hazmat.primitives.asymmetric import ec as _ec, rsa as _rsa
    kty = str(getattr(jwk, "kty", ""))
    if kty.startswith("EC"):
        crv = {"P-256": _ec.SECP256R1(), "P-384": _ec.SECP384R1()}[str(jwk.crv)]
        pub = _ec.EllipticCurvePublicNumbers(int.from_bytes(jwk.x, "big"), int.from_bytes(jwk.y, "big"), crv).public_key()
    else:
        pub = _rsa.RSAPublicNumbers(int.from_bytes(jwk.e, "big"), int.from_bytes(jwk.n, "big")).public_key()
    return algs.spki(pub)


class VaultTransitCustody:
    """HashiCorp Vault Transit via injected ``hvac.Client`` (auth via workload identity)."""

    provider = "vault-transit"
    _TYPE = {"ed25519": "ed25519", "ecdsa-p256-sha256": "ecdsa-p256", "ecdsa-p384-sha384": "ecdsa-p384",
             "rsa-pss-sha256-3072": "rsa-3072", "rsa-pss-sha384-4096": "rsa-4096"}

    def __init__(self, client: Any, mount_point: str = "transit"):
        self._c = client
        self._mp = mount_point

    def _call(self, fn: Callable[[], Any]) -> Any:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            if type(exc).__name__ in {"VaultDown", "InternalServerError", "RateLimitExceeded", "BadGateway"} or isinstance(exc, (TimeoutError, ConnectionError)):
                raise ProviderTransient(type(exc).__name__) from exc
            raise ProviderPermanent(type(exc).__name__) from exc

    def sign(self, ref: KeyRef, message: bytes, *, request_id: str) -> bytes:
        import base64
        kw: dict[str, Any] = {"name": ref.name, "hash_input": base64.b64encode(message).decode(), "key_version": int(ref.version),
                              "mount_point": self._mp, "marshaling_algorithm": "asn1"}
        if ref.algorithm.startswith("rsa-pss"):
            kw.update(signature_algorithm="pss", hash_algorithm="sha2-384" if "sha384" in ref.algorithm else "sha2-256")
        elif ref.algorithm.startswith("ecdsa"):
            kw.update(hash_algorithm="sha2-384" if "sha384" in ref.algorithm else "sha2-256")
        resp = self._call(lambda: self._c.secrets.transit.sign_data(**kw))
        sig = resp["data"]["signature"]  # "vault:v<N>:<b64>"
        prefix, ver, b64 = sig.split(":", 2)
        if prefix != "vault" or ver != f"v{ref.version}":
            raise ProviderMismatch("Vault answered with a different key version")
        return base64.b64decode(b64, validate=True)

    def _key(self, ref: KeyRef) -> Mapping[str, Any]:
        return self._call(lambda: self._c.secrets.transit.read_key(name=ref.name, mount_point=self._mp))["data"]

    def public_key(self, ref: KeyRef) -> bytes:
        import base64
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519 as _ed
        entry = self._key(ref)["keys"][str(ref.version)]
        pk = entry["public_key"]
        if ref.algorithm == "ed25519":
            return algs.spki(_ed.Ed25519PublicKey.from_public_bytes(base64.b64decode(pk)))
        return algs.spki(serialization.load_pem_public_key(pk.encode()))

    def metadata(self, ref: KeyRef) -> KeyMetadata:
        d = self._key(ref)
        if d.get("type") != self._TYPE.get(ref.algorithm):
            raise ProviderMismatch("Vault key type does not match declared algorithm")
        enabled = int(ref.version) >= int(d.get("min_decryption_version", 1)) and str(ref.version) in d.get("keys", {})
        return KeyMetadata(ref, enabled, bool(d.get("exportable", False)), "software" if not d.get("managed_key_name") else "hsm",
                           self.public_key(ref), frozenset({ref.algorithm}), {"latest_version": d.get("latest_version")})

    def health(self, ref: KeyRef) -> dict[str, Any]:
        d = self._key(ref)
        return {"ok": str(ref.version) in d.get("keys", {}), "provider": self.provider}


class Pkcs11Custody:
    """PKCS#11 HSM via an injected ``pkcs11`` (python-pkcs11) session factory.

    ``session_factory()`` must return a context-managed, already-logged-in
    session; PINs are the operator's secret-manager concern, never GAP-07's.
    """

    provider = "pkcs11"

    def __init__(self, session_factory: Callable[[], Any], mechanisms: Mapping[str, Any]):
        self._sf = session_factory
        self._mech = dict(mechanisms)

    def _call(self, fn: Callable[[Any], Any]) -> Any:
        try:
            with self._sf() as session:
                return fn(session)
        except Exception as exc:  # noqa: BLE001
            name = type(exc).__name__
            if name in {"SessionCount", "DeviceError", "DeviceRemoved", "TokenNotPresent"} or isinstance(exc, (TimeoutError, ConnectionError)):
                raise ProviderTransient(name) from exc
            raise ProviderPermanent(name) from exc

    def sign(self, ref: KeyRef, message: bytes, *, request_id: str) -> bytes:
        return bytes(self._call(lambda s: s.get_key(label=f"{ref.name}@{ref.version}", object_class="PRIVATE_KEY").sign(message, mechanism=self._mech[ref.algorithm])))

    def public_key(self, ref: KeyRef) -> bytes:
        return bytes(self._call(lambda s: s.get_key(label=f"{ref.name}@{ref.version}", object_class="PUBLIC_KEY").spki()))

    def metadata(self, ref: KeyRef) -> KeyMetadata:
        def _md(s):
            priv = s.get_key(label=f"{ref.name}@{ref.version}", object_class="PRIVATE_KEY")
            return bool(getattr(priv, "extractable", True)), bool(getattr(priv, "sensitive", False))
        extractable, sensitive = self._call(_md)
        return KeyMetadata(ref, True, extractable or not sensitive, "hsm", self.public_key(ref), frozenset({ref.algorithm}))

    def health(self, ref: KeyRef) -> dict[str, Any]:
        self.public_key(ref)
        return {"ok": True, "provider": self.provider}


# ------------------------------------------------------------- resilience

@dataclass
class CustodyPolicy:
    require_protection: frozenset[str] = frozenset({"hsm", "external-hsm", "tpm"})
    require_non_exportable: bool = True
    timeout_s: float = 5.0
    max_attempts: int = 3
    backoff_s: float = 0.05
    breaker_threshold: int = 5
    breaker_reset_s: float = 30.0
    policy_check_ttl_s: float = 60.0


class ResilientCustody:
    """Fail-closed wrapper: timeouts, retry, breaker, response pinning, audit."""

    def __init__(self, inner: KeyCustody, pinned_spki: Mapping[str, bytes], policy: CustodyPolicy | None = None,
                 *, audit: Any = None, clock: Callable[[], float] = time.monotonic):
        self._inner = inner
        self._pins = dict(pinned_spki)
        self.policy = policy or CustodyPolicy()
        self._audit = audit
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None
        self._lock = threading.Lock()
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="gap07-kms")
        self._policy_ok: dict[str, float] = {}

    # breaker ------------------------------------------------------------
    def _breaker_check(self) -> None:
        with self._lock:
            if self._opened_at is not None:
                if self._clock() - self._opened_at < self.policy.breaker_reset_s:
                    raise fail("CIRCUIT_OPEN", "key provider circuit breaker open")
                self._opened_at = None  # half-open: allow one probe
                self._failures = self.policy.breaker_threshold - 1

    def _record(self, ok: bool) -> None:
        with self._lock:
            if ok:
                self._failures = 0
            else:
                self._failures += 1
                if self._failures >= self.policy.breaker_threshold:
                    self._opened_at = self._clock()

    def _invoke(self, fn: Callable[[], Any], op: str, ref: KeyRef, request_id: str) -> Any:
        self._breaker_check()
        last: Exception | None = None
        for attempt in range(1, self.policy.max_attempts + 1):
            fut = self._pool.submit(fn)
            try:
                result = fut.result(timeout=self.policy.timeout_s)
                self._record(True)
                return result
            except concurrent.futures.TimeoutError as exc:
                fut.cancel()
                last = exc
            except ProviderTransient as exc:
                last = exc
            except GapError:
                self._record(False)
                raise
            except ProviderMismatch as exc:
                self._record(False)
                self._emit("custody.response_mismatch", ref, op, request_id, str(exc))
                raise fail("KEY_MISMATCH", "provider answered for a different key/version/algorithm", kid=ref.kid, op=op) from exc
            except ProviderPermanent as exc:
                self._record(False)
                self._emit("custody.permanent_failure", ref, op, request_id, str(exc))
                raise fail("KEY_DISABLED", "key provider refused the operation", kid=ref.kid, op=op, provider_code=str(exc)[:64]) from exc
            except Exception as exc:  # noqa: BLE001 - unexpected adapter/SDK defect: counted, structured, not retried
                self._record(False)
                self._emit("custody.unexpected_failure", ref, op, request_id, type(exc).__name__)
                raise fail("KEY_UNAVAILABLE", "key provider adapter failed unexpectedly", kid=ref.kid, op=op, error=type(exc).__name__) from exc
            time.sleep(self.policy.backoff_s * attempt)
        self._record(False)
        self._emit("custody.transient_failure", ref, op, request_id, type(last).__name__)
        raise fail("KEY_UNAVAILABLE", "key provider unavailable after retries", kid=ref.kid, op=op, attempts=self.policy.max_attempts)

    def _emit(self, event: str, ref: KeyRef, op: str, request_id: str, reason: str) -> None:
        if self._audit is not None:
            self._audit.append(event, {"kid": ref.kid, "op": op, "request_id": request_id, "reason": reason[:128]})

    # contract -----------------------------------------------------------
    def check_key_policy(self, ref: KeyRef) -> KeyMetadata:
        rid = str(uuid.uuid4())
        md: KeyMetadata = self._invoke(lambda: self._inner.metadata(ref), "metadata", ref, rid)
        if not md.enabled:
            raise fail("KEY_DISABLED", "key is not enabled at provider", kid=ref.kid)
        if md.protection_level not in self.policy.require_protection:
            raise fail("KEY_POLICY_VIOLATION", "key protection level not permitted", kid=ref.kid, protection=md.protection_level)
        if self.policy.require_non_exportable and md.exportable:
            raise fail("KEY_POLICY_VIOLATION", "exportable private keys are not permitted", kid=ref.kid)
        if ref.algorithm not in md.allowed_algorithms:
            raise fail("KEY_POLICY_VIOLATION", "provider key does not permit declared algorithm", kid=ref.kid)
        pin = self._pins.get(ref.kid)
        if pin is None or md.public_key_spki != pin:
            raise fail("KEY_MISMATCH", "provider public key does not match pinned key", kid=ref.kid)
        return md

    def sign(self, ref: KeyRef, message: bytes, *, request_id: str | None = None) -> bytes:
        rid = request_id or str(uuid.uuid4())
        pin = self._pins.get(ref.kid)
        if pin is None:
            raise fail("KEY_MISMATCH", "no pinned public key for kid", kid=ref.kid)
        checked = self._policy_ok.get(ref.kid)
        if checked is None or self._clock() - checked > self.policy.policy_check_ttl_s:
            self.check_key_policy(ref)  # enabled / protection level / non-exportable / algorithm / pin
            self._policy_ok[ref.kid] = self._clock()
        sig = self._invoke(lambda: self._inner.sign(ref, message, request_id=rid), "sign", ref, rid)
        try:  # never release a signature the pinned key would not verify
            algs.verify_raw(ref.algorithm, pin, sig, message, profile=algs.PROFILE_REFERENCE)
        except GapError as exc:
            self._emit("custody.response_mismatch", ref, "sign", rid, exc.code)
            raise fail("KEY_MISMATCH", "provider signature does not verify under pinned key", kid=ref.kid) from exc
        self._emit("custody.sign", ref, "sign", rid, "ok")
        return sig

    def health(self, ref: KeyRef) -> dict[str, Any]:
        """Metadata-only probe: never consumes a signing operation."""
        try:
            self.check_key_policy(ref)
            return {"ok": True, "kid": ref.kid}
        except GapError as exc:
            return {"ok": False, "kid": ref.kid, "code": exc.code}
