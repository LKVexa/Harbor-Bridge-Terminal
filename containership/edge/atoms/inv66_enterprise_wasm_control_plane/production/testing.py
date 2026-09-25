"""Deterministic test/bench/demo estate: issuer, signers, a valid config, signed components.

Used by every suite, the benchmark harness and ``cli demo``.  Keys are generated
fresh per estate; nothing here is production trust material.
"""
from __future__ import annotations

import hashlib
import itertools
import tempfile
from pathlib import Path
from typing import Any, Optional

from .identity import Authenticator, StaticJwks, mint_token
from .keys import Signer
from .provenance import sign_component, sign_statement
from .service import ControlPlaneService

ORG = "acme"
ISSUER = "https://idp.acme.example"
AUDIENCE = "inv66-control-plane"
_counter = itertools.count(1)


def digest_for(name: str, version: str = "1") -> str:
    return hashlib.sha256(f"{name}:{version}".encode()).hexdigest()


class Estate:
    def __init__(self, root: Optional[Path] = None, *, environment: str = "prod", approvals: int = 2,
                 clock=None, **svc_kwargs: Any):
        self.root = Path(root or tempfile.mkdtemp(prefix="inv66-"))
        self.idp = Signer("idp-key-1")
        self.release_signer = Signer("release-signer")
        self.other_signer = Signer("team-b-signer")
        self.builder_signer = Signer("ci-builder")
        self.environment = environment
        self.approvals = approvals
        self.clock = clock
        self.jwks = StaticJwks({ISSUER: {self.idp.key_id: self.idp.public_b64()}})
        kw = {"clock": clock} if clock else {}
        self.auth = Authenticator(self.jwks, audience=AUDIENCE, trust_domain="acme.example", spiffe_org=ORG, **kw)
        self.svc_kwargs = svc_kwargs
        self.service = self.open()
        self.bootstrap()

    def open(self, **extra: Any) -> ControlPlaneService:
        kw = {**self.svc_kwargs, **extra}
        if self.clock:
            kw.setdefault("clock", self.clock)
        return ControlPlaneService(self.root, authenticator=self.auth, **kw)

    def config(self, **over: Any) -> dict[str, Any]:
        doc = {
            "schema": "PK_ECP_CONFIG/1", "environment": self.environment, "site": "eu-west-1", "org": ORG,
            "limits": {"max_components": 256, "max_manifest_bytes": 1_000_000, "default_deadline_ms": 5000,
                       "max_inflight": 256, "audit_segment_records": 10_000, "retention_days": 400},
            "quotas": {"default": {"rate_per_s": 1000.0, "burst": 1000, "max_inflight": 64},
                       "tenants": {"payments": {"rate_per_s": 1000.0, "burst": 1000, "max_inflight": 64}}},
            "roles": {"release-manager": ["admit", "admit.dry_run", "inventory.read", "explain.read"]},
            "bindings": [
                {"subject": "ops", "role": "deployer", "scope": f"{ORG}/payments/prod", "effect": "allow"},
                {"subject": "dev", "role": "deployer", "scope": f"{ORG}/payments/staging", "effect": "allow"},
                {"group": "platform-admins", "role": "org-admin", "scope": ORG, "effect": "allow"},
                {"subject": "sec1", "role": "security-admin", "scope": ORG, "effect": "allow"},
                {"subject": "sec2", "role": "security-admin", "scope": ORG, "effect": "allow"},
                {"subject": "auditor", "role": "auditor", "scope": ORG, "effect": "allow"},
                {"subject": "tadmin", "role": "tenant-admin", "scope": f"{ORG}/payments", "effect": "allow"},
                {"subject": "contractor", "role": "deployer", "scope": f"{ORG}/payments", "effect": "allow"},
                {"subject": "contractor", "role": "deployer", "scope": f"{ORG}/payments/prod", "effect": "deny"},
                {"subject": "payments/deployer", "role": "deployer", "scope": f"{ORG}/payments", "effect": "allow"},
            ],
            "registries": [{"host": "registry.estate.local", "scope": ORG},
                           {"host": "eu.registry.estate.local", "scope": ORG}],
            "signers": [{"id": self.release_signer.key_id, "public_key": self.release_signer.public_b64(), "scope": ORG},
                        {"id": self.other_signer.key_id, "public_key": self.other_signer.public_b64(),
                         "scope": f"{ORG}/analytics"},
                        {"id": self.builder_signer.key_id, "public_key": self.builder_signer.public_b64(), "scope": ORG}],
            "provenance": {"require_digest": True, "require_signature": True, "require_attestation": False,
                           "trusted_builders": ["https://ci.acme.example/builder@v3"]},
            "policy": {"engine": "local", "on_unavailable": "deny", "cache_ttl_s": 30, "rules": [
                {"id": "SEC-NO-DEBUG", "effect": "deny", "priority": 100, "class": "security",
                 "when": {"component_name": "debug-shell"}, "message": "debug shells never deploy"},
                {"id": "RES-EU-PROD", "effect": "require", "priority": 50, "class": "residency",
                 "when": {"tenant": "payments", "lattice": "prod"}, "require_image_prefix": "eu.registry.estate.local/",
                 "message": "payments prod images must come from the EU registry"},
                {"id": "COST-EXEMPT-RES", "effect": "exempt", "priority": 10, "class": "cost",
                 "when": {"tenant": "payments"}, "targets": ["RES-EU-PROD"], "message": "cost exemption (must be refused)"},
            ]},
            "dual_authorization": {"config_activate": self.approvals, "quarantine_release": 2},
            "dependencies": {"deployment": {"required": False, "endpoint": "http://inv63.local", "timeout_ms": 2000}},
            "secrets": {"anchor_key": "env:INV66_ANCHOR_KEY"},
            "telemetry": {"log_level": "info", "trace_sample_ratio": 1.0, "log_retention_days": 30,
                          "metrics_retention_days": 90, "redact_subjects": False},
        }
        doc.update(over)
        return doc

    def bootstrap(self) -> str:
        if self.service.config.active is not None:
            return self.service.config.active.generation
        gen = self.service.config.stage(self.config(), author="bootstrap", source_repo="file://bootstrap",
                                        source_rev="0" * 40)
        self.service.activate_config(gen, None, expected_active=None, reason_="day-0 bootstrap", bootstrap=True)
        return gen

    def token(self, sub: str, *, groups=(), kind: str = "user", ttl: float = 300, org: str = ORG,
              aud: str = AUDIENCE, tenant: Optional[str] = None, **extra: Any) -> str:
        t = (self.clock or __import__("time").time)()
        claims = {"iss": ISSUER, "aud": aud, "sub": sub, "org": org, "kind": kind, "groups": list(groups),
                  "iat": t, "nbf": t, "exp": t + ttl, "jti": f"jti-{next(_counter)}", **extra}
        if tenant:
            claims["tenant"] = tenant
        return mint_token(self.idp, claims)

    def principal(self, sub: str, **kw: Any):
        return self.auth.authenticate_token(self.token(sub, **kw))

    def component(self, name: str, *, registry: str = "eu.registry.estate.local", signer: Optional[Signer] = None,
                  version: str = "1", attest: bool = False) -> dict[str, Any]:
        signer = signer or self.release_signer
        d = digest_for(name, version)
        image = f"{registry}/{name}@sha256:{d}"
        c: dict[str, Any] = {"name": name, "image": image, "signer": signer.key_id,
                             "signature": sign_component(signer, image, name)}
        if attest:
            c["attestation"] = sign_statement(self.builder_signer, {
                "schema": "PK_ECP_ARTIFACT_STATEMENT/1", "subject_digest": d,
                "builder": "https://ci.acme.example/builder@v3", "source_repo": "https://git.acme.example/app",
                "source_rev": "a" * 40, "signer": "", "signature": ""})
        return c

    def request(self, *names: str, tenant: str = "payments", lattice: str = "prod", key: Optional[str] = None,
                **comp_kw: Any) -> dict[str, Any]:
        n = next(_counter)
        r = {"protocol": "PK_ECP_ADMIT/1", "request_id": f"req-{n}", "tenant": tenant, "lattice": lattice,
             "manifest": {"app": names[0] if names else "app",
                          "components": [self.component(x, **comp_kw) for x in (names or ("api",))]}}
        if key:
            r["idempotency_key"] = key
        return r
