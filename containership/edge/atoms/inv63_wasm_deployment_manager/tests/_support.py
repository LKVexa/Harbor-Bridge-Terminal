"""Shared fixtures and C-ID tagging for INV-63 tests."""
import importlib
import json
import pathlib
import sys
import tempfile

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pkg = importlib.import_module(PKG_DIR.name)
P = PKG_DIR.name


def mod(name):
    return importlib.import_module(f"{P}.{name}")


def covers(*cids):
    """Tag a test with the INV-63 C-IDs it evidences (read by audit.py)."""
    def deco(fn):
        fn.__inv63__ = tuple(f"INV-63-C{int(c):03d}" if str(c).isdigit() else c for c in cids)
        return fn
    return deco


class FakeClock:
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


HOSTS = {"h1": "z1", "h2": "z2", "h3": "z3", "h4": "z1"}


def make_env(tmp=None, *, config_over=None, hosts=None, signed=True):
    security = mod("security")
    config = mod("config")
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    tmp = tmp or tempfile.mkdtemp(prefix="inv63-")
    clock = FakeClock()
    mono = FakeClock(1000.0)
    over = {"environment": "prod", "site": "test", "residency_labels": {"h1": "eu", "h2": "eu", "h3": "us", "h4": "us"},
            "trusted_key_ids": ["rel-1"]}
    over.update(config_over or {})
    cfg = config.compose(over)
    priv = Ed25519PrivateKey.generate()
    verifier = security.ArtifactVerifier({"rel-1": priv.public_key()})
    tokens = security.TokenAuthority({"k1": b"k" * 32}, clock=clock)
    lattice = mod("adapter").InMemoryLattice(hosts or HOSTS)
    sealer = security.Sealer({"d1": b"\x11" * 32})
    journal = mod("store").Journal(pathlib.Path(tmp) / "state", clock=clock, sealer=sealer)
    svc = mod("service").DeploymentService(config=cfg, hosts=hosts or HOSTS, adapter=lattice, journal=journal,
                                           tokens=tokens, verifier=verifier, clock=clock, mono=mono)
    env = type("Env", (), {})()
    env.__dict__.update(dict(tmp=tmp, clock=clock, mono=mono, cfg=cfg, priv=priv, verifier=verifier, tokens=tokens,
                             lattice=lattice, journal=journal, svc=svc, security=security, sealer=sealer,
                             operator=security.Principal("oncall", "*", frozenset({"sre-operator"}))))
    return env


_n = [0]


def req(env, op, body, *, roles=("tenant-deployer",), tenant="acme", key=None, subject="alice", token=None, **extra):
    security = env.security
    _n[0] += 1
    if token is None:
        token = env.tokens.issue(security.Principal(subject, tenant, frozenset(roles)))
    r = {"schema": "PK_DEPLOY_REQUEST/1", "op": op, "token": token,
         "idempotency_key": key or f"req-{_n[0]:08d}", "body": body}
    r.update(extra)
    return env.svc.handle(json.dumps(r).encode())


def desired(env, component="api", version="v1", count=3, tenant="acme", **kw):
    security = env.security
    art = security.sign_artifact(env.priv, "rel-1", component, version, f"{component}-{version}".encode(),
                                 provenance="ci://build/1")
    body = {"schema": "PK_DEPLOY_DESIRED/2", "tenant": tenant, "component": component, "version": version,
            "count": count, "spread": True, "artifact": art}
    body.update(kw)
    return body
