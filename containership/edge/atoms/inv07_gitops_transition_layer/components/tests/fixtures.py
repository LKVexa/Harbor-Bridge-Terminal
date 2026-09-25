"""Deterministic fixtures: keys, trust roots, a real signed git repository,
policy bundle, config and a fully wired controller in a temp directory."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.dont_write_bytecode = True

from inv07_gitops_transition_layer.components import cli, config, keys, policy, repotools  # noqa: E402


def seed(name: str) -> bytes:
    return hashlib.sha256(b"inv07-fixture-" + name.encode()).digest()


KEYS = {n: keys.generate_keypair(seed(n)) for n in ("dev", "dev2", "builder", "policy", "rogue", "token",
                                                    "audit")}
DEV_EMAIL, DEV2_EMAIL = "dev@example.invalid", "dev2@example.invalid"
BUILDER = "https://pk.example/builders/review"
NOW = int(time.time())


def trust_doc(**over) -> dict:
    ks = [
        {"key_id": "dev", "algorithm": "ed25519", "identity": DEV_EMAIL, "public_key": KEYS["dev"][1].hex(),
         "scopes": ["refs/heads/*", "refs/tags/*"], "purposes": ["commit"]},
        {"key_id": "dev2", "algorithm": "ed25519", "identity": DEV2_EMAIL, "public_key": KEYS["dev2"][1].hex(),
         "scopes": ["refs/heads/main"], "purposes": ["commit"]},
        {"key_id": "builder", "algorithm": "ed25519", "identity": "builder@example.invalid",
         "public_key": KEYS["builder"][1].hex(), "purposes": ["provenance"]},
        {"key_id": "policy", "algorithm": "ed25519", "identity": "policy@example.invalid",
         "public_key": KEYS["policy"][1].hex(), "purposes": ["policy"]},
    ]
    d = {"schema": "PK_GITOPS_TRUST/1", "version": 1, "allowed_algorithms": ["ed25519", "openpgp"], "keys": ks}
    d.update(over)
    return d


def deployment(name="web", ns="team-a", replicas=2, image="registry.example/web:1.0") -> str:
    return (f"apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: {name}\n  namespace: {ns}\n"
            f"spec:\n  replicas: {replicas}\n  template:\n    spec:\n      containers:\n        - name: {name}\n"
            f"          image: \"{image}\"\n")


def configmap(name="settings", ns="team-a", **data) -> str:
    return json.dumps({"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": name, "namespace": ns},
                       "data": data or {"mode": "prod"}}, indent=1)


def policy_bundle(version=1, rules=None, waivers=None) -> bytes:
    doc = {"schema": "PK_GITOPS_POLICY/1", "version": version, "waivers": waivers or [],
           "rules": rules if rules is not None else [
               {"id": "max-replicas", "effect": "deny", "match": {"kind": ["Deployment"]},
                "when": [{"path": "spec.replicas", "op": "gt", "value": 50}], "reason": "too many replicas"},
               {"id": "no-latest", "effect": "deny", "match": {"kind": ["Deployment"]},
                "when": [{"path": "spec.template.spec.containers.*.image", "op": "matches", "value": ".*:latest"}],
                "reason": "mutable image tag"}]}
    return policy.sign_bundle(doc, "policy", KEYS["policy"][0])


class Env:
    """A temp workspace with a signer repo, controller config and controller."""

    def __init__(self, *, prune=False, require_provenance=True, offline_mode="fail_closed", target=None,
                 time_source=None) -> None:
        self.tmp = tempfile.mkdtemp(prefix="inv07-")
        self.work = os.path.join(self.tmp, "signer")
        repotools.init(self.work)
        self.url = "file://" + self.work.replace(os.sep, "/")
        self.t = NOW - 3600
        with open(os.path.join(self.tmp, "trust_roots.json"), "w") as fh:
            json.dump(trust_doc(), fh)
        self.doc = config.merge(config.DEFAULTS, {
            "repository": {"url": self.url, "approved_refs": ["refs/heads/main"], "timeout_seconds": 60},
            "trust": {"trust_roots_file": "trust_roots.json", "require_provenance": require_provenance},
            "controller": {"prune": prune, "offline_mode": offline_mode, "state_dir": "state"},
            "tenancy": {"tenant": "acme", "site": "edge-1", "region": "local", "allowed_namespaces": ["team-a"],
                        "allowed_regions": ["local"]}})
        config.validate(self.doc)
        self.events: list[str] = []
        self.prune, self.target, self.time_source = prune, target, time_source

    def commit(self, files: dict, msg="change", key="dev", email=DEV_EMAIL, provenance=True, secret=None,
               ref="refs/heads/main") -> str:
        repotools.write_files(self.work, files)
        self.t += 60
        sk = secret if secret is not None else (KEYS[key][0] if key else None)
        oid = repotools.signed_commit(self.work, msg, key_id=key or "none", secret=sk, email=email, when=self.t,
                                      ref=ref)
        if provenance:
            repotools.add_provenance(self.work, oid, repo_url=self.url, ref=ref, builder_id=BUILDER,
                                     signers=[("builder", KEYS["builder"][0])])
        return oid

    def revert(self, target_oid: str) -> str:
        self.t += 60
        oid = repotools.revert_to(self.work, target_oid, key_id="dev", secret=KEYS["dev"][0], email=DEV_EMAIL,
                                  when=self.t)
        repotools.add_provenance(self.work, oid, repo_url=self.url, ref="refs/heads/main", builder_id=BUILDER,
                                 signers=[("builder", KEYS["builder"][0])])
        return oid

    def controller(self, node="node-1", bundle=None):
        return cli.build(self.doc, base_dir=self.tmp, target=self.target, node=node, allow_file_repos=True,
                         policy_bundle=bundle if bundle is not None else policy_bundle(),
                         event_sink=self.events.append, time_source=self.time_source)

    def cleanup(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
