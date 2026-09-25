"""Shared test fixtures.  Keys here are deterministic TEST keys; they are not
and must never be production trust roots."""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from gap09_unified_observability.runtime import Sample, SignalStore  # noqa: E402
from gap09_unified_observability.components import ed25519  # noqa: E402
from gap09_unified_observability.components.audit_ledger import AuditLedger  # noqa: E402
from gap09_unified_observability.components.canonical import submission_envelope  # noqa: E402
from gap09_unified_observability.components.controls import (AdmissionController, QuarantineRegistry,  # noqa: E402
                                                             TenantCardinalityQuota, TimeAuthority)
from gap09_unified_observability.components.durable import DurableReplayGuard  # noqa: E402
from gap09_unified_observability.components.ingest import VerifiedIngest  # noqa: E402
from gap09_unified_observability.components.keys import Ed25519Verifier, KeyRecord, KeyRegistry, sign_envelope  # noqa: E402


def seed(label: str) -> bytes:
    return hashlib.sha256(b"GAP09-TEST-ONLY|" + label.encode()).digest()


SK_A = seed("reporter-a")
PK_A = ed25519.public_key(SK_A)
SK_ROOT = seed("att-root")
PK_ROOT = ed25519.public_key(SK_ROOT)
SK_POLICY = seed("policy")
PK_POLICY = ed25519.public_key(SK_POLICY)
SK_GW = seed("gateway")
PK_GW = ed25519.public_key(SK_GW)


def sample(signal="cpu", value=1.0, tenant="t1", env="prod", site="s1", workload="w1", at=100):
    return Sample(signal, value, tenant, env, site, workload, at)


class Clock:
    def __init__(self, now=1000, synced=None):
        self.now, self.synced = now, now if synced is None else synced

    def __call__(self):
        return self.now, self.synced


def make_stack(tmp: str, *, now=1000, tenant_series=100, rate=1000.0):
    audit = AuditLedger(os.path.join(tmp, "audit.jsonl"), clock=lambda: now)
    reg = KeyRegistry(audit=audit)
    reg.add(KeyRecord("k1", "rep-a", "ed25519", PK_A, 0, 10**9, frozenset({"t1"})), actor="test")
    clock = Clock(now)
    ingest = VerifiedIngest(
        store=SignalStore(), verifier=Ed25519Verifier(reg), time_authority=TimeAuthority(clock, max_skew=5, max_sync_age=60),
        admission=AdmissionController(tenant_rate=rate, tenant_burst=rate, reporter_rate=rate, reporter_burst=rate, max_inflight=64),
        quarantine=QuarantineRegistry(audit=audit), quota=TenantCardinalityQuota(tenant_series),
        replay=DurableReplayGuard(os.path.join(tmp, "replay.log"), window=3600), audit=audit)
    return ingest, reg, clock, audit


def signed(samples, sid="sub-1", issued=1000, key_id="k1", reporter="rep-a", sk=SK_A):
    env = submission_envelope(reporter, sid, issued, samples, key_id)
    return dict(reporter=reporter, samples=samples, submission_id=sid, issued_at=issued,
                signature=sign_envelope(sk, env), key_id=key_id)


def tmpdir():
    return tempfile.mkdtemp(prefix="gap09-")
