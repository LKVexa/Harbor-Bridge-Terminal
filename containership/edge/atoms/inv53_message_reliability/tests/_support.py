"""Shared helpers for the INV-53 5.1 test suites (stdlib only)."""
from __future__ import annotations

import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import inv53_message_reliability as P  # noqa: E402
from inv53_message_reliability import security as S  # noqa: E402
from inv53_message_reliability.observability import Metrics, StructuredLogger  # noqa: E402
from inv53_message_reliability.service import Broker  # noqa: E402

KEY_A = bytes(range(32))
KEY_B = bytes(range(1, 33))


OPEN_BROKERS: list = []


class TmpDirCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="inv53-test-"))

    def tearDown(self) -> None:
        while OPEN_BROKERS:
            b = OPEN_BROKERS.pop()
            for c in b._queues.values():
                try:
                    c.q.close()
                except Exception:
                    pass
        shutil.rmtree(self.tmp, ignore_errors=True)


class Clock:
    def __init__(self, t: float = 1_000_000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


def make_broker(root, *, clock=None, config=None, grants=None, fault=None, audit=True, keyring=None):
    clock = clock or Clock()
    ring = keyring or S.Keyring()
    if keyring is None:
        ring.add("ka", KEY_A, activate=True)
        ring.add("kb", KEY_B)
    authn = S.Authenticator(ring, principals={"alice": "ka", "bob": "kb", "ops": "ka"})
    grants = grants if grants is not None else [
        S.Grant("alice", "acme", "*", frozenset({"produce", "consume", "redrive", "read_dlq"})),
        S.Grant("bob", "globex", "*", frozenset({"produce", "consume"})),
    ]
    stream = io.StringIO()
    b = Broker(root / "broker", config=config, authenticator=authn, authorizer=S.Authorizer(grants),
               audit=S.AuditLog(root / "audit.jsonl") if audit else None, metrics=Metrics(),
               logger=StructuredLogger(stream, clock=clock), clock=clock, fault=fault)
    b._test_log = stream
    OPEN_BROKERS.append(b)
    return b, clock


_nonce = [0]


def signed(req: dict, principal: str = "alice", kid: str = "ka", key: bytes = KEY_A, ts: float = 1_000_000.0) -> dict:
    _nonce[0] += 1
    req = {"v": "inv53.wire/1", **req}
    req["auth"] = S.sign(key, req, kid=kid, principal=principal, ts=ts, nonce=f"n{_nonce[0]}")
    return req


def load_json(path) -> dict:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
