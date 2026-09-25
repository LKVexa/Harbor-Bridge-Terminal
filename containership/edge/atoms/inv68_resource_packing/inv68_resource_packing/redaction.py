"""Secret-material detection and centralized redaction (INV-68 MC-11; C039, C075).

Carried from the owner's INV-64 v4.3.0 ``redaction.py`` (itself built for the
same Post-Kubernetes series). In INV-68 it guards configuration documents
(inline secrets are refused with ``SECRET_IN_CONFIG``), error messages,
structured logs, audit details and explain/support exports.

Two jobs, one pattern set:

* :func:`find_secrets` walks a decoded value and reports *where* credential
  material sits (never *what* it is). The config loader turns any hit
  into ``SECRET_IN_CONFIG``, so a configuration carrying a token is refused
  before it can be activated.
* :func:`redact` / :func:`redact_text` sanitise anything leaving the process:
  logs, audit details, diagnostics, decision records and support bundles.
  Export is allowlist-based (:func:`allowlisted`) — a field reaches an export
  only if its name is on the list, and even then its value is redacted.

Secret *references* are the only approved form: ``secretref://<provider>/<key>``
optionally suffixed ``@<version>``. The pure parser never resolves them.
"""
from __future__ import annotations

import base64
import functools
import binascii
import re
import unicodedata
from typing import Any, Iterable, Iterator, Mapping
from urllib.parse import unquote

REDACTED = "[REDACTED]"
MAX_WALK_NODES = 200_000
MAX_SCAN_CHARS = 16_384
MIN_SECRET_LEN = 6  # shortest pattern hit is "pwd=xx"; shorter strings cannot match

SECRET_REF_RE = re.compile(r"^secretref://[a-z0-9][a-z0-9-]{0,62}/[A-Za-z0-9._/-]{1,256}(?:@[A-Za-z0-9._-]{1,64})?$")

# Field names that may only carry a secret reference. Compared after NFKC,
# casefold and removal of separators, so ``Pass_Word`` and ``ｐａｓｓｗｏｒｄ`` match.
SENSITIVE_KEYS = frozenset({
    "password", "passwd", "pwd", "secret", "clientsecret", "token", "accesstoken",
    "refreshtoken", "apikey", "apitoken", "privatekey", "secretkey", "accesskey",
    "awssecretaccesskey", "credential", "credentials", "connectionstring", "authorization",
    "bearer", "sessiontoken", "sastoken", "passphrase", "mackey", "signingkey",
})

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("pem-private-key", re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")),
    ("aws-access-key-id", re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}(?![0-9A-Z])")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}")),
    ("url-credentials", re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]+@")),
    ("conn-string-password", re.compile(r"(?i)(?:^|[;\s])(?:password|pwd)\s*=\s*[^;\s]+")),
    ("signed-url", re.compile(r"(?i)[?&](?:x-amz-signature|sig|signature|x-goog-signature)=[A-Za-z0-9%/+=_-]{16,}")),
    ("azure-account-key", re.compile(r"(?i)accountkey=[A-Za-z0-9+/=]{40,}")),
    ("generic-api-key", re.compile(r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}\b")),
)
_ANY = re.compile("|".join(f"(?i:{p.pattern[4:]})" if p.pattern.startswith("(?i)") else f"(?:{p.pattern})"
                           for _, p in _PATTERNS))
_B64_RE = re.compile(r"^[A-Za-z0-9+/_-]{24,}={0,2}$")


@functools.lru_cache(maxsize=8192)
def _norm_key_cached(key: str) -> str:
    return re.sub(r"[\s_.\-]", "", unicodedata.normalize("NFKC", key).casefold())


def normalize_key(key: str) -> str:
    if isinstance(key, str):
        return _norm_key_cached(key)
    return re.sub(r"[\s_.\-]", "", unicodedata.normalize("NFKC", str(key)).casefold())


_SENSITIVE_SUFFIXES = ("password", "passwd", "secret", "token", "apikey", "privatekey", "secretkey",
                       "accesskey", "credential", "credentials", "passphrase", "connectionstring")


@functools.lru_cache(maxsize=8192)
def _sensitive_cached(key: str) -> bool:
    k = normalize_key(key)
    if k in ("tokenttl", "tokenlifetime"):
        return False
    return k == "secretref" or k in SENSITIVE_KEYS or k.endswith(_SENSITIVE_SUFFIXES)


def is_sensitive_key(key: Any) -> bool:
    k = normalize_key(key)
    if k in ("secretref", "tokenttl", "tokenlifetime"):
        return False
    return k in SENSITIVE_KEYS or k.endswith(_SENSITIVE_SUFFIXES)


def is_secret_ref(value: Any) -> bool:
    return isinstance(value, str) and bool(SECRET_REF_RE.fullmatch(value))


def _variants(text: str) -> Iterator[str]:
    text = text[:MAX_SCAN_CHARS]
    norm = text if text.isascii() else unicodedata.normalize("NFKC", text)
    yield norm
    if "%" in norm:
        yield unquote(norm)
    stripped = norm.strip()
    if _B64_RE.fullmatch(stripped):
        try:
            raw = base64.b64decode(stripped + "=" * (-len(stripped) % 4), altchars=b"-_" if ("-" in stripped or "_" in stripped) else None)
            dec = raw.decode("utf-8")
            if dec.isprintable() or "\n" in dec:
                yield dec
        except (binascii.Error, ValueError, UnicodeDecodeError):
            pass


def classify_text(text: str) -> str | None:
    """Return the matching pattern class for credential-like text, else None."""
    if not isinstance(text, str) or len(text) < MIN_SECRET_LEN or is_secret_ref(text):
        return None
    for variant in _variants(text):
        if _ANY.search(variant):  # one combined scan; name the class only on a hit
            for name, pat in _PATTERNS:
                if pat.search(variant):
                    return name
    return None


def _join(path: str, key: Any) -> str:
    if isinstance(key, int):
        return f"{path}[{key}]"
    return f"{path}.{key}" if path else str(key)


def find_secrets(value: Any, path: str = "") -> list[tuple[str, str]]:
    """Return ``[(path, reason)]`` for inline secrets. Iterative and bounded."""
    hits: list[tuple[str, str]] = []
    stack: list[tuple[str, Any, bool]] = [(path, value, False)]
    seen = 0
    while stack:
        p, v, sensitive = stack.pop()
        seen += 1
        if seen > MAX_WALK_NODES:
            hits.append((p, "walk-limit"))
            break
        if isinstance(v, dict) or (not isinstance(v, (str, list, int, float)) and isinstance(v, Mapping)):
            for k, child in v.items():
                ks = _sensitive_cached(k) if isinstance(k, str) else is_sensitive_key(k)
                stack.append((_join(p, k), child, sensitive or ks))
        elif isinstance(v, list):
            for i, child in enumerate(v):
                stack.append((_join(p, i), child, sensitive))
        elif isinstance(v, str):
            if sensitive and not is_secret_ref(v):
                hits.append((p, "sensitive-field-not-secretref"))
                continue
            cls = classify_text(v)
            if cls:
                hits.append((p, cls))
        elif sensitive and v is not None and not isinstance(v, bool):
            hits.append((p, "sensitive-field-not-secretref"))
    hits.sort()
    return hits


def redact_text(text: str) -> str:
    if not isinstance(text, str):
        return text
    if classify_text(text):
        out = unicodedata.normalize("NFKC", text)
        for _, pat in _PATTERNS:
            out = pat.sub(REDACTED, out)
        # if a decoded variant matched but the surface form did not, drop the whole value
        return out if not classify_text(out) else REDACTED
    return text


def redact(value: Any, *, _depth: int = 0) -> Any:
    """Deep-copy ``value`` with sensitive keys and credential-like strings redacted."""
    if _depth > 64:
        return REDACTED
    if isinstance(value, Mapping):
        out = {}
        for k, v in value.items():
            if is_sensitive_key(k) and not is_secret_ref(v):
                out[str(k)] = REDACTED
            else:
                out[str(k)] = redact(v, _depth=_depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [redact(v, _depth=_depth + 1) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, BaseException):
        return f"{type(value).__name__}: {redact_text(str(value))}"
    return value


def allowlisted(record: Mapping[str, Any], allow: Iterable[str]) -> dict:
    """Export only allowlisted fields, each redacted (MC-11 allowlist export)."""
    allowed = set(allow)
    return {k: redact(v) for k, v in record.items() if k in allowed}
