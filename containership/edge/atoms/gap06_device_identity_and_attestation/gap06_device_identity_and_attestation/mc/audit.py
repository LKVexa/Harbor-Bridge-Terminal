"""MC-13: tamper-evident security audit ledger.

Each event = canonical JSON {seq, prev, type, at, fields}; ``hash`` = sha256 of it;
every event is Ed25519-signed through the KeyStore.  ``verify`` recomputes the
chain and every signature, and checks the externally anchored head (tail
truncation is invisible to a hash chain alone, so heads must be anchored
elsewhere -- ``anchor()`` returns the value to publish).  Field values are
redacted before they are written.
"""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from pathlib import Path

from . import algorithms as alg
from .errors import fail, redact

EVENT_TYPES = {"enroll", "challenge", "verdict", "reject", "policy_change", "revocation", "replay_rejected",
               "quarantine", "release_quarantine", "key_rotation", "config_change", "waiver", "restore", "authz_denied"}


@dataclass
class AuditLedger:
    path: Path
    keystore: object
    key_id: str
    principal: str = "gap06-audit"
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    seq: int = 0
    head: str = "0" * 64

    def __post_init__(self):
        self.path = Path(self.path)
        if self.path.exists():
            for rec in self._read():
                self.seq, self.head = rec["event"]["seq"], rec["hash"]

    def _read(self):
        for line in self.path.read_text("utf-8").splitlines():
            yield json.loads(line)

    def append(self, etype: str, at: float, **fields_) -> dict:
        if etype not in EVENT_TYPES:
            raise fail("E_SCHEMA", f"unknown audit event {etype}")
        with self._lock:
            ev = {"seq": self.seq + 1, "prev": self.head, "type": etype, "at": at,
                  "fields": {k: redact(str(v))[:256] for k, v in sorted(fields_.items())},
                  "key_id": self.key_id}
            body = json.dumps(ev, sort_keys=True, separators=(",", ":")).encode()
            h = hashlib.sha256(body).hexdigest()
            sig = self.keystore.sign(self.key_id, body, principal=self.principal).hex()
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"event": ev, "hash": h, "sig": sig}, sort_keys=True) + "\n")
                f.flush()
            self.seq, self.head = ev["seq"], h
            return ev

    def anchor(self) -> dict:
        return {"seq": self.seq, "head": self.head}

    @staticmethod
    def verify(path, public_keys: dict, anchored: dict | None = None) -> int:
        """Return event count or raise E_LEDGER_TAMPER."""
        prev, seq = "0" * 64, 0
        for line in Path(path).read_text("utf-8").splitlines():
            try:
                rec = json.loads(line)
                ev = rec["event"]
                body = json.dumps(ev, sort_keys=True, separators=(",", ":")).encode()
            except Exception as exc:
                raise fail("E_LEDGER_TAMPER", "unparseable ledger line") from exc
            if ev["seq"] != seq + 1 or ev["prev"] != prev or hashlib.sha256(body).hexdigest() != rec["hash"]:
                raise fail("E_LEDGER_TAMPER", f"chain broken at seq {seq + 1}")
            pem = public_keys.get(ev["key_id"])
            if pem is None:
                raise fail("E_LEDGER_TAMPER", "event signed by unknown key")
            try:
                alg.verify(alg.load_public_key(pem), "ed25519", bytes.fromhex(rec["sig"]), body)
            except Exception as exc:
                raise fail("E_LEDGER_TAMPER", f"bad signature at seq {ev['seq']}") from exc
            prev, seq = rec["hash"], ev["seq"]
        if anchored is not None and (anchored["seq"] > seq or (anchored["seq"] == seq and anchored["head"] != prev)):
            raise fail("E_LEDGER_TAMPER", "ledger shorter than or diverges from anchored head (truncation)")
        return seq
