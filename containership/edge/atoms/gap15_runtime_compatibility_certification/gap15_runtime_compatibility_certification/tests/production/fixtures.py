"""Shared fixture world for the GAP-15 production-layer tests.

Builds real Ed25519 keys (deterministic seeds), a trust store with scoped keys,
token issuers, a provenance builder, an attestation key, a trusted clock, a
SQLite store in a temp dir and a fully wired CertificationService. Every
signed object in the tests is produced by these helpers — nothing is mocked
past the external boundaries (GAP-02 / GAP-07 / HSM), which are simulated
by locally generated keys and documented as such.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gap15_runtime_compatibility_certification.production import (  # noqa: E402
    attestation, authn, authz, policy, signing, store as store_mod, timepolicy)
from gap15_runtime_compatibility_certification.production.service import (  # noqa: E402
    CertificationService, ServiceConfig)
from gap15_runtime_compatibility_certification.production.state import CertKey, CertPolicy  # noqa: E402

ENV = "prod"
PART = "acme/prod/edge-1"
PART2 = "acme/prod/edge-2"
T0 = 1_800_000_000
BASELINE = {"pcr0": "a" * 64, "pcr7": "b" * 64}


def seed(name: str) -> bytes:
    return hashlib.sha256(b"gap15-fixture-" + name.encode()).digest()


def art(n: int = 1) -> str:
    return "sha256:" + hashlib.sha256(f"artifact-{n}".encode()).hexdigest()


class World:
    def __init__(self, *, ttl_s: int = 500, production: bool = False, fault_hook=None, db_path=None, clock_value=None):
        self.tmp = tempfile.mkdtemp(prefix="gap15-")
        self.db_path = db_path or os.path.join(self.tmp, "gap15.db")
        self.kp = signing.DevelopmentKeyProvider()
        self.trust = signing.TrustStore()
        keys = {
            "idp-key": ("idp", {"token:issue:producer", "token:issue:service", "token:issue:user",
                                "token:issue:automation", "token:issue:node", "token:issue:breakglass"}),
            "producer-a-key": ("producer-a", {f"evidence:submit:{ENV}"}),
            "producer-b-key": ("producer-b", {f"evidence:submit:{ENV}"}),
            "builder-key": ("gap07-builder", {"provenance:attest"}),
            "ak-node-1": ("node-1", {"attestation:quote"}),
            "svc-key": ("gap15-service", {"offline:issue", "checkpoint:sign", "backup:sign", "gate:sign"}),
        }
        for kid, (signer, scopes) in keys.items():
            pub = self.kp.generate(kid, seed(kid))
            self.trust.add(signing.TrustedKey(kid, signer, pub, scopes=frozenset(scopes)))
        self.clock_ref = [clock_value if clock_value is not None else T0]
        self.clock = timepolicy.TrustedClock([timepolicy.fixed_source(self.clock_ref)],
                                             monotonic=lambda: float(self.clock_ref[0]))
        self.authn = authn.Authenticator(self.trust, audience=ENV,
                                         issuers={"idp": set(authn.PRINCIPAL_TYPES)})
        self.authn.update_revocations(set(), set(), T0 + 10**9)  # fresh revocation list for fixture lifetime
        rules = [
            authz.Rule("producers-submit", "allow", frozenset({"evidence.submit"}), frozenset({"producer"})),
            authz.Rule("services-read", "allow", frozenset({"certify", "matrix.read", "explain.read", "admission.decide"}),
                       frozenset({"service", "user"})),
            authz.Rule("ops-lifecycle", "allow", frozenset({"lifecycle.mutate", "lifecycle.reactivate", "revocation.create",
                                                            "quarantine.create", "revocation.reverse", "quarantine.release",
                                                            "conflict.resolve", "emergency.disable", "audit.read",
                                                            "waiver.approve"}),
                       frozenset({"user"}), partitions=frozenset({"acme/prod/*"})),
        ]
        self.authz = authz.Authorizer(authz.PolicyBundle("authz:1", rules))
        self.policy = policy.PolicySet("policy:1", [
            policy.PolicyRule("deny-eol", "lifecycle", "deny", (("lifecycle", "end-of-life"),), control_id="CTL-EOL"),
            policy.PolicyRule("deny-deprecated-new", "lifecycle", "deny", (("lifecycle", "deprecated"),), control_id="CTL-DEPRECATED"),
        ])
        self.att_policy = attestation.AttestationPolicy(baselines={"base-1": BASELINE}, min_firmware="2.0.0")
        self.store = store_mod.Store(self.db_path, fault_hook=fault_hook)
        self.svc = CertificationService(
            config=ServiceConfig(ENV, frozenset({PART, PART2}), CertPolicy(ttl_s=ttl_s), production=production),
            store=self.store, trust=self.trust, authn=self.authn, authz=self.authz, clock=self.clock,
            key_provider=self.kp, service_key_id="svc-key", policy=self.policy, attestation_policy=self.att_policy)
        self._n = 0

    # ---------------------------------------------------------------- tokens
    def token(self, subject: str, ptype: str, scopes, partitions=(PART, PART2), **kw) -> str:
        self._n += 1
        return authn.issue_token(self.kp, "idp-key", issuer="idp", subject=subject, ptype=ptype, audience=ENV,
                                 now=self.clock_ref[0], ttl_s=600, scopes=list(scopes), partitions=list(partitions),
                                 nonce=f"n{self._n:06d}{os.urandom(4).hex()}", **kw)

    def producer(self, name: str = "producer-a") -> str:
        return self.token(name, "producer", ["evidence.submit"])

    def reader(self, name: str = "scheduler-svc") -> str:
        return self.token(name, "service", ["certify", "matrix.read", "explain.read", "admission.decide"])

    def operator(self, name: str = "alice") -> str:
        return self.token(name, "user", ["lifecycle.mutate", "lifecycle.reactivate", "revocation.create", "quarantine.create",
                                         "revocation.reverse", "quarantine.release", "conflict.resolve",
                                         "emergency.disable", "certify", "explain.read", "audit.read", "waiver.approve"],
                          partitions=("acme/prod/*",))

    # -------------------------------------------------------------- evidence
    def quote(self, nonce: str, *, runtime=("wasmtime", "21.0.0"), firmware="2.1.0", measurements=None, quoted_at=None,
              root="sev-snp", ak="ak-node-1", node="node-1", secure_boot=True):
        q = {"schema": "GAP15_QUOTE/1", "node_id": node, "ak_id": ak, "root": root, "nonce": nonce,
             "measurements": measurements or dict(BASELINE), "baseline": "base-1", "firmware": firmware,
             "secure_boot": secure_boot, "layers": [{"kind": "host"}, {"kind": "confidential"}],
             "quoted_at": self.clock_ref[0] if quoted_at is None else quoted_at,
             "runtime": {"arch": "arm64", "os": "linux", "isolation": "sev-snp", "name": runtime[0], "version": runtime[1],
                         "wasi": "preview2", "component_model": "0.2", "abi": "wasm32",
                         "wit": ["wasi:http/outgoing-handler@0.2.0", "wasi:cli/run@0.2.0"]}}
        sig = signing.sign_payload(self.kp, ak, message_type="quote", environment=ENV, payload=q, signed_at=q["quoted_at"])
        return q, sig

    def provenance(self, digest: str, *, builder="https://builder.example/gap07", sbom_subject=None):
        st = {"_type": "https://in-toto.io/Statement/v1",
              "subject": [{"name": "svc.wasm", "digest": {"sha256": digest[7:]}}],
              "predicateType": "https://slsa.dev/provenance/v1",
              "predicate": {"runDetails": {"builder": {"id": builder}},
                            "buildDefinition": {"resolvedDependencies": [{"uri": "git+https://src.example/svc@abc"}]}}}
        sig = signing.sign_payload(self.kp, "builder-key", message_type="provenance", environment=ENV, payload=st,
                                   signed_at=self.clock_ref[0])
        return {"statement": st, "signature": sig, "sbom": {"subject": sbom_subject or digest, "components": []}}

    def evidence(self, *, producer="producer-a", event_id=None, digest=None, result="compatible", observed_at=None,
                 runtime=("wasmtime", "21.0.0"), partition=PART, failure_class=None, features=None, nonce=None,
                 key_id=None, mutate=None, quote_kw=None, prov_kw=None) -> bytes:
        from gap15_runtime_compatibility_certification.production.canonical import canonical_bytes
        digest = digest or art(1)
        nonce = nonce or self.svc.issue_nonce(partition)
        q, qs = self.quote(nonce, runtime=runtime, **(quote_kw or {}))
        self._n += 1
        env = {"schema": "GAP15_EVIDENCE/1", "producer": producer, "producer_event_id": event_id or f"pe-{self._n}",
               "partition": partition, "artifact": {"digest": digest, "media_type": "application/wasm"},
               "runtime": f"{runtime[0]}@{runtime[1]}", "attestation": {"quote": q, "signature": qs, "nonce": nonce},
               "provenance": self.provenance(digest, **(prov_kw or {})), "result": result,
               "observed_at": self.clock_ref[0] if observed_at is None else observed_at,
               "test_suite": {"id": "wasi-conformance", "version": "2026.09", "harness_digest": art(999)}}
        if result == "incompatible":
            env["failure_class"] = failure_class or "deterministic"
        if features:
            env["features"] = features
        if mutate:
            mutate(env)
        kid = key_id or f"{producer}-key"
        env["signature"] = signing.sign_payload(self.kp, kid, message_type="evidence", environment=ENV,
                                                payload={k: v for k, v in env.items() if k != "signature"},
                                                signed_at=self.clock_ref[0])
        return canonical_bytes(env)

    def key_for(self, item: dict, digest=None, runtime="wasmtime@21.0.0", partition=PART) -> CertKey:
        return CertKey(partition, digest or art(1), runtime, item["profile_id"])

    def advance(self, seconds: int) -> None:
        self.clock_ref[0] += seconds
