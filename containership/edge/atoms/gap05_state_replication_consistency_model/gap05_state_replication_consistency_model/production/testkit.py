"""Deterministic fixture cluster used by tests, benchmarks, the model checker and demos."""
from __future__ import annotations

import tempfile
from pathlib import Path

from .authz import Grant, Permission, Policy
from .identity import CertificateAuthority, IdentityVerifier, ReplicaKeys, TrustBundle, b64, pub_bytes
from .membership import MembershipConfig, MembershipStore, ReplicaRecord
from .node import ReplicaNode

T, E = "tenant-a", "prod"
NOW = 1_800_000_000


def replica_record(keys: ReplicaKeys, *, since=1) -> ReplicaRecord:
    return ReplicaRecord(keys.replica, keys.credential.workload_id, (keys.fingerprint,),
                         (b64(pub_bytes(keys.private_key.public_key())),), "active", {}, since, None)


def full_policy(principals, tenants=((T, E),), version="p1") -> Policy:
    grants = [Grant(p, perm, t, e) for p in principals for perm in Permission for t, e in tenants]
    return Policy(grants, version=version)


class Cluster:
    def __init__(self, names=("a", "b", "c"), *, root: Path | None = None, trust_domain="gap05.test",
                 node_kwargs=None, tenants=((T, E),)):
        self._tmp = None
        if root is None:
            self._tmp = tempfile.TemporaryDirectory(prefix="gap05-")
            root = Path(self._tmp.name)
        self.root = Path(root)
        self.ca = CertificateAuthority(trust_domain, key=self._load_key("ca"))
        self._save_key("ca", self.ca._key)
        self.bundle = TrustBundle(trust_domain)
        self.bundle.add(self.ca.public_key)
        self.verifier = IdentityVerifier(self.bundle)
        self.keys = {}
        for n in names:
            k = self._load_key(f"replica-{n}")
            if k is None:
                self.keys[n] = ReplicaKeys.provision(self.ca, n, now=NOW)
                self._save_key(f"replica-{n}", self.keys[n].private_key)
            else:
                self.keys[n] = ReplicaKeys(n, k, self.ca.issue(n, k.public_key(), now=NOW, ttl=86_400))
        genesis = MembershipConfig(1, {n: replica_record(k) for n, k in self.keys.items()}, None, "bootstrap",
                                   "genesis")
        self.membership_dirs = {}
        self.memberships = {}
        for n in names:
            d = self.root / n / "membership"
            self.membership_dirs[n] = d
            self.memberships[n] = MembershipStore(d, genesis)
        principals = ["operator"] + [k.credential.workload_id for k in self.keys.values()]
        self.policy = full_policy(principals, tenants)
        self.node_kwargs = node_kwargs or {}
        self.nodes = {n: self.open(n) for n in names}

    def _key_path(self, name):
        return self.root / "keys" / f"{name}.ed25519"

    def _load_key(self, name):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        p = self._key_path(name)
        return Ed25519PrivateKey.from_private_bytes(p.read_bytes()) if p.exists() else None

    def _save_key(self, name, key):
        from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
        p = self._key_path(name)
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()))
            p.chmod(0o600)

    def open(self, n, **extra):
        kw = {**self.node_kwargs, **extra}
        return ReplicaNode(self.root / n / "data", self.keys[n], self.memberships[n],
                           policy_provider=lambda: self.policy, **kw)

    def reopen(self, n, **extra):
        self.nodes[n].close()
        self.nodes[n] = self.open(n, **extra)
        return self.nodes[n]

    def principal(self, n) -> str:
        return self.keys[n].credential.workload_id

    def activate_everywhere(self, fn):
        """Apply the same membership change to every replica's store (config distribution)."""
        out = None
        for n, store in self.memberships.items():
            out = fn(store)
        return out

    def close(self):
        for node in self.nodes.values():
            try:
                node.close()
            except Exception:
                pass
        if self._tmp:
            self._tmp.cleanup()
