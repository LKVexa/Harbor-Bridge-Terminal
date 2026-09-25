"""Shared fixtures for the INV-72 v4.3.0 suites."""
import io
import pathlib
import sys
import time

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

pkg = __import__(PKG_DIR.name)
from importlib import import_module  # noqa: E402

M = {n: import_module(f"{PKG_DIR.name}.{n}") for n in (
    "adapters", "audit", "capacity", "compat", "config", "discovery", "errors", "explain", "lifecycle", "matcher",
    "precedence", "redaction", "resilience", "schema_check", "service", "state", "telemetry", "trust")}
KEY = b"inventory-key-for-tests-000000000"
CALLER_KEY = b"caller-key-for-tests-0000000000000"
OPERATOR_KEY = b"operator-key-for-tests-00000000000"
ALL_CAPS = ["accel.match", "accel.reserve", "accel.release", "accel.read"]


def fleet_dicts():
    return [dict(dev_id="a0", cls="gpu-large", mem_gb=80, node="n1", link_group="nvl-1"),
            dict(dev_id="a1", cls="gpu-large", mem_gb=80, node="n1", link_group="nvl-1"),
            dict(dev_id="b0", cls="gpu-large", mem_gb=80, node="n2", link_group="pcie"),
            dict(dev_id="c0", cls="gpu-large", mem_gb=40, node="n3", link_group="pcie"),
            dict(dev_id="p0", cls="gpu-large", mem_gb=80, node="n4", link_group="pcie", partition_of="gpu-n4")]


class Clock:
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def build(profile="cloud", devices=None, clock=None, journal=None, auth=True, **svc_kw):
    clock = clock or time.time
    pub = M["adapters"].Gap02Publisher("gap02-a", KEY, devices if devices is not None else fleet_dicts(), clock=clock)
    inv = M["discovery"].InventoryCache([M["discovery"].Source("gap02-a", pub.publish, KEY)],
                                        clock=clock)
    cs = M["config"].ConfigStore()
    cfg = M["config"].compose(profile)
    cs.activate(cfg, author="test-operator", reason="fixture")
    inv.max_age_s, inv.offline_grace_s = cfg["inventory_max_age_s"], cfg["offline_grace_s"]
    inv.refresh()
    kp = M["trust"].StaticKeyProvider({"sched": CALLER_KEY, "operator": OPERATOR_KEY},
                                      {"sched": set(ALL_CAPS), "operator": {"accel.operate", "accel.read", "accel.config"}})
    authn = M["trust"].Authenticator(kp, clock=clock) if auth else None
    store = M["state"].ReservationStore(journal_path=journal, fsync=False)
    svc = M["service"].AcceleratorService(cs, inv, store, authn, logger=M["telemetry"].Logger(stream=io.StringIO()),
                                          clock=clock, **svc_kw)
    return svc, pub, kp


class Tokens:
    def __init__(self, clock=time.time):
        self.n = 0
        self.clock = clock

    def caller(self, tenants=("t1", "t2"), caps=ALL_CAPS):
        self.n += 1
        return M["trust"].mint(CALLER_KEY, "sched", tenants, caps, f"n{self.n}", int(self.clock()) + 60)

    def operator(self):
        self.n += 1
        return M["trust"].mint(OPERATOR_KEY, "operator", ["*"], ["accel.operate", "accel.read", "accel.config"],
                               f"o{self.n}", int(self.clock()) + 60)
