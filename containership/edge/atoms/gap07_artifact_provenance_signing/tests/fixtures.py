"""Shared deterministic test PKI for v6 tests (software custody, never production)."""
from __future__ import annotations

from gap07_artifact_provenance_signing import algorithms as algs
from gap07_artifact_provenance_signing.keys import KeyRef, SoftwareKeyCustody
from gap07_artifact_provenance_signing.signing import ArtifactSigner
from gap07_artifact_provenance_signing.trust import Anchor, Namespace, SignerAuthz, TrustGeneration, issue_cert

T0 = 1_800_000_000
NS = Namespace("acme", "site-a", "prod")
IDENT = "spiffe://acme/prod/release-bot"


class PKI:
    def __init__(self, alg: str = "ed25519", ns: Namespace = NS):
        self.ns = ns
        self.root = algs.generate_private_key("ed25519")
        self.inter = algs.generate_private_key("ed25519")
        self.custody = SoftwareKeyCustody()
        self.refs = {}
        self.anchor = Anchor("root-1", "ed25519", algs.spki(self.root.public_key()), T0 - 10**6, T0 + 10**8,
                             name_constraints=("spiffe://acme/",), max_path_len=2)
        self.inter_cert = issue_cert(issuer_id="root-1", issuer_alg="ed25519", issuer_sign=algs.software_signer("ed25519", self.root),
                                     serial="int-1", subject="spiffe://acme/ca/intermediate", namespace=ns, kid="int-1-key", alg="ed25519",
                                     spki=algs.spki(self.inter.public_key()), usages=["ca"], not_before=T0 - 10**6, not_after=T0 + 10**7,
                                     path_len=0, name_constraints=["spiffe://acme/prod/"])
        self.certs = [self.inter_cert]
        self.signers = []
        self.add_signer(IDENT, "k1", alg, kinds=("code", "bundle", "oci-image", "oci-index", "wasm-module", "attestation", "sbom", "microvm-image", "provider-bundle"),
                        predicates=("https://slsa.dev/provenance/v1", "https://cyclonedx.org/bom", "https://spdx.dev/Document"))

    def add_signer(self, identity, name, alg="ed25519", *, kinds=("code",), predicates=(), not_after=None, serial=None):
        ref = KeyRef("software", self.ns.tenant, self.ns.site, self.ns.environment, name, "1", alg, protection_level="software")
        spki = self.custody.create(ref)
        usages = [f"sign:{k}" for k in kinds] + [f"attest:{p}" for p in predicates]
        cert = issue_cert(issuer_id="int-1", issuer_alg="ed25519", issuer_sign=algs.software_signer("ed25519", self.inter),
                          serial=serial or f"leaf-{name}", subject=identity, namespace=self.ns, kid=ref.kid, alg=alg, spki=spki,
                          usages=usages, not_before=T0 - 1000, not_after=not_after or T0 + 10**6)
        self.certs.append(cert)
        self.signers.append(SignerAuthz(identity, frozenset({"release"}), frozenset(kinds), frozenset(predicates)))
        self.refs[name] = ref
        return ref

    def signer(self, name="k1", identity=IDENT):
        return ArtifactSigner(self.custody, self.refs[name], identity)

    def trust(self, generation=1, **kw):
        base = dict(namespace=self.ns, generation=generation, issued_at=T0 - 10, max_staleness_s=86400,
                    anchors=(self.anchor,), certs=tuple(self.certs), signers=tuple(self.signers))
        base.update(kw)
        return TrustGeneration(**base)


# ------------------------------------------------------------------ E2E env
import base64 as _b64
import hashlib as _hl

from gap07_artifact_provenance_signing import dsse as _dsse
from gap07_artifact_provenance_signing.admission import AdmissionController, AdmissionConfig, make_bundle
from gap07_artifact_provenance_signing.canonical import canonical_bytes
from gap07_artifact_provenance_signing.core import AuditLedger
from gap07_artifact_provenance_signing.policy import PolicyStore
from gap07_artifact_provenance_signing.store import AuthorityKey, TrustState, sign_config
from gap07_artifact_provenance_signing.timesrc import TimeAuthority, TrustedClock
from gap07_artifact_provenance_signing.tlog import LocalTransparencyLog, LogKey, entry_bytes, CheckpointCache

AUTH_PURPOSES = frozenset({"trust-snapshot", "trust-distribution", "trust-delta", "policy-bundle", "waiver", "break-glass"})

def default_rules():
    return [
        {"rule_id": "prod-code", "priority": 100, "match": {"tenant": "acme", "environment": "prod", "kind": "code"}, "effect": "allow",
         "require": {"roles": ["release"], "threshold": 1, "transparency": True,
                     "attestations": [{"predicate_type": "https://slsa.dev/provenance/v1", "builder_ids": ["https://ci.acme/builder@v1"]}],
                     "sbom": {"required": True, "deny_packages": ["pkg:pypi/evil"], "max_severity": "medium"}}},
        {"rule_id": "prod-oci", "priority": 100, "match": {"tenant": "acme", "environment": "prod", "kind": "oci-image"}, "effect": "allow",
         "require": {"roles": ["release"], "threshold": 1}},
        {"rule_id": "deny-grants", "priority": 100, "match": {"tenant": "*", "environment": "*", "kind": "grant"}, "effect": "deny", "require": {}},
    ]


class Env:
    def __init__(self, rules=None, policy_version=1):
        self.pki = PKI()
        self.auth_key = algs.generate_private_key("ed25519")
        self.auth_sign = algs.software_signer("ed25519", self.auth_key)
        self.authorities = {"cfg-1": AuthorityKey("cfg-1", "ed25519", algs.spki(self.auth_key.public_key()), AUTH_PURPOSES)}
        tk = algs.generate_private_key("ed25519")
        self.time_auth = TimeAuthority("ta-1", "ed25519", algs.software_signer("ed25519", tk))
        self.mono = [0.0]
        self.clock = TrustedClock(site="site-a", device="dev-1", authorities={"ta-1": ("ed25519", algs.spki(tk.public_key()))},
                                  monotonic=lambda: self.mono[0], wall=lambda: T0)
        self.clock.ingest(self.time_auth.attest("site-a", "dev-1", T0))
        lk = algs.generate_private_key("ed25519")
        self.log = LocalTransparencyLog("log.acme", "log-k1", "ed25519", algs.software_signer("ed25519", lk))
        self.log_keys = {"log-k1": LogKey("log.acme", "log-k1", "ed25519", algs.spki(lk.public_key()))}
        self.audit = AuditLedger()
        self.state = TrustState()
        self.state.swap(self.pki.trust())
        self.policy = PolicyStore(self.authorities, audit=self.audit)
        self.policy.activate(self.policy_doc(rules or default_rules(), policy_version), now=T0, actor="test")
        self.ctl = AdmissionController(trust_state=self.state, policy_store=self.policy, clock=self.clock, authorities=self.authorities,
                                       log_keys=self.log_keys, checkpoint_cache=CheckpointCache(self.log_keys), audit=self.audit)
        self.builder = self.pki.signer()

    def advance(self, s):
        self.mono[0] += s

    def cfg(self, t, body):
        return sign_config(t, body, kid="cfg-1", alg="ed25519", signer=self.auth_sign)

    def policy_doc(self, rules, version=1, expires=T0 + 10**6):
        return self.cfg("policy-bundle", {"schema": "PK_POLICY_BUNDLE/1", "adapter_version": 1, "bundle_id": "acme-prod", "version": version,
                                          "issued_at": T0 - 10, "expires": expires, "tenant": "acme", "rules": rules})

    def slsa(self, digest_hex, builder="https://ci.acme/builder@v1", name="app"):
        st = _dsse.statement([(name, digest_hex)], _dsse.SLSA_V1, {
            "buildDefinition": {"buildType": "https://ci.acme/type/v1", "externalParameters": {"ref": "refs/heads/main"},
                                "resolvedDependencies": [{"uri": "git+https://git.acme/app", "digest": {"gitCommit": "a" * 40}}]},
            "runDetails": {"builder": {"id": builder}, "metadata": {"finishedOn": "2027-01-15T08:00:00Z"}}})
        return _dsse.make_envelope(canonical_bytes(st), [(self.pki.refs["k1"].kid, lambda m: self.pki.custody.sign(self.pki.refs["k1"], m, request_id="t"))])

    def sbom(self, digest_hex, packages=("pkg:pypi/requests@2.0",), vulns=()):
        bom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "components": [{"name": p.split("/")[-1], "purl": p} for p in packages],
               "vulnerabilities": [{"id": f"CVE-{i}", "ratings": [{"severity": s}], "analysis": {"state": "exploitable"}} for i, s in enumerate(vulns)]}
        st = _dsse.statement([("app", digest_hex)], "https://cyclonedx.org/bom", bom)
        return _dsse.make_envelope(canonical_bytes(st), [(self.pki.refs["k1"].kid, lambda m: self.pki.custody.sign(self.pki.refs["k1"], m, request_id="t"))])

    def full_request(self, payload=b"artifact-bytes", kind="code", **kw):
        hexd = _hl.sha256(payload).hexdigest()
        sig = self.builder.sign(payload, kind, now=T0)
        env_digest = _hl.sha256(canonical_bytes(sig)).hexdigest()
        idx = self.log.append(entry_bytes(kind, hexd, env_digest))
        cp = self.log.checkpoint(T0)
        tl = [{"envelope_digest": env_digest, "evidence": {"index": idx, "checkpoint": cp, "proof": self.log.prove_inclusion(idx, cp["size"])}}]
        atts = kw.pop("attestations", None)
        if atts is None:
            atts = [self.slsa(hexd), self.sbom(hexd)]
        bundle = make_bundle("sha256:" + hexd, kind, signatures=[sig], attestations=atts, transparency=tl if kw.pop("tlog", True) else [])
        req = {"digest": "sha256:" + hexd, "kind": kind, "tenant": "acme", "site": "site-a", "environment": "prod", "bundle": bundle}
        req.update(kw)
        return req
