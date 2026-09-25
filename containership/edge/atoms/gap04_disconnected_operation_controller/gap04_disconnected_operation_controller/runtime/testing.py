"""Control-plane simulator and fixtures for integration, fault-injection and
contract tests. Not used on the production path; ships so adjacent teams can
run the GAP-04 contract suite against their own adapters."""
from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from pathlib import Path

from . import canonical, crypto
from .adapters import (CapabilityPlane, ReachabilityMonitor, ReferencePolicyEngine, ReferenceReplication,
                       ReferenceSupervisor, sign_grant, sign_heartbeat)
from .authz import Principal
from .clock import TrustedClock
from .config import default_config
from .node import QUARANTINE_CMD, QUARANTINE_TOKEN, Adapters, DisconnectedNode
from .trust import LEASE_VERSION, POLICY_VERSION, TRUST_VERSION, TrustStore, sign_lease, sign_policy

TD = "example.org"
SCOPE = {"site": "site-a", "tenant": "t0", "cluster": "c0", "node_class": "edge", "environment": "prod"}


class FakeMono:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


@dataclass
class ControlPlane:
    issuer: str = "cp-1"
    key_id: str = "cp-1-k1"
    t0: int = 1_800_000_000
    seed: bytes = b""
    pub: str = ""
    bundle_version: int = 1
    extra_keys: list = field(default_factory=list)
    epoch: int = 1
    policy_version: int = 0

    def __post_init__(self):
        self.seed, self.pub = crypto.generate_signing_key()

    def trust_doc(self, revoked=False) -> dict:
        keys = [{"key_id": self.key_id, "issuer": self.issuer, "alg": "Ed25519", "public_key": self.pub,
                 "not_before": 0, "not_after": 2**40, "revoked": revoked,
                 "purposes": ["lease", "policy", "time", "heartbeat", "grant", "quarantine", "config"]}]
        return {"version": TRUST_VERSION, "trust_domain": TD, "bundle_version": self.bundle_version,
                "keys": keys + self.extra_keys}

    def trust(self) -> TrustStore:
        return TrustStore.from_doc(self.trust_doc())

    def policy(self, version=None, rules=None) -> dict:
        self.policy_version = version if version is not None else self.policy_version + 1
        b = {"version": POLICY_VERSION, "issuer": self.issuer, "trust_domain": TD,
             "policy_version": self.policy_version, "activated_at": self.t0, "author": "alice", "approver": "bob",
             "rules": rules or {"allow_kinds": ["restart", "rebalance", "admit-known", "admit-new", "scale"],
                                "deny_subject_prefixes": ["kube-system/"], "freeze_kinds": ["restart"]},
             "key_id": self.key_id, "alg": "Ed25519"}
        return sign_policy(b, self.seed)

    def lease(self, policy_bundle, now, ttl=86400, epoch=None, scope=None, caps=None, lease_id=None, **over) -> dict:
        from .trust import policy_digest
        p = {"version": LEASE_VERSION, "issuer": self.issuer, "trust_domain": TD, "scope": dict(scope or SCOPE),
             "lease_id": lease_id or "L-" + secrets.token_hex(6), "issued_at": now, "not_before": now,
             "expires_at": now + ttl, "policy": {"version": policy_bundle["policy_version"],
                                                 "digest": policy_digest(policy_bundle)},
             "capabilities": sorted(caps or ["restart", "rebalance", "admit-known", "admit-new", "scale"]),
             "authority_epoch": self.epoch if epoch is None else epoch, "nonce": secrets.token_hex(16),
             "key_id": self.key_id, "alg": "Ed25519"}
        p.update(over)
        return sign_lease(p, self.seed)

    def heartbeat(self, monitor: ReachabilityMonitor, now: int, site="site-a") -> dict:
        return sign_heartbeat(site, monitor.challenge(), now, self.issuer, self.key_id, self.seed)

    def signed(self, version: str, **fields) -> dict:
        body = {"version": version, "site": "site-a", "issuer": self.issuer, "key_id": self.key_id, "alg": "Ed25519", **fields}
        return dict(body, sig=crypto.sign(self.seed, canonical.dumps(body)))

    def quarantine_cmd(self, reason="remote containment"):
        return self.signed(QUARANTINE_CMD, reason=reason)

    def release_token(self, nonce):
        return self.signed(QUARANTINE_TOKEN, quarantine_nonce=nonce)

    def grant(self, principal, caps, now, epoch=None, gid=None):
        return sign_grant(gid or "g-" + secrets.token_hex(4), "site-a", principal, caps,
                          self.epoch if epoch is None else epoch, now - 10, now + 10 ** 6,
                          self.issuer, self.key_id, self.seed)


OPERATOR = Principal(f"spiffe://{TD}/ops/alice", TD)
OPERATOR2 = Principal(f"spiffe://{TD}/ops/bob", TD)
WORKLOAD = Principal(f"spiffe://{TD}/workload/scheduler", TD)


def make_node(tmp: Path, cp: ControlPlane | None = None, *, supervisor=None, replication=None, config=None,
              mono: FakeMono | None = None, capabilities=False, owner="node-1", authorizer=None, **kw):
    cp = cp or ControlPlane()
    mono = mono or FakeMono()
    trust = cp.trust()
    cfg = config or default_config()
    r = cfg["reachability"]
    mon = ReachabilityMonitor("site-a", trust, up_after=r["up_after"], down_after=r["down_after"],
                              flap_window_s=r["flap_window_s"], flap_threshold=r["flap_threshold"])
    caps = CapabilityPlane(trust, "site-a") if capabilities else None
    ad = Adapters(ReferencePolicyEngine(), caps, supervisor or ReferenceSupervisor(),
                  replication or ReferenceReplication(), mon)
    clock = TrustedClock(monotonic=mono, max_drift_s=cfg["clock"]["max_drift_s"],
                         persist_interval_s=cfg["clock"]["persist_interval_s"])
    node = DisconnectedNode(Path(tmp), config=cfg, trust=trust, owner_id=owner, adapters=ad, clock=clock,
                            authorizer=authorizer, **kw)
    return node, cp, mono


def bring_up(node, cp, mono, *, ttl=86400):
    """Anchor time, go reachable, install policy + lease. Returns (policy, lease)."""
    node.clock.anchor_trusted(cp.t0 + int(mono.t - 1000))
    for _ in range(node.adapters.reachability.up_after):
        node.observe_reachability(cp.heartbeat(node.adapters.reachability, node.clock.now()))
    pol = cp.policy()
    node.install_policy(pol)
    lease = cp.lease(pol, node.clock.now(), ttl=ttl)
    node.install_lease(lease)
    return pol, lease


def go_dark(node, mono, secs=1):
    for _ in range(node.adapters.reachability.down_after):
        mono.t += secs
        node.observe_reachability(None)


def come_back(node, cp, mono, secs=1):
    for _ in range(node.adapters.reachability.up_after):
        mono.t += secs
        node.observe_reachability(cp.heartbeat(node.adapters.reachability, node.clock.now()))
