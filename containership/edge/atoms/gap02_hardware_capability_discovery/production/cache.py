"""GAP02-MC-28 — Persistent probe cache (optional, signed, strictly invalidated).

A cache entry is usable only as a *hint* for scheduling the next probe — its
evidence kind is ``cache``, which ``promote()`` never maps to present. It is
discarded outright if signature, boot id, firmware/kernel identity, topology
digest, or max-age do not match.
"""
from __future__ import annotations

import base64
import json
import os
import tempfile

from .errors import Code, Gap02Error
from .evidence import ProbeEvidence


def boot_identity(host=None) -> dict:
    from .evidence import Host
    host = host or Host()
    return {"boot_id": (host.read("/proc/sys/kernel/random/boot_id") or "").strip() or None,
            "kernel": (host.read("/proc/sys/kernel/osrelease") or "").strip() or None,
            "firmware": (host.read("/sys/class/dmi/id/bios_version") or "").strip()[:64] or None}


class ProbeCache:
    def __init__(self, path: str, signer, *, max_age: int = 3600):
        self.path, self.signer, self.max_age = path, signer, max_age

    def _canon(self, d) -> bytes:
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()

    def store(self, snapshot, identity: dict, now: int) -> None:
        if not identity.get("boot_id"):
            raise Gap02Error(Code.PROBE_UNAVAILABLE, "no boot identity; cache disabled")
        body = {"identity": identity, "topology": snapshot.topology_digest, "at": now,
                "states": {c: s for c, (s, _) in snapshot.report.results.items()}}
        rec = {"body": body, "sig": base64.b64encode(self.signer.sign(self._canon(body))).decode(),
               "key_id": self.signer.key_id, "alg": self.signer.alg}
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(self.path)))
        with os.fdopen(fd, "w") as f:
            json.dump(rec, f)
        os.replace(tmp, self.path)

    def load(self, identity: dict, now: int) -> list[ProbeEvidence]:
        try:
            with open(self.path) as f:
                rec = json.loads(f.read(1_000_000))
            body = rec["body"]
            ok = self.signer.verify(rec["key_id"], rec["alg"], self._canon(body), base64.b64decode(rec["sig"]))
        except (OSError, ValueError, KeyError, TypeError):
            return []
        if not ok or body["identity"] != identity or not identity.get("boot_id") \
                or not 0 <= now - int(body["at"]) <= self.max_age:
            return []
        return [ProbeEvidence(c, None, "cache", "probe-cache", {"hint": s}) for c, s in body["states"].items()]
