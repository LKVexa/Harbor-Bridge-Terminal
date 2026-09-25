"""Test/benchmark world builder: a self-contained PKI, policy and endpoint pair.

Uses the ``test`` key namespace only; nothing here is valid for production.
"""
from __future__ import annotations

import pathlib
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from .audit_log import AuditLog
from .endpoint import Channel, ControlEndpoint, EndpointConfig
from .handshake import AllowlistAttestation, HandshakePolicy, StaticRevocations, TrustStore, issue_credential
from .health import AdmissionController
from .keys import EpochPolicy, InMemoryKeyProvider, KeyClass, SigningKey
from .observability import MetricsRegistry, StructuredLogger
from .policy import Authorizer, PolicyStore, default_policy
from .quarantine import QuarantineRegistry
from .stream import Connection, FakeStream, FaultPlan

ISSUER = "inv36-test-ca"


@dataclass
class World:
    env: str = "test"
    tmp: pathlib.Path = field(default_factory=lambda: pathlib.Path(tempfile.mkdtemp(prefix="inv36-")))
    provider: InMemoryKeyProvider = field(init=False)
    anchor: SigningKey = field(init=False)
    quarantine_authority: SigningKey = field(init=False)
    audit_key: SigningKey = field(init=False)
    revocations: StaticRevocations = field(default_factory=StaticRevocations)
    epochs: EpochPolicy = field(default_factory=EpochPolicy)
    attestation: AllowlistAttestation = field(default_factory=AllowlistAttestation)
    policy_store: PolicyStore = field(default_factory=PolicyStore)

    def __post_init__(self) -> None:
        self.provider = InMemoryKeyProvider(self.env)
        self.anchor = self.provider.get_signing_key(self.provider.create("ca", KeyClass.TRUST_ANCHOR))
        self.quarantine_authority = self.provider.get_signing_key(
            self.provider.create("quarantine", KeyClass.QUARANTINE_AUTHORITY))
        self.audit_key = self.provider.get_signing_key(self.provider.create("audit", KeyClass.AUDIT_SIGNING))
        self.trust = TrustStore(ISSUER, {1: self.anchor.public_bytes()})
        self.policy_store.load(default_policy(time.time()))

    def identity(self, subject: str, role: str, tenant: str, *, epoch: int = 1, ttl: float = 3600.0,
                 not_before: float | None = None, measurement: str = "", env: str | None = None,
                 serial: str | None = None, anchor: SigningKey | None = None) -> tuple[SigningKey, bytes]:
        ref = self.provider.create(f"id/{subject.replace(':', '_')}", KeyClass.IDENTITY, epoch=epoch)
        key = self.provider.get_signing_key(ref)
        nb = time.time() - 60 if not_before is None else not_before
        cred = issue_credential(anchor or self.anchor, subject=subject, role=role, tenant=tenant,
                                env=env or self.env, public_key=key.public_bytes(), key_epoch=epoch,
                                issuer=ISSUER, anchor_version=1, not_before=nb, not_after=nb + ttl,
                                measurement=measurement, serial=serial)
        return key, cred

    def hs_policy(self, **kw) -> HandshakePolicy:
        base: dict[str, Any] = dict(env=self.env, trust=self.trust, revocations=self.revocations,
                                    attestation=self.attestation, epochs=self.epochs)
        base.update(kw)
        return HandshakePolicy(**base)

    def audit_log(self, name: str = "audit.jsonl", **kw) -> AuditLog:
        return AuditLog.open(self.tmp / name, signer=self.audit_key, signer_key_id="audit#1", node="test-node",
                             component_version="test", **kw)

    def quarantine_registry(self, **kw) -> QuarantineRegistry:
        return QuarantineRegistry({"q#1": self.quarantine_authority.public_bytes()}, **kw)

    def endpoint(self, subject: str, role: str, tenant: str, *, audit: AuditLog | None = None,
                 quarantine: QuarantineRegistry | None = None, handlers=None, cfg: EndpointConfig | None = None,
                 admission: AdmissionController | None = None, policy_kw: dict | None = None,
                 metrics: MetricsRegistry | None = None) -> ControlEndpoint:
        key, cred = self.identity(subject, role, tenant)
        return ControlEndpoint(identity=key, credential=cred, hs_policy=self.hs_policy(**(policy_kw or {})),
                               authorizer=Authorizer(self.policy_store, audit=(audit.listener() if audit else None)),
                               quarantine=quarantine or self.quarantine_registry(), audit=audit,
                               metrics=metrics or MetricsRegistry(), logger=StructuredLogger(level="error", stream=_Null()),  # type: ignore[arg-type]
                               admission=admission, cfg=cfg, handlers=handlers)


class _Null:
    def write(self, _s: str) -> int:
        return 0


def connect_pair(server: ControlEndpoint, client: ControlEndpoint, *, a_plan: FaultPlan | None = None,
                 b_plan: FaultPlan | None = None, timeout: float = 5.0) -> tuple[Channel, Channel]:
    """Run a full handshake over an in-memory stream; return (server_channel, client_channel)."""
    sa, sb = FakeStream.pair(a_plan=a_plan, b_plan=b_plan)
    ca = Connection(sa, read_timeout=timeout, write_timeout=timeout)
    cb = Connection(sb, read_timeout=timeout, write_timeout=timeout)
    out: dict = {}

    def run_server() -> None:
        try:
            out["s"] = server.accept(ca, source="fake:server")
        except Exception as exc:  # noqa: BLE001 - surfaced to caller below
            out["se"] = exc

    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    try:
        out["c"] = client.connect(cb, source="fake:client")
    except Exception as exc:  # noqa: BLE001
        out["ce"] = exc
    t.join(timeout + 1)
    if "se" in out:
        if "c" in out:
            out["c"].close("peer failed", graceful=False)
        raise out["se"]
    if "ce" in out:
        raise out["ce"]
    return out["s"], out["c"]
