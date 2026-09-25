"""Waiver register rules (G12-I115, G12-I116-02): a waiver counts only when it is
signed by a registered approver, names owner/scope/rationale/compensating control,
and is unexpired.  Expiry is automatic: an expired waiver fails the gate."""
from __future__ import annotations

import hashlib
import hmac
import json

REQUIRED = ("id", "item", "owner", "scope", "rationale", "compensating_control", "expires", "approver")


def _body(w: dict) -> bytes:
    return json.dumps({k: v for k, v in w.items() if k != "sig"}, sort_keys=True, separators=(",", ":")).encode()


def sign(w: dict, key: bytes) -> dict:
    return {**w, "sig": hmac.new(key, _body(w), hashlib.sha256).hexdigest()}


def valid(w: dict, approver_keys: dict[str, bytes], *, now: float) -> tuple[bool, str]:
    key = approver_keys.get(w.get("approver"))
    if key is None:
        return False, "unknown approver"
    if not hmac.compare_digest(hmac.new(key, _body(w), hashlib.sha256).hexdigest(), w.get("sig", "")):
        return False, "bad signature"
    if any(not w.get(k) for k in REQUIRED):
        return False, "missing fields"
    if now >= float(w["expires"]):
        return False, "expired"
    return True, "OK"
