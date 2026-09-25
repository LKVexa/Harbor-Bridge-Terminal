"""Shared deterministic fixtures for the INV-66 production test-suite."""
from __future__ import annotations

import hashlib
import io
import pathlib
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from cryptography.hazmat.primitives import serialization  # noqa: E402

from inv66_enterprise_wasm_control_plane.adapters import InMemoryDeploymentManager, RulePolicyEngine  # noqa: E402
from inv66_enterprise_wasm_control_plane.identity import Authenticator, Issuer, mint_token  # noqa: E402
from inv66_enterprise_wasm_control_plane.observability import JsonLogger, Metrics  # noqa: E402
from inv66_enterprise_wasm_control_plane.provenance import sign_image  # noqa: E402
from inv66_enterprise_wasm_control_plane.service import ControlPlaneService  # noqa: E402
from inv66_enterprise_wasm_control_plane.store import JournalStore  # noqa: E402


def _seed_key(seed: str) -> bytes:
    return hashlib.sha256(seed.encode()).digest()


def pub(priv: bytes) -> bytes:
    return Ed25519PrivateKey.from_private_bytes(priv).public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)


SIGNER_PRIV = _seed_key("release-signer")
ROGUE_PRIV = _seed_key("rogue")
IDP_HS_KEY = b"k" * 32
IDP_ED_PRIV = _seed_key("idp")
ANCHOR_KEY = b"a" * 32
REG = "registry.estate.local"
DIGEST = "ab" * 32


def image(name="api", digest=DIGEST, reg=REG):
    return f"{reg}/{name}@sha256:{digest}"


def component(name="api", priv=SIGNER_PRIV, signer="release-signer", img=None, attest=True):
    img = img or image(name)
    c = {"name": name, "image": img, "signer": signer, "signature": sign_image(priv, img)}
    if attest:
        c["attestations"] = [{"type": "slsa-provenance/v1", "digest": "sha256:" + "cd" * 32}]
    return c


def config(revision=1, environment="prod", **over):
    doc = {
        "schema": "PK_ECP_CONFIG/1", "revision": revision, "author": "alice", "approved_by": ["bob"],
        "source_revision": "0" * 40, "environment": environment,
        "limits": {"max_components": 64, "max_manifest_bytes": 1_000_000, "max_inflight": 64,
                   "audit_retention_records": 1000, "idempotency_ttl_s": 3600},
        "registries": [REG],
        "signers": [{"id": "release-signer", "public_key": pub(SIGNER_PRIV).hex()}],
        "require_attestations": ["slsa-provenance/v1"],
        "bindings": [
            {"subject": "user:ops", "role": "deployer", "scope": "org:acme/tenant:payments", "effect": "allow"},
            {"subject": "user:dev", "role": "deployer", "scope": "org:acme/tenant:payments/lattice:staging", "effect": "allow"},
            {"subject": "group:sre", "role": "org-admin", "scope": "org:acme", "effect": "allow"},
            {"subject": "user:auditor", "role": "auditor", "scope": "org:acme", "effect": "allow"},
            {"subject": "user:ops", "role": "deployer", "scope": "org:acme/tenant:payments/lattice:restricted", "effect": "deny"},
            {"subject": "service:gitops", "role": "deployer", "scope": "org:acme/tenant:payments", "effect": "allow"},
        ],
        "groups": {"sre": ["user:root"]},
        "quotas": {"*": {"admissions_per_minute": 10_000}},
    }
    doc.update(over)
    return doc


class Clock:
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def authenticator(clock):
    return Authenticator({
        "https://idp.acme": Issuer("https://idp.acme", frozenset({"HS256"}), {"k1": IDP_HS_KEY}),
        "https://ed.acme": Issuer("https://ed.acme", frozenset({"EdDSA"}), {"e1": pub(IDP_ED_PRIV)}),
    }, clock=clock)


_JTI = [0]


def token(sub="user:ops", clock=None, groups=(), iss="https://idp.acme", **over):
    now = int((clock or time.time)())
    _JTI[0] += 1
    claims = {"iss": iss, "sub": sub, "aud": "inv66-control-plane", "iat": now, "nbf": now, "exp": now + 300,
              "jti": f"j{_JTI[0]}-{time.monotonic_ns()}", "groups": list(groups)}
    claims.update(over)
    if iss == "https://ed.acme":
        return mint_token("EdDSA", "e1", IDP_ED_PRIV, claims)
    return mint_token("HS256", "k1", IDP_HS_KEY, claims)


def request(components=None, lattice="prod-eu", tenant="payments", rid="r1", **over):
    req = {"protocol": "PK_ECP_ADMIT/1", "request_id": rid, "tenant": tenant, "lattice": lattice,
           "manifest": {"name": "shop", "components": components or [component()]}}
    req.update(over)
    return req


class Harness:
    """Builds a service on a temp store; ``restart()`` simulates a process restart."""

    def __init__(self, cfg=None, rules=None, node="n1", path=None, fault=None, sink=None):
        self.tmp = tempfile.TemporaryDirectory() if path is None else None
        self.path = path or self.tmp.name
        self.clock = Clock()
        self.mono = Clock(1000.0)
        self.cfg = cfg or config()
        self.policy = RulePolicyEngine(rules or [], "gap13-bundle-7")
        self.deployer = InMemoryDeploymentManager()
        self.logs = io.StringIO()
        self.node, self.fault, self.sink = node, fault, sink
        self.svc = self._build()

    def _build(self):
        store = JournalStore(self.path, self.node, anchor_key=ANCHOR_KEY, clock=self.clock, fault=self.fault,
                             anchor_sink=self.sink, fsync=False)
        return ControlPlaneService(org="acme", store=store, authenticator=authenticator(self.clock),
                                   initial_config=self.cfg, policy_engine=self.policy, deployer=self.deployer,
                                   metrics=Metrics(), logger=JsonLogger(self.logs), clock=self.clock,
                                   mono=self.mono, sleep=lambda s: None)

    def restart(self):
        self.svc.store.release()
        self.svc = self._build()
        return self.svc

    def tok(self, sub="user:ops", **kw):
        return token(sub, self.clock, **kw)

    def close(self):
        if self.tmp:
            self.tmp.cleanup()
