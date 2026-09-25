"""Shared test harness: a trust domain, principals, signer and a fabric."""
from __future__ import annotations

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from inv60_wasm_application_fabric.fabric import signing  # noqa: E402
from inv60_wasm_application_fabric.fabric.fabric import AUDIENCE, Fabric  # noqa: E402
from inv60_wasm_application_fabric.fabric.identity import (TrustDomain, new_keypair,  # noqa: E402
                                                           reference_attestation)


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


class World:
    def __init__(self, tmp=None, hosts=("h1", "h2", "h3"), regions=None, clock=None, mono=None, limits=None):
        self.clock = clock or Clock()
        self.mono = mono or Clock(100.0)
        self.trust = TrustDomain("lattice.test", clock=self.clock)
        self.keys = {}
        self.signer_seed, signer_pub = new_keypair()
        self.policy = signing.TrustPolicy(allowed_builders=("https://ci.example/builder@v1",), clock=self.clock,
                                          trust_root_issued_at=self.clock())
        self.policy.add_signer("release-signer", signer_pub, subjects=("tenant-a/*", "tenant-b/*"))
        self.fabric = Fabric(trust=self.trust, policy=self.policy, clock=self.clock, mono=self.mono,
                             state_dir=(os.path.join(tmp, "state") if tmp else None),
                             ledger_path=(os.path.join(tmp, "audit.jsonl") if tmp else None), limits=limits)
        self.p = {}
        self.enrol("operator", "ops", "tenant-a")
        self.enrol("automation", "deployer-a", "tenant-a")
        self.enrol("automation", "deployer-b", "tenant-b")
        self.enrol("workload", "api", "tenant-a")
        self.enrol("workload", "evil", "tenant-b")
        regions = regions or {}
        for h in hosts:
            self.enrol("host", h, "infra", attest=True)
            r = self.fabric.join_host(self.tok(h), h, region=regions.get(h, "eu"))
            assert r.code == "OK", r.to_wire()

    def enrol(self, kind, name, tenant, attest=False):
        seed, pub = new_keypair()
        code = self.trust.issue_enrolment_code(kind, name, tenant)
        pr = self.trust.enrol(code, pub, attestation=reference_attestation(pub) if attest else None)
        self.keys[name] = seed
        self.p[name] = pr
        return pr

    def tok(self, name, **kw):
        return self.trust.mint_token(self.p[name].id, self.keys[name], AUDIENCE, **kw)

    def artifact(self, name="tenant-a/api", data=b"\x00asm-component-v1", level=3, seed=None):
        st = signing.statement_for(name, data, builder="https://ci.example/builder@v1", level=level,
                                   source_uri="git+https://example/inv60", commit="a" * 40)
        return signing.sign_statement(st, "release-signer", seed or self.signer_seed)

    def deploy(self, component="api", name="tenant-a/api", data=b"\x00asm-component-v1", tenant="tenant-a",
               deployer="deployer-a", **kw):
        r = self.fabric.push(self.tok(deployer), name, data, self.artifact(name, data), tenant=tenant)
        assert r.code == "OK", r.to_wire()
        return self.fabric.start(self.tok(deployer), component, r.value, tenant=tenant, **kw)
