"""Identity, authentication, authorization, secrets and transport security
(MC-021, MC-022, MC-023, MC-024, MC-025).

Identity model (MC-022-01): every caller is a :class:`Principal` whose identity
is a SPIFFE-style URI ``spiffe://<trust-domain>/tenant/<t>/env/<e>/site/<s>/wl/<w>/<name>``.
Two authenticators are provided:

* :class:`MTLSAuthenticator` -- production path.  Validates the peer
  certificate presented on a mutually-authenticated TLS connection (chain is
  verified by the TLS stack against the pinned trust bundle; this class then
  enforces URI SAN, trust domain, validity window, revocation list and the
  extended-key-usage *purpose*) (MC-022-02/03/06).
* :class:`TokenAuthenticator` -- HMAC-SHA256 signed bearer tokens for
  loopback/test and break-glass use; audience- and expiry-checked, key-rotated.

Authorization (MC-023) is deny-by-default: a request is allowed only if some
rule of the *active, versioned* policy matches subject roles, action and the
namespace the principal is bound to.  Policy rollout is atomic with rollback.
"""
from __future__ import annotations

import base64
import fnmatch
import hashlib
import hmac
import json
import os
import re
import ssl
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

from .errors import InvalidArgument, PermissionDenied, Unauthenticated

ACTIONS = frozenset({
    "read", "write", "delete", "watch", "lease", "compact",           # data plane
    "admin.freeze", "admin.drain", "admin.quarantine", "admin.maintenance",
    "admin.break_glass", "admin.config", "admin.policy", "admin.backup", "admin.restore",
    "admin.explain", "admin.audit_read", "admin.diagnostics", "admin.loglevel", "replicate",
})

_SEG = r"[A-Za-z0-9][A-Za-z0-9_.-]{0,62}"
SPIFFE_RE = re.compile(rf"^spiffe://(?P<td>{_SEG})/tenant/(?P<tenant>{_SEG})/env/(?P<env>{_SEG})"
                       rf"/site/(?P<site>{_SEG})/wl/(?P<wl>{_SEG})/(?P<name>{_SEG})$")


@dataclass(frozen=True)
class Namespace:
    """Canonical tenant/environment/site/workload namespace (MC-021-01)."""
    tenant: str
    env: str
    site: str
    workload: str

    def __post_init__(self) -> None:
        for part in (self.tenant, self.env, self.site, self.workload):
            if not re.fullmatch(_SEG, part or ""):
                raise InvalidArgument("invalid namespace segment", field="namespace")

    @property
    def prefix(self) -> str:
        return f"/t/{self.tenant}/e/{self.env}/s/{self.site}/w/{self.workload}/"

    def label(self) -> str:
        return f"{self.tenant}/{self.env}/{self.site}/{self.workload}"


@dataclass(frozen=True)
class Principal:
    subject: str
    namespace: Namespace
    roles: frozenset[str]
    purpose: str = "client"
    expires_at: float = 0.0
    auth_method: str = "mtls"

    @property
    def subject_hash(self) -> str:
        """Pseudonymous subject for telemetry (MC-036)."""
        return hashlib.sha256(self.subject.encode()).hexdigest()[:16]


#: Cluster-scoped administrative namespace (compaction, metrics, diagnostics).
CLUSTER = Namespace("cluster", "global", "global", "global")

# --------------------------------------------------------------------------- authn

class MTLSAuthenticator:
    """Validate ``ssl.SSLSocket.getpeercert()`` dicts (MC-022)."""

    def __init__(self, trust_domain: str, *, role_map: Mapping[str, Iterable[str]],
                 revoked_serials: Iterable[str] = (), required_purpose: str = "client",
                 clock: Callable[[], float] = time.time) -> None:
        self.trust_domain = trust_domain
        self.role_map = {k: frozenset(v) for k, v in role_map.items()}
        self._revoked = set(revoked_serials)
        self.required_purpose = required_purpose
        self.clock = clock
        self._lock = threading.Lock()

    def revoke(self, serial: str) -> None:
        with self._lock:
            self._revoked.add(serial.upper())

    def authenticate(self, cert: Mapping[str, Any] | None) -> Principal:
        if not cert:
            raise Unauthenticated("client certificate required")
        serial = str(cert.get("serialNumber", "")).upper()
        with self._lock:
            if serial in self._revoked:
                raise Unauthenticated("certificate revoked")
        now = self.clock()
        try:
            nb = ssl.cert_time_to_seconds(cert["notBefore"])
            na = ssl.cert_time_to_seconds(cert["notAfter"])
        except (KeyError, ValueError):
            raise Unauthenticated("certificate validity unreadable") from None
        if not (nb <= now <= na):
            raise Unauthenticated("certificate outside validity window")
        uris = [v for (k, v) in cert.get("subjectAltName", ()) if k == "URI"]
        if len(uris) != 1:
            raise Unauthenticated("exactly one URI SAN required")
        m = SPIFFE_RE.match(uris[0])
        if not m or m["td"] != self.trust_domain:
            raise Unauthenticated("identity not in trusted domain")
        purpose = "peer" if m["name"].startswith("peer-") else ("admin" if m["name"].startswith("admin-") else "client")
        if self.required_purpose != "any" and purpose != self.required_purpose and not (
                self.required_purpose == "client" and purpose == "admin"):
            raise Unauthenticated("certificate purpose not accepted on this listener")
        ns = Namespace(m["tenant"], m["env"], m["site"], m["wl"])
        roles = self.role_map.get(uris[0]) or self.role_map.get(purpose, frozenset())
        return Principal(uris[0], ns, frozenset(roles), purpose, na, "mtls")


class TokenAuthenticator:
    """HMAC-signed bearer tokens with key ids for rotation (MC-022-04, MC-024-04)."""

    def __init__(self, keys: Mapping[str, bytes], active: str, audience: str = "inv05",
                 clock: Callable[[], float] = time.time, max_ttl_s: int = 3600) -> None:
        if active not in keys:
            raise InvalidArgument("active key missing", field="active")
        self.keys, self.active, self.audience, self.clock, self.max_ttl_s = dict(keys), active, audience, clock, max_ttl_s

    def issue(self, subject: str, ns: Namespace, roles: Iterable[str], ttl_s: int = 600, purpose: str = "client") -> str:
        ttl_s = min(ttl_s, self.max_ttl_s)
        body = {"sub": subject, "ns": [ns.tenant, ns.env, ns.site, ns.workload], "roles": sorted(roles),
                "aud": self.audience, "exp": int(self.clock()) + ttl_s, "pur": purpose, "kid": self.active,
                "nonce": base64.urlsafe_b64encode(os.urandom(9)).decode()}
        raw = base64.urlsafe_b64encode(json.dumps(body, sort_keys=True).encode()).decode()
        sig = hmac.new(self.keys[self.active], raw.encode(), hashlib.sha256).hexdigest()
        return f"{raw}.{sig}"

    def authenticate(self, token: str | None) -> Principal:
        if not token or token.count(".") != 1:
            raise Unauthenticated("bearer token required")
        raw, sig = token.split(".")
        try:
            body = json.loads(base64.urlsafe_b64decode(raw.encode()))
            key = self.keys[body["kid"]]
        except Exception:
            raise Unauthenticated("malformed token") from None
        if not hmac.compare_digest(hmac.new(key, raw.encode(), hashlib.sha256).hexdigest(), sig):
            raise Unauthenticated("bad token signature")
        if body.get("aud") != self.audience or int(body.get("exp", 0)) < self.clock():
            raise Unauthenticated("token expired or wrong audience")
        try:
            ns = Namespace(*body["ns"])
        except Exception:
            raise Unauthenticated("token namespace invalid") from None
        return Principal(str(body["sub"]), ns, frozenset(body.get("roles", ())), body.get("pur", "client"),
                         float(body["exp"]), "token")


# --------------------------------------------------------------------------- authz

@dataclass(frozen=True)
class Rule:
    roles: frozenset[str]
    actions: frozenset[str]
    namespaces: tuple[str, ...] = ("{self}",)   # glob over Namespace.label(); {self} = principal's own
    key_prefixes: tuple[str, ...] = ("",)


@dataclass(frozen=True)
class Policy:
    version: str
    rules: tuple[Rule, ...]

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Policy":
        if not isinstance(d.get("version"), str) or not d["version"]:
            raise InvalidArgument("policy.version required", field="policy.version")
        rules = []
        for r in d.get("rules", []):
            acts = frozenset(r["actions"])
            unknown = acts - ACTIONS - {"*"}
            if unknown:
                raise InvalidArgument(f"unknown actions {sorted(unknown)}", field="policy.rules")
            rules.append(Rule(frozenset(r["roles"]), ACTIONS if "*" in acts else acts,
                              tuple(r.get("namespaces", ["{self}"])), tuple(r.get("key_prefixes", [""]))))
        return cls(d["version"], tuple(rules))


@dataclass(frozen=True)
class Decision:
    allowed: bool
    action: str
    subject_hash: str
    namespace: str
    policy_version: str
    rule_index: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


DEFAULT_POLICY = Policy.from_dict({"version": "builtin-1", "rules": [
    {"roles": ["reader"], "actions": ["read", "watch"]},
    {"roles": ["writer"], "actions": ["read", "watch", "write", "delete", "lease"]},
    {"roles": ["operator"], "actions": ["compact", "admin.freeze", "admin.drain", "admin.maintenance",
                                        "admin.explain", "admin.diagnostics", "admin.backup", "admin.loglevel"],
     "namespaces": ["*"]},
    {"roles": ["security-admin"], "actions": ["admin.policy", "admin.audit_read", "admin.quarantine",
                                              "admin.break_glass", "admin.config", "admin.restore"],
     "namespaces": ["*"]},
    {"roles": ["replicator"], "actions": ["replicate", "read", "watch"], "namespaces": ["*"]},
]})


class Authorizer:
    """Deny-by-default policy evaluation with atomic rollout/rollback (MC-023)."""

    def __init__(self, policy: Policy = DEFAULT_POLICY, on_decision: Callable[[Decision], None] | None = None) -> None:
        self._policy = policy
        self._previous: Policy | None = None
        self._lock = threading.Lock()
        self.on_decision = on_decision

    @property
    def policy(self) -> Policy:
        return self._policy

    def rollout(self, policy: Policy) -> str:
        with self._lock:
            self._previous, self._policy = self._policy, policy
            return policy.version

    def rollback(self) -> str:
        with self._lock:
            if self._previous is None:
                raise InvalidArgument("no previous policy to roll back to", field="policy")
            self._policy, self._previous = self._previous, None
            return self._policy.version

    def decide(self, p: Principal, action: str, target_ns: Namespace | None = None, key: str = "") -> Decision:
        policy = self._policy
        target = target_ns or p.namespace
        label = target.label()
        allowed, idx, reason = False, -1, "no matching rule (deny by default)"
        if action not in ACTIONS:
            reason = "unknown action"
        else:
            for i, r in enumerate(policy.rules):
                if action not in r.actions or not (p.roles & r.roles):
                    continue
                ns_ok = any((pat == "{self}" and target == p.namespace) or
                            (pat != "{self}" and fnmatch.fnmatchcase(label, pat)) for pat in r.namespaces)
                if not ns_ok:
                    continue
                if not any(key.startswith(kp) for kp in r.key_prefixes):
                    continue
                allowed, idx, reason = True, i, "rule matched"
                break
        d = Decision(allowed, action, p.subject_hash, label, policy.version, idx, reason)
        if self.on_decision:
            self.on_decision(d)
        return d

    def require(self, p: Principal, action: str, target_ns: Namespace | None = None, key: str = "") -> Decision:
        d = self.decide(p, action, target_ns, key)
        if not d.allowed:
            raise PermissionDenied(f"{action} denied", reason="policy")
        return d


# --------------------------------------------------------------------------- secrets

SENSITIVE_KEY_RE = re.compile(r"(pass(word)?|secret|token|key|credential|authorization|cookie|private)", re.I)
REDACTED = "[REDACTED]"


def redact(obj: Any, _depth: int = 0) -> Any:
    """Central redaction used by logs, traces, explain records and errors (MC-024-06, MC-033-04)."""
    if _depth > 8:
        return "[TRUNCATED]"
    if isinstance(obj, Mapping):
        return {k: (REDACTED if isinstance(k, str) and SENSITIVE_KEY_RE.search(k) else redact(v, _depth + 1))
                for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact(v, _depth + 1) for v in obj[:100]]
    if isinstance(obj, str) and obj.count(".") == 1 and len(obj) > 80:  # looks like a bearer token
        return REDACTED
    return obj


class SecretProvider:
    """Resolve ``secret://<name>`` references from files or env (MC-024-02).

    Production deployments point ``secret_dir`` at a KMS/CSI-mounted tmpfs; the
    values are never placed in configuration, logs or exceptions.
    """

    def __init__(self, secret_dir: str | None = None, env_prefix: str = "INV05_SECRET_") -> None:
        self.secret_dir, self.env_prefix = secret_dir, env_prefix

    def get(self, ref: str) -> bytes:
        if not ref.startswith("secret://"):
            raise InvalidArgument("not a secret reference", field="secret")
        name = ref[9:]
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", name):
            raise InvalidArgument("invalid secret name", field="secret")
        if self.secret_dir:
            path = os.path.join(self.secret_dir, name)
            if os.path.exists(path):
                st = os.stat(path)
                if st.st_mode & 0o077:
                    raise InvalidArgument("secret file permissions too open", field="secret")
                with open(path, "rb") as fh:
                    return fh.read().strip()
        val = os.environ.get(self.env_prefix + name.upper().replace(".", "_").replace("-", "_"))
        if val is None:
            raise InvalidArgument("secret not available", field="secret")
        return val.encode()


def derive_key(material: bytes, purpose: str) -> bytes:
    """HKDF-like purpose separation (single block) for data/audit/backup keys."""
    prk = hmac.new(b"inv05-kdf-v1", material, hashlib.sha256).digest()
    return hmac.new(prk, purpose.encode() + b"\x01", hashlib.sha256).digest()


# --------------------------------------------------------------------------- TLS

MIN_TLS = ssl.TLSVersion.TLSv1_2
APPROVED_CIPHERS_TLS12 = "ECDHE+AESGCM:ECDHE+CHACHA20"


def server_tls_context(cert_file: str, key_file: str, ca_file: str, *, require_client_cert: bool = True) -> ssl.SSLContext:
    """mTLS server context: TLS>=1.2 (1.3 preferred), AEAD-only suites, client certs required (MC-025-01/02)."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = MIN_TLS
    ctx.set_ciphers(APPROVED_CIPHERS_TLS12)
    ctx.options |= ssl.OP_NO_COMPRESSION | ssl.OP_NO_RENEGOTIATION
    ctx.load_cert_chain(cert_file, key_file)
    ctx.load_verify_locations(ca_file)
    ctx.verify_mode = ssl.CERT_REQUIRED if require_client_cert else ssl.CERT_OPTIONAL
    return ctx


def client_tls_context(ca_file: str, cert_file: str | None = None, key_file: str | None = None) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)  # check_hostname + CERT_REQUIRED by default
    ctx.minimum_version = MIN_TLS
    ctx.set_ciphers(APPROVED_CIPHERS_TLS12)
    ctx.load_verify_locations(ca_file)
    if cert_file:
        ctx.load_cert_chain(cert_file, key_file)
    return ctx


def check_tls_context(ctx: ssl.SSLContext, *, server: bool) -> list[str]:
    """Runtime verification of encryption configuration (MC-025-05)."""
    problems = []
    if ctx.minimum_version < MIN_TLS:
        problems.append("minimum TLS version below 1.2")
    if server and ctx.verify_mode != ssl.CERT_REQUIRED:
        problems.append("server does not require client certificates")
    if not server and (not ctx.check_hostname or ctx.verify_mode != ssl.CERT_REQUIRED):
        problems.append("client hostname/certificate verification disabled")
    for c in ctx.get_ciphers():
        if "GCM" not in c["name"] and "CHACHA20" not in c["name"]:
            problems.append(f"non-AEAD cipher enabled: {c['name']}")
    return problems
