"""Shared fixtures for the 4.3.0 suites (stdlib only)."""
from __future__ import annotations

import importlib
import os
import pathlib
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pkg = importlib.import_module(PKG_DIR.name)
from pln04_execution_plane import plane as plane_mod  # noqa: E402
from pln04_execution_plane import policy, providers, security  # noqa: E402
from pln04_execution_plane.resilience import RetryPolicy  # noqa: E402

KEY = b"k" * 32
AUD = "pln04"


class FakeClock:
    def __init__(self, t: float = 1_000_000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, s: float) -> None:
        self.t += s


def keyring():
    ring = security.HmacKeyring()
    ring.add("k1", KEY)
    return ring


def request(workload="w1", tenant="t1", trust_class="trusted", **extra):
    doc = {"schema": "PK_ADMISSION/1", "kind": "request", "request_id": f"r-{workload}",
           "workload": workload, "tenant": tenant, "trust_class": trust_class}
    doc.update(extra)
    return doc


def dev_plane(tiers=("process", "wasm", "unikernel", "microvm", "vm"), attest=True, config=None, **kw):
    cfg = policy.PlaneConfig.load(config or {})
    reg = providers.ProviderRegistry(allow_reference=True)
    provs = {}
    for t in tiers:
        provs[t] = providers.ReferenceProvider(t)
        reg.register(provs[t])
    kw.setdefault("retry_policy", RetryPolicy(max_attempts=2, base_s=0.001, cap_s=0.002))
    pl = plane_mod.ExecutionPlane(cfg, reg, **kw)
    if attest:
        for t in tiers:
            pl.attest_tier(t)
    return pl, provs


class StandIn(providers.ReferenceProvider):
    """Test-only stand-in that clears the reference flag so the production wiring can be exercised."""

    reference = False


def secured_plane(tmpdir: str, clock: FakeClock, **cfg_over):
    """Production-profile plane wired with every verifier and durable store/audit."""
    from pln04_execution_plane import observability, store
    ring = keyring()
    signer = ring.signer("k1")
    trusted = security.TrustedClock(clock, max_skew_s=5)
    verifiers = {"HS256": ring}
    att = security.AttestationVerifier(verifiers, trusted, reference_measurements={t: ["m-good"] for t in pkg.TIERS})
    cfg = policy.PlaneConfig.load({"profile": "production", "node_id": "n1", "site": "eu-1", **cfg_over})
    reg = providers.ProviderRegistry(allow_reference=False)
    for t in pkg.TIERS:
        reg.register(StandIn(t))
    arts = security.ArtifactPolicy(verifiers, trusted_builders=["ci"])
    pl = plane_mod.ExecutionPlane(
        cfg, reg,
        store=store.FileStateStore(os.path.join(tmpdir, "state"), fsync=False),
        audit=observability.DurableAuditSink(os.path.join(tmpdir, "audit.jsonl"), fsync=False),
        authenticator=security.Authenticator(verifiers, trusted, audience=AUD),
        classifier=security.ClassificationVerifier(verifiers, trusted, trusted_issuers=["sec-plane"]),
        artifacts=arts, attestor=att, wall=clock)
    for t in pkg.TIERS:
        nonce = att.challenge("n1")
        pl.attest_tier(t, security.issue_attestation(signer, node_id="n1", tier=t, nonce=nonce, measurement="m-good", now=clock()))
    return pl, signer, arts
