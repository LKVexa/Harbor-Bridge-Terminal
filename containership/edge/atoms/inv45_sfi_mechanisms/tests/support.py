"""Shared test harness: builds a fully wired SfiService in a temp dir with real keys."""
from __future__ import annotations

import os
import pathlib
import secrets
import sys
import tempfile

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]  # .../inv45_sfi_mechanisms
if str(PKG_DIR.parent) not in sys.path:
    sys.path.insert(0, str(PKG_DIR.parent))

from inv45_sfi_mechanisms.production import authz, builder, engine, service, trust  # noqa: E402
from inv45_sfi_mechanisms.production.authz import Grant  # noqa: E402

ALL = sorted(authz.CAPABILITIES)


def node_available() -> bool:
    try:
        return engine.preflight(None)["ok"]
    except Exception:  # pragma: no cover
        return False


class Harness:
    def __init__(self, with_engine: bool = False, root: pathlib.Path | None = None):
        self._tmp = None
        if root is None:
            self._tmp = tempfile.TemporaryDirectory(prefix="inv45-test-")
            root = pathlib.Path(self._tmp.name)
        self.root = root
        suffix = secrets.token_hex(4)
        self.seal_env = f"INV45_TEST_SEAL_{suffix}"
        self.idp_env = f"INV45_TEST_IDP_{suffix}"
        os.environ[self.seal_env] = secrets.token_hex(32)
        os.environ[self.idp_env] = secrets.token_hex(32)
        self.keyring = trust.KeyRing()
        self.keyring.add(trust.HmacKey("seal-1", trust.SecretRef("env:" + self.seal_env)), activate=True)
        self.signer, pub = trust.new_ed25519()
        self.trust_store = trust.ArtifactTrustStore()
        self.trust_store.add(trust.TrustRoot("ci-1", pub, "ci.example"))
        self.idp = authz.IdentityProvider(trust.SecretRef("env:" + self.idp_env))
        eng = engine.NodeV8Engine(timeout=10.0, expected_major=None) if with_engine else None
        self.svc = service.SfiService(root=root, keyring=self.keyring, trust_store=self.trust_store,
                                      idp=self.idp, engine=eng)

    def token(self, subject="op", kind="human", tenant=None, caps=None, **kw):
        caps = ALL if caps is None else caps
        return self.idp.mint(subject, kind, tenant, [Grant(c, **kw) for c in caps])

    def tenant_token(self, tenant, caps=("sfi.submit", "sfi.load", "sfi.execute")):
        return self.idp.mint(f"svc-{tenant}", "service", tenant, [Grant(c, tenant=tenant) for c in caps])

    def sign(self, artifact: bytes, workload="wl", version=1):
        return trust.sign_statement(self.signer, "ci-1", artifact, workload=workload, version=version,
                                    issuer="ci.example")

    def submit(self, artifact=None, tenant="t1", workload="wl", version=1, token=None):
        artifact = artifact if artifact is not None else builder.rw_module(memory_pages=4)
        token = self.tenant_token(tenant) if token is None else token
        return self.svc.submit(token, artifact, tenant=tenant, workload=workload, version=version,
                               signed_statement=self.sign(artifact, workload, version))

    def close(self):
        for k in (self.seal_env, self.idp_env):
            os.environ.pop(k, None)
        if self._tmp:
            self._tmp.cleanup()
