"""Minimal signed-request client helper for callers and tests."""
from __future__ import annotations

import json
import secrets
import socket
import time
from typing import Any

from .security import sign_request


def make_request(caller: str, key: bytes, op: str, args: dict | None = None, *,
                 request_id: str | None = None, ts: float | None = None,
                 nonce: str | None = None) -> dict:
    req: dict[str, Any] = {"schema": "PK_NODE_LIFECYCLE/1", "caller": caller,
                           "request_id": request_id or secrets.token_hex(8),
                           "nonce": nonce or secrets.token_hex(12),
                           "ts": time.time() if ts is None else ts, "op": op, "args": args or {}}
    req["sig"] = sign_request(req, key)
    return req


def call(sock_path: str, req: dict, timeout: float = 10) -> dict:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect(sock_path)
        s.sendall(json.dumps(req).encode() + b"\n")
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
    return json.loads(buf)
