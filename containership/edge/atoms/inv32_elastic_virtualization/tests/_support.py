"""Shared fixtures for the v4.3.0 control-plane tests (stdlib unittest)."""
from __future__ import annotations

import importlib
import pathlib
import random
import sys
import tempfile

try:  # installed wheel (CI "install from artifact" stage) takes precedence
    pkg = importlib.import_module("inv32_elastic_virtualization")
except ModuleNotFoundError:  # source checkout
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
    pkg = importlib.import_module("inv32_elastic_virtualization")

from inv32_elastic_virtualization import errors as E  # noqa: E402
from inv32_elastic_virtualization.adapters import FakeHypervisor  # noqa: E402
from inv32_elastic_virtualization.authz import Authenticator, Keyring, Policy  # noqa: E402
from inv32_elastic_virtualization.config import ConfigManager  # noqa: E402
from inv32_elastic_virtualization.controller import ElasticController  # noqa: E402
from inv32_elastic_virtualization.fencing import FileLeaseStore, Ownership  # noqa: E402
from inv32_elastic_virtualization.store import DurableStore  # noqa: E402

KEY = b"k" * 32
AUDIT_KEY = b"a" * 32
HOST = "host-1"


class FakeClock:
    def __init__(self, t: float = 1_700_000_000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, s: float) -> None:
        self.t += s


class Rig:
    """A complete controller on a fake hypervisor with durable state in a temp dir."""

    def __init__(self, *, total_mib: int = 16384, tmp: str | None = None, controller_id: str = "c1",
                 lease_dir: str | None = None, fake: FakeHypervisor | None = None, config_layers=None,
                 clock: FakeClock | None = None) -> None:
        self._tmp = tempfile.TemporaryDirectory() if tmp is None else None
        self.dir = pathlib.Path(tmp or self._tmp.name)
        self.clock = clock or FakeClock()
        self.fake = fake or FakeHypervisor(total_mib, overhead_mib=0, block_mib=128)
        self.store = DurableStore(self.dir / f"state-{controller_id}", signing_key=AUDIT_KEY, clock=self.clock)
        self.leases = FileLeaseStore(lease_dir or (self.dir / "leases"), clock=self.clock)
        self.ownership = Ownership(self.leases, HOST, controller_id, duration_s=15, clock=self.clock)
        self.ownership.acquire()
        self.authn = Authenticator(Keyring({"k1": KEY}, "k1"), issuer="idp.test", audience="inv32", clock=self.clock)
        self.policy = Policy()
        self.config = ConfigManager(release_version=pkg.__version__)
        if config_layers:
            self.config.activate(self.config.stage(config_layers, author="test", source="test"))
        self.ctl = ElasticController(host=HOST, controller_id=controller_id, adapter=self.fake, store=self.store,
                                     ownership=self.ownership, authenticator=self.authn, policy=self.policy,
                                     config=self.config, clock=self.clock, sleep=lambda s: None,
                                     rng=random.Random(7))

    def guest(self, name="g1", tenant="t1", mem=1024, vcpus=1, floor=256, ceiling=4096, vcpu_max=4, **kw):
        self.fake.create_guest(name, tenant, mem, vcpus, **kw)
        self.ctl.register_guest(name, tenant=tenant, floor_mib=floor, ceiling_mib=ceiling, vcpu_max=vcpu_max)

    def tenant_token(self, tenant="t1", actions=("memory.adjust", "vcpu.adjust", "guest.read"), **kw):
        return self.authn.issue(f"tenant:idp.test/{tenant}", "tenant", tenant=tenant, actions=actions, **kw)

    def operator_token(self, actions=("memory.adjust", "vcpu.adjust", "adjustment.revert", "quarantine.set",
                                      "emergency.disable", "explain.read"), **kw):
        return self.authn.issue("operator:idp.test/alice", "operator", actions=actions, **kw)

    @staticmethod
    def mem(op_id, target, guest="g1", tenant="t1", **extra):
        return {"schema": "PK_RESOURCE_ADJUSTMENT/2", "op": "memory_adjust", "operation_id": op_id, "host": HOST,
                "guest": guest, "tenant": tenant, "target_mib": target, **extra}

    @staticmethod
    def cpu(op_id, target, guest="g1", tenant="t1", **extra):
        return {"schema": "PK_RESOURCE_ADJUSTMENT/2", "op": "vcpu_adjust", "operation_id": op_id, "host": HOST,
                "guest": guest, "tenant": tenant, "target_vcpus": target, **extra}

    @staticmethod
    def revert(op_id, event_hash, kind="memory", guest="g1", tenant="t1"):
        return {"schema": "PK_RESOURCE_ADJUSTMENT/2", "op": f"{kind}_revert", "operation_id": op_id, "host": HOST,
                "guest": guest, "tenant": tenant, "record_event_hash": event_hash}

    def close(self):
        if self._tmp:
            self._tmp.cleanup()
