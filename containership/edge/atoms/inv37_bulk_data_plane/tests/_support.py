"""Shared test fixtures.  Every test runs with stdlib only; nothing is skipped
for a missing optional dependency except the pk_core adapter tests."""
from __future__ import annotations

import importlib
import json
import os
import pathlib
import sys
import tempfile

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pkg = importlib.import_module(PKG_DIR.name)
C = pkg.config
S = pkg.security
ALL_DATA = ["create-transfer", "attach-buffer", "write-chunk", "read-progress", "resume", "finalize", "cancel"]
ADMIN = ["quarantine", "release", "inspect", "administer", "freeze"]


class Env:
    """Temp dir with a key file, checkpoint dir and an activated config."""

    def __init__(self, overrides=None, *, checkpoint=True, caps=None):
        self.tmp = tempfile.TemporaryDirectory()
        d = pathlib.Path(self.tmp.name)
        self.dir = d
        self.key_file = d / "keys.json"
        self.key_file.write_text(json.dumps({"keys": {"k1": os.urandom(32).hex()}, "active": "k1"}))
        os.chmod(self.key_file, 0o600)
        (d / "ck").mkdir()
        layer = {"security": {"key_file": str(self.key_file)},
                 "checkpoint": {"directory": str(d / "ck"), "enabled": checkpoint, "fsync": True},
                 "limits": {"host_memory_budget": "64GiB", "max_mapped_bytes": "4GiB"}}
        for k, v in (overrides or {}).items():
            layer.setdefault(k, {}).update(v) if isinstance(v, dict) else layer.__setitem__(k, v)
        self.caps = caps if caps is not None else pkg.shm_transport.probe()
        self.mgr = C.ConfigManager(probe=self.caps, history_path=d / "config-history.json")
        self.cfg = self.mgr.build([("site", C.load_layer(layer, layer="site"))], author="test")
        self.mgr.activate(self.cfg)
        self.ring = S.KeyRing.from_file(self.key_file)

    def plane(self, **kw):
        return pkg.BulkDataPlane(self.cfg, keyring=self.ring, caps=self.caps, **kw)

    def token(self, tenant="acme", actions=ALL_DATA, **kw):
        return S.mint(self.ring, sub=kw.pop("sub", f"wl-{tenant}"), tenant=tenant, actions=actions, **kw)

    def admin(self, **kw):
        return S.mint(self.ring, sub="operator", tenant="*", actions=ADMIN, **kw)

    def close(self):
        self.tmp.cleanup()
