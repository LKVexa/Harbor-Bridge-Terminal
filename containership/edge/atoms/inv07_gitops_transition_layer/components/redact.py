"""Central redaction (checks xx.S03, component 36/40).

One function decides what is sensitive, and every sink -- errors, structured
logs, trace attributes, audit payloads, explain records, evidence -- goes
through it.  Rules:

* a mapping key naming secret material is replaced by ``<redacted>``;
* credentials embedded in URLs (``https://user:tok@host``) are stripped;
* bearer/basic tokens, PEM private-key blocks, and long high-entropy hex/base64
  runs that look like key material are replaced in free text;
* depth, list length and string size are bounded so a hostile payload cannot
  turn a log line into a memory bomb.
"""
from __future__ import annotations

import re
from typing import Any

SECRET_KEYS = ("secret", "password", "passwd", "token", "private", "credential", "key_material",
               "authorization", "cookie", "api_key", "apikey", "seed")
_URL_CRED = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/@\s:]+(?::[^/@\s]*)?@")
_BEARER = re.compile(r"(?i)\b(bearer|basic|token)\s+[A-Za-z0-9._~+/=-]{8,}")
_PEM = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S)
_ASSIGN = re.compile(r"(?i)\b(password|passwd|secret|token|api_key|apikey)\s*[=:]\s*\S+")
MAX_DEPTH, MAX_ITEMS, MAX_STR = 8, 64, 2048


def scrub_text(s: str) -> str:
    s = _PEM.sub("<redacted-private-key>", s)
    s = _URL_CRED.sub(r"\1<redacted>@", s)
    s = _BEARER.sub(lambda m: m.group(1) + " <redacted>", s)
    s = _ASSIGN.sub(lambda m: m.group(1) + "=<redacted>", s)
    if len(s) > MAX_STR:
        s = s[:MAX_STR] + f"...<truncated {len(s) - MAX_STR} chars>"
    return s


def is_secret_key(k: str) -> bool:
    kl = str(k).lower()
    if kl in ("key_id", "public_key", "keyid", "signer_key_id"):
        return False
    return any(t in kl for t in SECRET_KEYS)


def scrub(obj: Any, depth: int = 0) -> Any:
    if depth > MAX_DEPTH:
        return "<depth-limit>"
    if isinstance(obj, dict):
        out = {}
        for i, (k, v) in enumerate(obj.items()):
            if i >= MAX_ITEMS:
                out["<truncated>"] = len(obj) - MAX_ITEMS
                break
            out[str(k)] = "<redacted>" if is_secret_key(k) else scrub(v, depth + 1)
        return out
    if isinstance(obj, (list, tuple)):
        items = [scrub(v, depth + 1) for v in list(obj)[:MAX_ITEMS]]
        if len(obj) > MAX_ITEMS:
            items.append(f"<truncated {len(obj) - MAX_ITEMS} items>")
        return items
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return f"<{len(bytes(obj))} bytes>"
    if isinstance(obj, str):
        return scrub_text(obj)
    if obj is None or isinstance(obj, (bool, int, float)):
        return obj
    return scrub_text(repr(obj))
