"""Shared fixture world for the 4.3.0 runtime tests (stdlib only)."""
from __future__ import annotations

import os
import pathlib
import secrets
import sys
import tempfile
import time

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

import importlib  # noqa: E402

P = importlib.import_module(PKG_DIR.name)
from inv65_capability_providers.authn.authenticator import Authenticator, TrustRoot, issue_token  # noqa: E402
from inv65_capability_providers.authz.decision import AuthorizationEnforcer, sign_decision  # noqa: E402
from inv65_capability_providers.fixtures.providers.keyvalue import KeyValueBackend  # noqa: E402
from inv65_capability_providers.residency.engine import ResidencyEngine  # noqa: E402
from inv65_capability_providers.secret_refs.resolver import InMemoryInv55Backend, SecretResolver  # noqa: E402
from inv65_capability_providers.service import ProviderService  # noqa: E402
from inv65_capability_providers.state.store import LinkStateStore  # noqa: E402

AUTHN_KEY = b"k" * 32
POLICY_KEY = b"p" * 32
CONTRACT = "wasi:keyvalue"


def ident(tenant="acme", env="prod", site="sfo1", workload="shop", component="orders"):
    return {"tenant": tenant, "environment": env, "site": site, "workload": workload, "component": component}


class World:
    def __init__(self, backend=None, state_dir=None, *, contract=CONTRACT, instance="inst-a", leases=None,
                 region="us-west", keyring=None):
        self.tmp = state_dir or tempfile.mkdtemp(prefix="inv65-")
        self.root = TrustRoot("pk-issuer", {"k1": AUTHN_KEY}, "inv65")
        self.backend = backend or KeyValueBackend()
        self.inv55 = InMemoryInv55Backend()
        self.residency = ResidencyEngine()
        self.residency.set_policy({"tenant": "acme", "allowed_regions": ["us-west", "us-east"], "failover_regions": ["us-east"]})
        self.residency.set_policy({"tenant": "globex", "allowed_regions": ["us-west"]})
        kw = {}
        if leases is not None:
            kw["leases"] = leases
        self.svc = ProviderService(
            contract_id=contract, backend=self.backend, store=LinkStateStore(self.tmp, keyring=keyring),
            authenticator=Authenticator(self.root), authz=AuthorizationEnforcer({"pol": POLICY_KEY}),
            secrets=SecretResolver(self.inv55), residency=self.residency, instance_id=instance,
            site="sfo1", region=region, environment="prod", **kw)

    def token(self, **ov):
        principal = ov.pop("principal", "")
        return issue_token(self.root, "k1", ident(**ov), nonce=secrets.token_hex(8), principal=principal)

    def decision(self, action, link_name, ops=None, *, effect="allow", ttl=300, subject=None, contract=None, **ov):
        now = time.time()
        res = {"contract_id": contract or self.svc.contract_id, "link_name": link_name}
        if ops is not None:
            res["operations"] = list(ops)
        return sign_decision(POLICY_KEY, {"schema": "PK_AUTHZ_DECISION/1", "decision_id": "d-" + secrets.token_hex(4),
                                          "subject": subject or ident(**ov), "action": action, "resource": res,
                                          "effect": effect, "issued_at": now - 1, "expires_at": now + ttl,
                                          "policy_version": "pol:7", "signature": "0" * 64})

    def link(self, name="primary", cfg=None, secret_ref=None, **ov):
        i = ident(**ov)
        key = (i["tenant"], i["environment"], i["site"], i["workload"], i["component"], name)
        action = "link.update" if self.svc.store.get(key) is not None else "link.create"
        return self.svc.link(self.token(**ov), self.decision(action, name, **ov), link_name=name,
                             config=cfg or {"bucket": f"{ov.get('tenant','acme')}-{name}", "user": "rw"}, secret_ref=secret_ref)

    def call(self, name="primary", op="get", payload=None, meta=None, **ov):
        return self.svc.call(self.token(**ov), self.decision("call", name, [op], **ov), link_name=name, op=op,
                             payload=payload or {"key": "x"}, meta=meta)

    def unlink(self, name="primary", **ov):
        return self.svc.unlink(self.token(**ov), self.decision("link.revoke", name, **ov), link_name=name)
