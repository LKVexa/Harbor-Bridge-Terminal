"""Shared test fixtures: a controller wired to fake runtimes and a manual clock."""
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import logging  # noqa: E402
from gap01_edge_node_supervisor import make_request  # noqa: E402
from gap01_edge_node_supervisor.config import SupervisorConfig  # noqa: E402
from gap01_edge_node_supervisor.controller import ManualClock, SupervisorController  # noqa: E402
from gap01_edge_node_supervisor.health import SignalSpec  # noqa: E402
from gap01_edge_node_supervisor.runtime import FakeRuntime, RuntimeManager  # noqa: E402
from gap01_edge_node_supervisor.security import Authenticator, AuthorizationPolicy  # noqa: E402

KEYS = {"cp": b"c" * 32, "op": b"o" * 32, "hr": b"h" * 32, "obs": b"b" * 32, "bg": b"g" * 32}
QUIET = logging.getLogger("gap01-test")
QUIET.addHandler(logging.NullHandler())
QUIET.propagate = False


class Harness:
    def __init__(self, state_dir=None, clock=None, runtime=None, config=None, pressure=None):
        self.dir = state_dir or tempfile.mkdtemp(prefix="gap01-")
        self.clock = clock or ManualClock()
        self.rt = runtime or FakeRuntime("process")
        self.pressure = pressure or {"under_pressure": False, "reasons": []}
        pol = AuthorizationPolicy()
        pol.bind("cp", "control-plane")
        pol.bind("op", "operator")
        pol.bind("hr", "health-reporter")
        pol.bind("obs", "observer")
        pol.bind("bg", "break-glass")
        self.ctl = SupervisorController(
            "node-1", self.dir, config=config or SupervisorConfig(),
            runtime=RuntimeManager({"process": self.rt}),
            authenticator=Authenticator(dict(KEYS), skew_s=30), policy=pol,
            clock=self.clock, logger=QUIET, fsync=False,
            pressure_probe=lambda: self.pressure)
        self.ctl.health.register(SignalSpec("runtime", True, 30, frozenset({"hr"})))
        self.ctl.start()

    def req(self, caller, op, args=None, **kw):
        return make_request(caller, KEYS[caller], op, args, ts=self.clock.wall(), **kw)

    def call(self, caller, op, args=None, **kw):
        return self.ctl.handle(self.req(caller, op, args, **kw))

    def make_ready(self):
        assert self.call("hr", "report_health", {"signal": "runtime", "ok": True})["ok"]
        r = self.call("cp", "transition", {"to": "ready"})
        assert r["ok"], r
        return r

    def admit(self, name, trust="trusted"):
        return self.call("cp", "admit", {"workload": name, "trust_class": trust})

    def restart(self):
        return Harness(self.dir, self.clock, self.rt, self.ctl.cfg, self.pressure)
