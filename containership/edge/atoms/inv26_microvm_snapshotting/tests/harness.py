"""Shared test/benchmark harness: builds a fully wired service with real crypto,
a real durable metastore (tmp dir), a real audit ledger, EdDSA credentials and
restore grants, and the reference hypervisor (or a supplied adapter)."""
from __future__ import annotations

import io
import secrets
import tempfile
import time
from pathlib import Path

from inv26_microvm_snapshotting import config as config_mod
from inv26_microvm_snapshotting.audit import AuditLog
from inv26_microvm_snapshotting.auth import Authenticator, Signer, TrustedKey, TrustStore
from inv26_microvm_snapshotting.config import ConfigStore
from inv26_microvm_snapshotting.crypto import LocalKeyService
from inv26_microvm_snapshotting.hypervisor import ReferenceEntropyInjector, ReferenceHypervisor
from inv26_microvm_snapshotting.metastore import MetaStore
from inv26_microvm_snapshotting.service import SnapshotService
from inv26_microvm_snapshotting.storage import FilesystemBlobStore, MemoryBlobStore
from inv26_microvm_snapshotting.telemetry import Metrics, StructuredLogger

DEVICES = ["virtio-block", "virtio-net"]
ENV, SITE, NODE = "prod", "site-a", "node-1"
AUDIENCE = "inv26.site-a.prod"


class Rig:
    def __init__(self, root: str | None = None, *, cfg_over: dict | None = None, fs_blobs: bool = True,
                 hv=None, entropy=None, clock=time.time, mem_meta: bool = False):
        self.root = Path(root or tempfile.mkdtemp(prefix="inv26-rig-"))
        self.clock = clock
        self.meta = MetaStore(None if mem_meta else self.root / "meta", clock=clock)
        self.audit_stream = io.StringIO()
        self.audit = AuditLog(self.root / "audit.jsonl", mac_key=b"k" * 32, clock=clock)
        self.cfgstore = ConfigStore(self.meta, audit=self.audit)
        self.hv = hv or ReferenceHypervisor()
        doc = config_mod.example("reference", environment=ENV, auth={"audience": AUDIENCE})
        doc["runtime"] = {"adapter": self.hv.name, "version": self.hv.version, "arch": self.hv.arch}
        doc["storage"] = {"kind": "filesystem", "root": str(self.root / "blobs"), "quota_bytes": 1 << 34}
        doc["metadata"] = {"root": str(self.root / "meta")}
        for k, v in (cfg_over or {}).items():
            if isinstance(v, dict) and isinstance(doc.get(k), dict):
                doc[k] = dict(doc[k], **v)
            else:
                doc[k] = v
        if self.cfgstore.active() is None:
            self.cfgstore.activate(doc, author="test", source="harness", approval_ref="T-1", expect_revision=0)
        self.blobs = FilesystemBlobStore(self.root / "blobs") if fs_blobs else MemoryBlobStore()
        self.kms = LocalKeyService()
        self.kms.create("inv26-kek")
        self.entropy = entropy or (ReferenceEntropyInjector(self.hv) if isinstance(self.hv, ReferenceHypervisor)
                                   else None)
        self.trust = TrustStore()
        self.caller, pub = Signer.ed25519("caller-1")
        self.trust.add(TrustedKey("caller-1", "EdDSA", pub, "caller", f"{ENV}/{SITE}"))
        self.issuer, gpub = Signer.ed25519("grant-1")
        self.trust.add(TrustedKey("grant-1", "EdDSA", gpub, "grant-issuer", f"{ENV}/{SITE}"))
        self.authn = Authenticator(self.trust, audience=AUDIENCE, environment=ENV, site=SITE, clock=clock)
        self.metrics = Metrics()
        self.logstream = io.StringIO()
        self.logger = StructuredLogger(stream=self.logstream)
        self.svc = self.build()

    def build(self, **kw):
        return SnapshotService(meta=self.meta, config=self.cfgstore, blobs=self.blobs, kms=self.kms,
                               hypervisor=self.hv, entropy=self.entropy, authn=self.authn, audit=self.audit,
                               node_id=NODE, metrics=self.metrics, logger=self.logger,
                               workdir=str(self.root / "work"), sleep=lambda s: None, clock=self.clock, **kw)

    # ------------------------------------------------------------ credentials
    def token(self, tenant="t1", workload="w1", caps=("snapshot.capture", "snapshot.restore", "snapshot.inspect"),
              env=ENV, site=SITE, aud=AUDIENCE, ttl=300, now=None, signer=None, extra=None, sub="svc-a"):
        now = self.clock() if now is None else now
        claims = {"sub": sub, "aud": aud, "env": env, "site": site, "iat": now, "nbf": now, "exp": now + ttl,
                  "jti": secrets.token_hex(8),
                  "caps": [{"cap": c, "tenant": tenant, "workload": workload, "environment": env} for c in caps]}
        claims.update(extra or {})
        return (signer or self.caller).sign(claims)

    def admin_token(self, **kw):
        return self.token(caps=(), extra={"caps": [{"cap": c, "tenant": "*", "workload": "*", "environment": "*"}
                                                   for c in ("snapshot.admin",)] +
                                          [{"cap": c, "tenant": kw.pop("tenant", "t1"), "workload": "w1",
                                            "environment": ENV}
                                           for c in ("snapshot.delete", "snapshot.quarantine", "snapshot.inspect")]},
                          sub="operator-1", **kw)

    def grant(self, snap: dict, *, vm="vm-2", tenant=None, node=NODE, ttl=60, nonce=None, **over):
        now = self.clock()
        claims = {"op": "restore", "snapshot_id": snap["snapshot_id"], "manifest_sha256": snap["manifest_sha256"],
                  "tenant": tenant or snap["tenant"], "workload": snap["workload"], "environment": snap["environment"],
                  "node": node, "target_vm_id": vm, "action": "restore", "generation": snap["generation"],
                  "iat": now, "nbf": now, "exp": now + ttl, "nonce": nonce or secrets.token_hex(16),
                  "aud": AUDIENCE, "env": ENV, "site": SITE}
        claims.update(over)
        return self.issuer.sign(claims)

    # ------------------------------------------------------------ requests
    def boot(self, vm="vm-1", memory=b"guest-memory" * 100):
        self.hv.boot(vm, memory)

    def capture_req(self, sid="s1", tenant="t1", vm="vm-1", idem=None, **over):
        r = {"schema": "PK_SNAPSHOT_CAPTURE_REQUEST/2", "snapshot_id": sid, "tenant": tenant, "workload": "w1",
             "environment": ENV, "devices": list(DEVICES), "memory_mib": 256, "vm_id": vm,
             "idempotency_key": idem or secrets.token_hex(8)}
        r.update(over)
        return r

    def restore_req(self, snap: dict, grant: str, vm="vm-2", idem=None, **over):
        r = {"schema": "PK_SNAPSHOT_RESTORE_REQUEST/2", "snapshot_id": snap["snapshot_id"], "tenant": snap["tenant"],
             "workload": snap["workload"], "environment": snap["environment"], "devices": list(DEVICES),
             "target_vm_id": vm, "grant": grant, "idempotency_key": idem or secrets.token_hex(8)}
        r.update(over)
        return r

    def capture(self, sid="s1", tenant="t1", vm="vm-1", **over):
        if vm not in self.hv.vms:
            self.boot(vm)
        st, body = self.svc.handle("capture", self.token(tenant=tenant), self.capture_req(sid, tenant, vm, **over))
        assert st == 200, body
        return body

    def restore(self, snap, vm="vm-2", token=None, grant=None, **over):
        grant = grant or self.grant(snap, vm=vm)
        return self.svc.handle("restore", token or self.token(tenant=snap["tenant"]),
                               self.restore_req(snap, grant, vm=vm, **over))
