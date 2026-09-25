"""M42 configuration provenance store, M43 atomic activation, M44 reconstruction.

Every signed policy bundle ever activated is recorded, hash-chained, with who
activated it and why.  Activation is verify -> parse -> epoch check -> single
reference swap (``Gate.activate``); a failed step leaves the old config live.
``reconstruct`` rebuilds the exact bundle active at any epoch from the store,
so historical attestations remain interpretable after upgrades (M42/M44).
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from .attest import Verifier, open_signed_bundle
from .errors import Code, InvalidModule
from .registry import PolicyBundle, load_bundle


class ConfigStore:
    def __init__(self, path: str):
        self.path = path

    def _records(self) -> list[dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def head(self) -> str:
        recs = self._records()
        return recs[-1]["record_hash"] if recs else "0" * 64

    def activate(self, gate, envelope: str, verifier: Verifier, *, actor: str, reason: str) -> PolicyBundle:
        raw = open_signed_bundle(envelope, verifier)      # signature first
        bundle = load_bundle(raw)                         # strict schema second
        gate.activate(bundle)                             # epoch + atomic swap third
        rec = {"schema": "PK_CONFIG_RECORD/1", "epoch": bundle.epoch, "bundle_revision": bundle.revision,
               "envelope": envelope, "actor": actor, "reason": reason, "prev": self.head()}
        rec["record_hash"] = hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return bundle

    def verify(self) -> bool:
        prev = "0" * 64
        for rec in self._records():
            body = {k: v for k, v in rec.items() if k != "record_hash"}
            if rec["prev"] != prev or hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != rec["record_hash"]:
                return False
            prev = rec["record_hash"]
        return True

    def reconstruct(self, epoch: int, verifier: Verifier) -> PolicyBundle:
        if not self.verify():
            raise InvalidModule(Code.REGISTRY_INVALID, "config store chain broken")
        for rec in self._records():
            if rec["epoch"] == epoch:
                b = load_bundle(open_signed_bundle(rec["envelope"], verifier))
                if b.revision != rec["bundle_revision"]:
                    raise InvalidModule(Code.REGISTRY_INVALID, "reconstructed revision mismatch")
                return b
        raise InvalidModule(Code.REGISTRY_INVALID, f"no configuration recorded for epoch {epoch}")
