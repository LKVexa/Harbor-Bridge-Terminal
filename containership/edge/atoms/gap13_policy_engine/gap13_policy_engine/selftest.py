"""Self-test loader used by the pk_core conformance adapter (no pk_core dependency)."""
from __future__ import annotations


def selftest_load(engine, rules, version, now=0):
    """Load ``rules`` through the real verification path using an ephemeral self-test key.

    5.0.0: engines no longer accept ``{"verified": True}``; the conformance
    harness signs a throwaway bundle and verifies it like production would.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    from .tools.sign_bundle import sign
    from .verify import BundleVerifier, StaticTrustSource, TrustStore, TrustedKey
    sk = Ed25519PrivateKey.generate()
    seed = sk.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                            serialization.NoEncryption())
    pk = sk.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    doc = {"schema": "PK_POLICY_BUNDLE/1", "bundle_id": f"selftest-{version}", "policy_id": "selftest",
           "issuer": "selftest", "generation": 1, "issued_at": 0, "environment": engine.environment,
           "version": version,
           "rules": [{"name": r.name, "effect": r.effect, "scope": r.scope, "match": dict(r.match)} for r in rules]}
    store = TrustStore("selftest", {"st": TrustedKey("st", "ed25519", pk, "selftest", (engine.environment,), 0, 2**40)})
    res = BundleVerifier(StaticTrustSource(store), environment=engine.environment,
                         max_trust_store_age=None).verify(sign(doc, seed, "st"), now=0)
    return engine.load(list(res.bundle.rules), version, res, now=now) if res.verified else engine.load(rules, version, None)
