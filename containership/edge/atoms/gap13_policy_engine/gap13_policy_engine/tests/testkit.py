"""Shared fixtures for the GAP-13 suites (deterministic keys; test-only)."""
from __future__ import annotations

import base64
import pathlib
import sys
import tempfile

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(PKG_DIR.parent) not in sys.path:
    sys.path.insert(0, str(PKG_DIR.parent))

import gap13_policy_engine as g  # noqa: E402
from gap13_policy_engine.tools.sign_bundle import sign  # noqa: E402
from gap13_policy_engine.authz import issue_token, TokenAuthenticator, Authorizer, Principal  # noqa: E402
from gap13_policy_engine.attributes import StaticContextProvider  # noqa: E402

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from cryptography.hazmat.primitives import serialization  # noqa: E402

SEED = bytes(range(32))
SEED2 = bytes(range(1, 33))
ROGUE = bytes(range(2, 34))
T0 = 1_800_000_000


def pub(seed: bytes) -> bytes:
    return Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def trust_store(**overrides) -> g.TrustStore:
    k = dict(key_id="k1", algorithm="ed25519", public_key=pub(SEED), issuer="gap07-publisher",
             environments=("prod",), not_before=T0 - 10_000, not_after=T0 + 10_000_000)
    k.update(overrides)
    k2 = g.TrustedKey("k2", "ed25519", pub(SEED2), "gap07-publisher", ("prod",), T0 - 10_000, T0 + 10_000_000)
    return g.TrustStore("ts-1", {"k1": g.TrustedKey(**k), "k2": k2}, fetched_at=0)


def bundle_doc(generation=1, rules=None, **over):
    doc = {"schema": "PK_POLICY_BUNDLE/1", "bundle_id": f"b-{generation}", "policy_id": "estate",
           "issuer": "gap07-publisher", "generation": generation, "issued_at": T0, "environment": "prod",
           "version": f"v{generation}",
           "rules": rules if rules is not None else [
               {"name": "allow-read", "effect": "allow", "scope": "estate", "match": {"action": "read"}},
               {"name": "deny-pii", "effect": "deny", "scope": "estate",
                "match": {"action": "read", "classification": "pii"}}]}
    doc.update(over)
    return doc


def envelope(generation=1, rules=None, seed=SEED, key_id="k1", **over) -> bytes:
    return sign(bundle_doc(generation, rules, **over), seed, key_id)


def verifier(**kw) -> g.BundleVerifier:
    return g.BundleVerifier(g.StaticTrustSource(kw.pop("store", None) or trust_store()), environment="prod", **kw)


def verified(generation=1, rules=None, now=T0) -> g.VerificationResult:
    r = verifier().verify(envelope(generation, rules), now=now)
    assert r.verified, r.reason
    return r


class Clock:
    def __init__(self, t=float(T0)):
        self.t = t
        self.m = 1000.0

    def wall(self):
        return self.t

    def mono(self):
        return self.m

    def advance(self, s):
        self.t += s
        self.m += s


def principal(subject="alice", roles=("policy_admin",), kind="human", clock=None, **kw):
    return Principal(subject, kind, frozenset(roles), frozenset({"prod"}),
                     auth_time=int(clock.wall()) if clock else T0, mfa=True, **kw)


CONTEXT = StaticContextProvider({
    "svc-a": {"tenant": "t1", "workload": "w1", "classification": "public"},
    "svc-pii": {"tenant": "t1", "workload": "w1", "classification": "pii"},
    "alice": {"tenant": "t1"}, "bob": {"tenant": "t1"}, "sec": {"tenant": "t1"}, "ops": {"tenant": "t1"},
})


def service(state_dir=None, clock=None, **kw):
    clock = clock or Clock()
    cfg = kw.pop("config", None) or g.EngineConfig()
    v = kw.pop("verifier", None) or verifier()
    svc = g.PolicyService(cfg, v, state_dir=state_dir, context=kw.pop("context", CONTEXT),
                          wall=clock.wall, mono=clock.mono,
                          authorizer=kw.pop("authorizer", None) or Authorizer("prod", clock=clock.wall), **kw)
    return svc, clock


def tmpdir():
    return tempfile.mkdtemp(prefix="g13-")
