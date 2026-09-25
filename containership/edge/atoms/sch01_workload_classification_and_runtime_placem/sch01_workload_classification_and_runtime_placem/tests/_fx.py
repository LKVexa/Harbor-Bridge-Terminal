"""Shared fixture: a scheduler with per-run keys (never shipped), fake clock, principals."""
from __future__ import annotations

import itertools
import os
import pathlib
import sys
import tempfile

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(PKG_DIR.parent) not in sys.path:
    sys.path.insert(0, str(PKG_DIR.parent))

import sch01_workload_classification_and_runtime_placem as sch  # noqa: E402
from sch01_workload_classification_and_runtime_placem import (  # noqa: E402
    config as cfg, model as m, resilience as rs, scheduler as sc, security as sec)

ALLOWED = {t: frozenset({f"good-{t}"}) for t in sch.TIER_ORDER}
_n = itertools.count()


class Clock:
    def __init__(self, t=100): self.t = t
    def __call__(self): return self.t


def keys():
    return sec.StaticSecretProvider({k: os.urandom(32) for k in ("authn", "attest", "audit", "config")})


class Rig:
    def __init__(self, tmp=None, secrets=None, clock=None, **cfg_over):
        self.tmp = tmp or tempfile.mkdtemp(prefix="sch01-")
        self.secrets = secrets or keys()
        self.clock = clock or Clock()
        self.verifier = sec.AttestationVerifier(self.secrets, allowed_measurements=ALLOWED)
        doc = dict(cfg.DEFAULT_CONFIG); doc.update(cfg_over)
        self.config = cfg.ConfigStore(self.secrets, initial=doc)
        self.s = sc.Scheduler(secrets=self.secrets, state_dir=self.tmp, clock=self.clock,
                              attestation=self.verifier, config=self.config)
        self.ctr = itertools.count(1)

    def tok(self, sub="alice", kind="service", tenants=("t1",), roles=("workload-submitter",)):
        return self.s.authn.issue(sec.Principal(sub, kind, frozenset(tenants), frozenset(roles)), nonce=f"n{next(_n)}")

    def evidence(self, node, tiers, at=None, measure=None):
        return self.verifier.sign({"node": node, "at": self.clock() if at is None else at,
                                   "counter": next(self.ctr), "measurements": {t: (measure or f"good-{t}") for t in tiers}})

    def node(self, name, tiers=("process", "wasm", "unikernel", "microvm", "vm"), *, site="eu", slots=4, report=True,
             attest=True, **kw):
        tiers = frozenset(tiers)
        rep = sch.NodeReport(name, site, tiers, capabilities=frozenset(kw.pop("caps", ())), free_slots=slots,
                             reported_at=kw.pop("reported_at", self.clock()))
        spec = m.NodeSpec(rep, runtimes=kw.pop("runtimes", {t: f"rt-{t}" for t in tiers}),
                          attestation=self.evidence(name, tiers) if attest else None, **kw)
        if report:
            self.s.report_node(self.tok(name, "node", (), ("node-agent",)), spec)
        return spec

    def ctx(self, key=None, deadline=None):
        return rs.RequestContext(f"r{next(_n)}", key or f"k{next(_n)}", deadline if deadline is not None else self.clock() + 50)

    def req(self, name="w1", tenant="t1", prov="internal", **kw):
        wkw = {k: kw.pop(k) for k in ("latency_sensitive", "needs", "site_affinity") if k in kw}
        return m.PlacementRequest(sch.Workload(name, tenant, prov, **wkw), **kw)

    def place(self, req=None, tok=None, ctx=None, **kw):
        req = req or self.req(**kw)
        return self.s.place(tok or self.tok(tenants=(req.workload.tenant,)), req, ctx or self.ctx())
