"""Build a ProviderService from an operator config file (M04).  Trust roots,
policy keys and state keys are read from files named in the config -- never
inlined -- and the implementation digest is verified against the catalog."""
from __future__ import annotations

import importlib
import json
import pathlib

from ..authn.authenticator import Authenticator, TrustRoot
from ..authz.decision import AuthorizationEnforcer
from ..crypto.at_rest import KeyRing
from ..residency.engine import ResidencyEngine
from ..secret_refs.resolver import SecretResolver
from ..service import ProviderService
from ..state.store import LinkStateStore
from ..supply_chain.trust import ArtifactTrust


def _read_key(path: str) -> bytes:
    return bytes.fromhex(pathlib.Path(path).read_text().strip())


def build_service(cfg: dict) -> ProviderService:
    trust = ArtifactTrust.load(cfg["provider_catalog"])
    trust.require(cfg["contract_id"], cfg["implementation_digest"])
    ring = None
    if cfg.get("state_keys"):
        ring = KeyRing()
        for kid, path in cfg["state_keys"].items():
            ring.add(kid, _read_key(path), activate=(kid == cfg["active_state_key"]))
    root = TrustRoot(cfg["authn"]["issuer"], {k: _read_key(p) for k, p in cfg["authn"]["keys"].items()}, cfg["authn"]["audience"])
    residency = ResidencyEngine()
    for pol in cfg.get("residency_policies", []):
        residency.set_policy(pol)
    mod, _, cls = cfg["backend"].rpartition(".")
    backend = getattr(importlib.import_module(mod), cls)()
    sec_mod, _, sec_cls = cfg["secret_backend"].rpartition(".")
    return ProviderService(
        contract_id=cfg["contract_id"], backend=backend, store=LinkStateStore(cfg["state_dir"], keyring=ring),
        authenticator=Authenticator(root), authz=AuthorizationEnforcer({k: _read_key(p) for k, p in cfg["policy_keys"].items()}),
        secrets=SecretResolver(getattr(importlib.import_module(sec_mod), sec_cls)()), residency=residency,
        instance_id=cfg["instance_id"], site=cfg["site"], region=cfg["region"], environment=cfg["environment"])
