"""Typed HTTP protocol model (checklist component 4).

No security or routing decision in INV-20 consumes a raw authority/header string: callers
build ``Request``/``Response`` objects, whose constructors validate every part, and the
single ``parse_authority`` routine is shared by the policy layer (``egress.py``) and any
transport adapter.

Field semantics follow RFC 9110 section 5: names are ``token`` characters and are
compared case-insensitively (stored lower-case, as the wasi:http ``fields`` resource does);
values may not contain CR, LF or NUL, and leading/trailing whitespace is rejected rather
than silently trimmed so that the reviewed value is the transmitted value.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import ipaddress
import re
from typing import Iterable, List, Optional, Tuple

from .errors import Inv20Error
from .runtime import BodyStream, Completion, canonical_host, InvalidHost

TOKEN_RE = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
_VALUE_BAD = re.compile(r"[\x00-\x08\x0a-\x1f\x7f]")
_PCT_RE = re.compile(r"%(?![0-9A-Fa-f]{2})")
_PATH_OK = re.compile(r"^[A-Za-z0-9\-._~!$&'()*+,;=:@/%?]*$")

STANDARD_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "DELETE", "CONNECT", "OPTIONS", "TRACE", "PATCH"})
IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "PUT", "DELETE", "OPTIONS", "TRACE"})
SUPPORTED_SCHEMES = {"http": 80, "https": 443}

# RFC 9110 7.6.1 connection-specific fields plus fields the component boundary owns.
HOP_BY_HOP = frozenset({"connection", "keep-alive", "proxy-connection", "transfer-encoding",
                        "upgrade", "te", "trailer", "proxy-authenticate", "proxy-authorization"})
# Fields that must never arrive via trailers (RFC 9110 6.5.1): framing, routing, auth, control.
FORBIDDEN_IN_TRAILERS = HOP_BY_HOP | frozenset({
    "host", "content-length", "content-type", "content-encoding", "content-range",
    "authorization", "cookie", "set-cookie", "www-authenticate", "cache-control",
    "expect", "max-forwards", "pragma", "range", "age", "expires", "date", "location",
    "retry-after", "vary", "warning", "x-forwarded-for", "forwarded"})


class InvalidField(Inv20Error):
    code = "E_INVALID_FIELD"


class ForbiddenField(Inv20Error):
    code = "E_FORBIDDEN_FIELD"


class FieldLimit(Inv20Error):
    code = "E_FIELD_LIMIT"


class InvalidMethod(Inv20Error):
    code = "E_INVALID_METHOD"


class InvalidScheme(Inv20Error):
    code = "E_INVALID_SCHEME"


class InvalidAuthority(Inv20Error):
    code = "E_INVALID_AUTHORITY"


class InvalidPath(Inv20Error):
    code = "E_INVALID_PATH"


class InvalidStatus(Inv20Error):
    code = "E_INVALID_STATUS"


@dataclass(frozen=True)
class FieldLimits:
    max_fields: int = 100
    max_total_bytes: int = 16 * 1024
    max_name_bytes: int = 256
    max_value_bytes: int = 8 * 1024
    max_trailer_fields: int = 16
    max_trailer_bytes: int = 4 * 1024


DEFAULT_LIMITS = FieldLimits()


def validate_method(method: str) -> str:
    if not isinstance(method, str) or not TOKEN_RE.fullmatch(method) or len(method) > 32:
        raise InvalidMethod(method)
    # Methods are case-sensitive (RFC 9110 9.1); a lower-case "get" is an extension method,
    # but we refuse case-variants of standard methods as a confusion hazard.
    if method.upper() in STANDARD_METHODS and method != method.upper():
        raise InvalidMethod(f"ambiguous case variant {method}")
    return method


def validate_scheme(scheme: str) -> str:
    if scheme not in SUPPORTED_SCHEMES:
        raise InvalidScheme(scheme)
    return scheme


@dataclass(frozen=True)
class Authority:
    host: str               # canonical host (lower-case name or compressed IP literal)
    port: int
    is_ip: bool

    def render(self) -> str:
        h = f"[{self.host}]" if ":" in self.host else self.host
        return f"{h}:{self.port}"


def parse_authority(raw: str, scheme: str = "https", allowed_ports: Optional[Iterable[int]] = None) -> Authority:
    """The one authority parser. Rejects userinfo, zone IDs, bad ports, and ambiguous forms."""
    validate_scheme(scheme)
    if not isinstance(raw, str) or not raw or raw != raw.strip():
        raise InvalidAuthority(raw)
    if "@" in raw:
        raise InvalidAuthority("userinfo is prohibited")
    if any(c in raw for c in "/?#\\ \t"):
        raise InvalidAuthority(raw)
    port: Optional[int] = None
    if raw.startswith("["):
        end = raw.find("]")
        if end < 0:
            raise InvalidAuthority(raw)
        host_part, rest = raw[1:end], raw[end + 1:]
        if "%" in host_part:
            raise InvalidAuthority("IPv6 zone identifiers are prohibited")
        try:
            ip = ipaddress.IPv6Address(host_part)
        except ValueError:
            raise InvalidAuthority(raw) from None
        host = ip.compressed
        if rest:
            if not rest.startswith(":"):
                raise InvalidAuthority(raw)
            port = _port(rest[1:])
    else:
        if raw.count(":") > 1:
            raise InvalidAuthority("unbracketed IPv6 in authority")
        host_part, _, port_s = raw.partition(":")
        if _:
            port = _port(port_s)
        try:
            host = canonical_host(host_part)
        except InvalidHost:
            raise InvalidAuthority(raw) from None
    if port is None:
        port = SUPPORTED_SCHEMES[scheme]
    if allowed_ports is not None and port not in set(allowed_ports):
        raise InvalidAuthority(f"port {port} not allowed")
    is_ip = True
    try:
        ipaddress.ip_address(host)
    except ValueError:
        is_ip = False
    return Authority(host, port, is_ip)


def _port(s: str) -> int:
    if not s.isdigit() or len(s) > 5 or (len(s) > 1 and s[0] == "0"):
        raise InvalidAuthority(f"bad port {s!r}")
    p = int(s)
    if not 1 <= p <= 65535:
        raise InvalidAuthority(f"bad port {s!r}")
    return p


def validate_path_with_query(pq: str) -> str:
    """Accept origin-form only; preserve bytes exactly (no decode/re-encode)."""
    if not isinstance(pq, str) or not pq.startswith("/") or pq.startswith("//"):
        raise InvalidPath(pq)
    if len(pq) > 8192 or not _PATH_OK.fullmatch(pq) or _PCT_RE.search(pq):
        raise InvalidPath(pq)
    if "#" in pq:
        raise InvalidPath("fragment not allowed")
    return pq


class Fields:
    """Validated, ordered, multi-valued field collection (wasi:http ``fields`` analogue)."""

    def __init__(self, entries: Iterable[Tuple[str, str]] = (), *, limits: FieldLimits = DEFAULT_LIMITS,
                 trailers: bool = False, boundary: str = "component") -> None:
        self._entries: List[Tuple[str, str]] = []
        self._bytes = 0
        self.limits = limits
        self.trailers = trailers
        self.boundary = boundary
        for name, value in entries:
            self.append(name, value)

    def append(self, name: str, value: str) -> None:
        if isinstance(name, str) and name.startswith(":"):
            raise ForbiddenField("pseudo-headers are owned by the binding layer")
        if not isinstance(name, str) or not TOKEN_RE.fullmatch(name):
            raise InvalidField(f"name {name!r}")
        if not isinstance(value, str):
            raise InvalidField("value must be str")
        if _VALUE_BAD.search(value) or value != value.strip(" \t"):
            raise InvalidField(f"value for {name}")
        try:
            value.encode("ascii")
        except UnicodeEncodeError:
            raise InvalidField(f"non-ASCII value for {name}") from None
        lname = name.lower()
        if lname.startswith(":"):
            raise ForbiddenField("pseudo-headers are owned by the binding layer")
        if lname in HOP_BY_HOP and self.boundary == "component":
            raise ForbiddenField(f"hop-by-hop field {lname}")
        if self.trailers and lname in FORBIDDEN_IN_TRAILERS:
            raise ForbiddenField(f"{lname} is not permitted in trailers")
        lim = self.limits
        nb, vb = len(lname), len(value)
        if nb > lim.max_name_bytes or vb > lim.max_value_bytes:
            raise FieldLimit(f"field {lname} too large")
        max_n = lim.max_trailer_fields if self.trailers else lim.max_fields
        max_b = lim.max_trailer_bytes if self.trailers else lim.max_total_bytes
        if len(self._entries) + 1 > max_n or self._bytes + nb + vb > max_b:
            raise FieldLimit("field count/bytes limit")
        self._entries.append((lname, value))
        self._bytes += nb + vb

    def get_all(self, name: str) -> List[str]:
        n = name.lower()
        return [v for k, v in self._entries if k == n]

    def get(self, name: str) -> Optional[str]:
        """Single-valued read. Duplicates of a singleton are an ambiguity and are rejected."""
        vals = self.get_all(name)
        if len(vals) > 1:
            raise InvalidField(f"duplicate singleton field {name.lower()}")
        return vals[0] if vals else None

    def names(self) -> List[str]:
        return [k for k, _ in self._entries]

    def items(self) -> List[Tuple[str, str]]:
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def byte_size(self) -> int:
        return self._bytes


def validate_trailers(trailers: Fields, reviewed_headers: Fields) -> Fields:
    """Prevent trailer smuggling: trailers must be trailer-mode and may not shadow reviewed headers."""
    if not trailers.trailers:
        raise ForbiddenField("trailers must be constructed in trailer mode")
    for name in trailers.names():
        if name in reviewed_headers.names():
            raise ForbiddenField(f"trailer {name} shadows a reviewed header")
    return trailers


@dataclass
class Request:
    method: str
    scheme: str
    authority: Authority
    path_with_query: str
    headers: Fields = field(default_factory=Fields)
    body: BodyStream = field(default_factory=BodyStream)
    trailers: Completion = field(default_factory=Completion)

    def __post_init__(self) -> None:
        validate_method(self.method)
        validate_scheme(self.scheme)
        if not isinstance(self.authority, Authority):
            raise InvalidAuthority("authority must be parsed with parse_authority")
        validate_path_with_query(self.path_with_query)
        host_hdr = self.headers.get("host")
        if host_hdr is not None:
            if parse_authority(host_hdr, self.scheme) != self.authority:
                raise InvalidAuthority("Host header does not match request authority")

    @classmethod
    def build(cls, method: str, url_scheme: str, authority: str, path: str = "/",
              headers: Iterable[Tuple[str, str]] = (), *, limits: FieldLimits = DEFAULT_LIMITS,
              body_limit: int = 1 << 20) -> "Request":
        return cls(method, url_scheme, parse_authority(authority, url_scheme), path,
                   Fields(headers, limits=limits), BodyStream(limit=body_limit))

    @property
    def idempotent(self) -> bool:
        return self.method in IDEMPOTENT_METHODS


@dataclass
class Response:
    status: int
    headers: Fields = field(default_factory=Fields)
    body: BodyStream = field(default_factory=BodyStream)
    trailers: Completion = field(default_factory=Completion)

    def __post_init__(self) -> None:
        if isinstance(self.status, bool) or not isinstance(self.status, int) or not 100 <= self.status <= 599:
            raise InvalidStatus(self.status)

    @property
    def status_class(self) -> str:
        return f"{self.status // 100}xx"
