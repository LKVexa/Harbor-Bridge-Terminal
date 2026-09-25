"""Shared test fixtures: import path, identities, production chainer builder."""
from __future__ import annotations

import pathlib
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import inv21_local_service_chaining as pkg  # noqa: E402
from inv21_local_service_chaining import errors as E  # noqa: E402,F401
from inv21_local_service_chaining.admission import AdmissionController, CircuitBreaker, RetryPolicy  # noqa: E402,F401
from inv21_local_service_chaining.audit import AuditLog  # noqa: E402
from inv21_local_service_chaining.chain import Chainer, Hop  # noqa: E402,F401
from inv21_local_service_chaining.config import ChainConfig  # noqa: E402
from inv21_local_service_chaining.context import CallContext, Deadline, IdentityVerifier  # noqa: E402,F401
from inv21_local_service_chaining.policy import GuardedProvider, StaticPolicyProvider  # noqa: E402
from inv21_local_service_chaining.residency import Residency  # noqa: E402
from inv21_local_service_chaining.transport import ChainEndpoint, LoopbackTransport  # noqa: E402

KEY = b"k" * 32
AUDIT_KEY = b"a" * 32
ISSUER = "pk-runtime"


def verifier() -> IdentityVerifier:
    return IdentityVerifier({"k1": KEY}, issuer=ISSUER)


def ctx(v: IdentityVerifier, tenant="acme", subject="svc-a", caps=(), trace="t-1", **kw) -> CallContext:
    tok = v.issue(subject, tenant, caps)
    return CallContext(v.verify(tok), trace, credential=tok, **kw)


def prod_config(**kw) -> ChainConfig:
    base = dict(mode="production", residency_lease_s=30.0, retry_max_attempts=1)
    base.update(kw)
    return ChainConfig(**base)


def build(host="host-1", *, grants=(), transport=None, cfg=None, provider=None, audit=True):
    """Production-mode chainer. Returns (chainer, residency, provider, verifier)."""
    v = verifier()
    res = Residency(host, default_lease_s=30.0)
    prov = provider or StaticPolicyProvider(grants)
    t = transport if transport is not None else _NullTransport()
    ch = Chainer(res, config=cfg or prod_config(), policy=GuardedProvider(prov), transport=t,
                 audit=AuditLog(AUDIT_KEY, lineage={"release": pkg.__version__}) if audit else None,
                 trusted_issuers=frozenset({ISSUER}), verifier=v)
    return ch, res, prov, v


class _NullTransport:
    def send(self, callee, request, ctx, timeout_s):
        raise E.TransportUnavailable("no peer", callee=callee)


def peer_pair(grants_local=(), grants_remote=(), handlers=None):
    """Caller host A (nothing placed) -> Loopback -> host B (handlers placed)."""
    b, res_b, prov_b, v = build("host-b", grants=grants_remote)
    for name, (tenant, fn) in (handlers or {}).items():
        res_b.place(name, tenant, fn, abi="hop")
    ep = ChainEndpoint(b, v)
    lt = LoopbackTransport(ep)
    a, res_a, prov_a, _ = build("host-a", grants=grants_local, transport=lt)
    return a, b, lt, v, res_a, res_b
