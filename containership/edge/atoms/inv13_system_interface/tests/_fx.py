"""Shared fixtures for the v4.3.0 host-layer suites (stdlib only)."""
import os, pathlib, secrets, sys, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv13_system_interface.host import identity, policy  # noqa: E402

KEY = b"k" * 32
CP_KEY = b"c" * 32
AUD = "inv13-host"


def keyring():
    return identity.KeyRing({"k1": KEY})


def gate(**kw):
    return identity.IdentityGate(keyring(), audience=AUD, clock=time.time, **kw)


def token(role="runtime", workload="api", ttl=300, **extra):
    return keyring().sign("k1", {"sub": f"{role}-node-1", "role": role, "workload": workload, "aud": AUD,
                                 "exp": time.time() + ttl, "nonce": secrets.token_hex(12), **extra})


def policy_doc(root_a, root_b="/srv/tenant-b"):
    return {"schema": "INV13_POLICY/1", "tenants": {
        "tenant-a": {"host_roots": [root_a], "rules": [
            {"id": "a-files", "workload": "api*", "world": "batch-file-worker",
             "capabilities": ["filesystem", "wall-clock", "monotonic-clock", "stdio"],
             "preopens": {"/data": {"host_root": root_a, "rights": ["read", "write", "create", "list"]}}},
            {"id": "a-entropy", "workload": "rng-*", "world": "entropy-consumer",
             "capabilities": ["random", "wall-clock", "monotonic-clock", "stdio"]}]},
        "tenant-b": {"host_roots": [root_b], "rules": []}}}


def tmpdir():
    return pathlib.Path(tempfile.mkdtemp(prefix="inv13-"))
