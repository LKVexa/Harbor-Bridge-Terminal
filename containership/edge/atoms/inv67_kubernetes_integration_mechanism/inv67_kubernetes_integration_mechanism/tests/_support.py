"""Shared fixtures: makes the package importable standalone and builds a fully
wired controller over FakeKube + InMemoryRuntime with a manual clock."""
from __future__ import annotations

import pathlib
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib  # noqa: E402

PKG = importlib.import_module(PKG_DIR.name)
P = importlib.import_module(PKG_DIR.name + ".plane")
from importlib import import_module as _im  # noqa: E402


def mod(name):
    return _im(f"{PKG_DIR.name}.plane.{name}")


translator = _im(f"{PKG_DIR.name}.translator")
artifact, audit, authz, compat, config = mod("artifact"), mod("audit"), mod("authz"), mod("compat"), mod("config")
controller, downstream, identity, journal, kube = mod("controller"), mod("downstream"), mod("identity"), mod("journal"), mod("kube")
leader, lifecycle, observability, policy, resilience = mod("leader"), mod("lifecycle"), mod("observability"), mod("policy"), mod("resilience")
secrets, status = mod("secrets"), mod("status")

KEY = b"k" * 32
DIGEST = "@sha256:" + "a" * 64
IMAGE = "registry.example.org/web" + DIGEST


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t

    def tick(self, s):
        self.t += s


def workload(name="web", ns="team-a", image=IMAGE, containers=None, **tmpl_spec):
    cs = containers or [{"name": "c", "image": image,
                         "resources": {"requests": {"cpu": "250m", "memory": "64Mi"},
                                       "limits": {"cpu": "1", "memory": "128Mi"}}}]
    spec = {"containers": cs}
    spec.update(tmpl_spec)
    return {"apiVersion": kube.API_VERSION, "kind": kube.KIND,
            "metadata": {"name": name, "namespace": ns},
            "spec": {"template": {"metadata": {"labels": {"app": name}}, "spec": spec}}}


class Harness:
    def __init__(self, *, cfg=None, clock=None, lease_store=None, ident="ctrl-0", runtime=None, kube_=None,
                 journal_path=None, bindings=None):
        self.clock = clock or Clock()
        import io as _io
        self.logbuf = _io.StringIO()
        self.kube = kube_ or kube.FakeKube()
        self.rt = runtime or downstream.InMemoryRuntime()
        base = {"allowedRegistries": ["registry.example.org"], "tenantRatePerSec": 1000.0, "tenantBurst": 1000.0}
        base.update(cfg or {})
        self.audit = audit.AuditLog()
        self.cfg = config.ConfigStore(base, audit=self.audit)
        self.lease = lease_store or leader.LeaseStore()
        self.elector = leader.Elector(self.lease, ident, 15.0, self.clock)
        att = {IMAGE: artifact.HmacAttestationVerifier.sign(KEY, IMAGE)}
        self.verifier = artifact.HmacAttestationVerifier(KEY, att)
        self.journal = journal.Journal(journal_path)
        self.ctrl = controller.Controller(
            self.kube, self.rt, config=self.cfg,
            identity=identity.IdentityMapper("cluster-1", bindings or {"team-a": "tenant-a", "team-b": "tenant-b"}),
            elector=self.elector, verifier=self.verifier, journal=self.journal, audit=self.audit, clock=self.clock,
            logger=observability.get_logger("inv67.test." + ident, self.logbuf))

    def settle(self, rounds=10, step=0.0):
        for _ in range(rounds):
            self.ctrl.run_once()
            if step:
                self.clock.tick(step)

    def obj(self, name="web", ns="team-a"):
        return self.kube.get(ns, name)


def write_json(path, obj):
    import json as _j
    with open(path, "w", encoding="utf-8") as fh:
        _j.dump(obj, fh)
