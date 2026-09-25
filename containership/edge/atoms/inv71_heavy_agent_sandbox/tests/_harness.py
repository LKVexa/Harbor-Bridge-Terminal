"""Shared deterministic fixtures for the v4.3.0 control-layer tests."""
from __future__ import annotations

import pathlib
import sys
import tempfile

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv71_heavy_agent_sandbox.control.audit_log import AuditStream  # noqa: E402
from inv71_heavy_agent_sandbox.control.auth import TokenAuthority  # noqa: E402
from inv71_heavy_agent_sandbox.control.config import SECURE_DEFAULTS, digest_of, merge  # noqa: E402
from inv71_heavy_agent_sandbox.control.controller import AUD, SandboxController  # noqa: E402
from inv71_heavy_agent_sandbox.control.egress import Answer, EgressPolicy, ResolverError  # noqa: E402
from inv71_heavy_agent_sandbox.control.resilience import AdmissionController, NodeCapacity, TenantQuota  # noqa: E402

KEY = b"k" * 32
EGRESS_KEY = b"e" * 32
AUDIT_KEY = b"a" * 32
FAKE_ARTIFACTS = {c: {"version": "1.0.0", "sha256": "ab" * 32} for c in
                  ("firecracker", "jailer", "guest_kernel", "guest_rootfs")}


class Clock:
    def __init__(self, t: float = 1_000_000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, s: float) -> None:
        self.t += s


class FakeResolver:
    """Scripted trusted resolver; ``answers`` may be replaced mid-test (rebinding)."""

    def __init__(self, answers=None) -> None:
        self.answers = dict(answers or {})
        self.calls = 0
        self.down = False

    def resolve(self, name):
        self.calls += 1
        if self.down:
            raise ResolverError("down")
        a = self.answers.get(name)
        if a is None:
            return Answer((), (), 60)
        return a


class Host:
    """Observed host inventory; tests add leaked resources to simulate failures."""

    def __init__(self) -> None:
        self.extra: set[tuple[str, str]] = set()

    def __call__(self):
        return set(self.extra)


def build(tmpdir: str | None = None, *, quotas=None, node=None, anchors=None, resolver=None):
    clock = Clock()
    ta = TokenAuthority(KEY, "inv71-issuer", clock=clock)
    res = resolver or FakeResolver({"pypi.org": Answer((), ("151.101.0.223",), 60),
                                    "files.pythonhosted.org": Answer((), ("151.101.64.223",), 60)})
    pol = EgressPolicy.build("pol-1", [("pypi.org", [443]), ("files.pythonhosted.org", [443])],
                             key=EGRESS_KEY, resolver=res, clock=clock)
    d = tmpdir or tempfile.mkdtemp()
    anchors = anchors if anchors is not None else []  # any object with .append
    audit = AuditStream(pathlib.Path(d) / "audit.jsonl", key=AUDIT_KEY, node="node-1", clock=clock,
                        anchor=anchors.append, checkpoint_every=4, fsync=False)
    adm = AdmissionController(node or NodeCapacity(vcpu=32, mem_mib=65536, max_sessions=20),
                              quotas or {"t1": TenantQuota(10, 16, 32768, 1), "t2": TenantQuota(10, 16, 32768, 1)})
    cfg = merge({})
    host = Host()
    c = SandboxController(node="node-1", site="site-a", auth=ta, admission=adm, egress=pol, audit=audit,
                          config=cfg, config_digest=digest_of(cfg), artifacts=FAKE_ARTIFACTS, clock=clock,
                          observe_host=host)
    return c, ta, clock, res, host, anchors


def token(ta, role="workload", tenant="t1", actions=None, sub="alice", nonce=None, site="site-a", ttl=300, aud=AUD):
    from inv71_heavy_agent_sandbox.control.auth import ROLES
    token.n = getattr(token, "n", 0) + 1
    return ta.issue(aud=aud, sub=sub, role=role, tenant=tenant, site=site,
                    actions=actions or ROLES[role], ttl_s=ttl, nonce=nonce or f"n{token.n}")


__all__ = ["build", "token", "Clock", "FakeResolver", "Host", "KEY", "EGRESS_KEY", "AUDIT_KEY",
           "SECURE_DEFAULTS", "FAKE_ARTIFACTS", "Answer"]
