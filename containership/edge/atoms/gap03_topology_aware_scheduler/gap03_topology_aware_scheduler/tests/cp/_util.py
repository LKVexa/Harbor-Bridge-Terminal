"""Shared test helpers.  ``covers`` binds a test to checklist check IDs; the
certification runner reads these bindings - a check is only ever evidenced by
a *passing* test that explicitly names it."""
import os
import shutil
import tempfile
import unittest

from gap03_topology_aware_scheduler.controlplane import identity
from gap03_topology_aware_scheduler.controlplane.audit import AuditLog
from gap03_topology_aware_scheduler.controlplane.faults import ManualClock


def covers(mc: str, *checks: int):
    ids = [f"{mc}-CHK-{c:03d}" for c in checks]

    def deco(fn):
        fn.__covers__ = list(getattr(fn, "__covers__", [])) + ids
        return fn
    return deco


class TmpCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gap03-")
        self.clock = ManualClock()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def d(self, name):
        p = os.path.join(self.tmp, name)
        os.makedirs(p, exist_ok=True)
        return p

    def trust(self, audit=None):
        t = identity.TrustStore(clock=self.clock, audit=audit)
        key = identity.SigningKey.generate("k1", "spiffe://prod.example/issuer/ca")
        t.add_key(key.issuer, key.kid, key.public)
        return t, key

    def audit(self, signer=None):
        return AuditLog(self.d("audit"), signer=signer, clock=self.clock)

    def token(self, key, sub, roles, aud, **extra):
        return identity.issue_token(key, subject=sub, audience=aud, roles=roles, clock=self.clock, extra=extra or None)
