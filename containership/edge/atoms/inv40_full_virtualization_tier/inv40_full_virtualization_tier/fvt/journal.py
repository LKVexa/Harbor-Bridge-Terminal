"""Crash-consistent write-ahead journal for mutable tier state (INV-40-C057, C095).

Record format, one per line:  ``<crc32 hex>\t<canonical json>\n``.  Appends are
fsync'd.  On replay a torn or corrupt tail record (the only corruption an
interrupted append can produce) is discarded and reported; corruption *before*
the tail is a hard error, because it cannot come from a crash.  ``snapshot`` +
``compact`` bound growth; ``export``/``restore`` give backup and restore.
"""
from __future__ import annotations

import json
import os
import pathlib
import zlib


class JournalCorrupt(RuntimeError):
    pass


def _enc(rec: dict) -> bytes:
    body = json.dumps(rec, sort_keys=True, separators=(",", ":")).encode()
    return f"{zlib.crc32(body):08x}\t".encode() + body + b"\n"


class Journal:
    def __init__(self, path: str | os.PathLike):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.torn_tail = False

    def append(self, rec: dict) -> None:
        with open(self.path, "ab") as fh:
            fh.write(_enc(rec))
            fh.flush()
            os.fsync(fh.fileno())

    def replay(self) -> list[dict]:
        if not self.path.exists():
            return []
        data = self.path.read_bytes()
        lines = data.split(b"\n")
        if lines and lines[-1] == b"":
            lines.pop()
        out, self.torn_tail = [], False
        for i, line in enumerate(lines):
            rec = None
            if b"\t" in line:
                crc, body = line.split(b"\t", 1)
                try:
                    if int(crc, 16) == zlib.crc32(body):
                        rec = json.loads(body)
                        if not isinstance(rec, dict) or not isinstance(rec.get("instance_id", ""), str) \
                                or (rec.get("op") == "snapshot" and not isinstance(rec.get("state"), dict)):
                            raise JournalCorrupt(f"record {i} is not a journal object")  # D-02
                except (ValueError, json.JSONDecodeError):
                    rec = None
            if rec is None:
                if i == len(lines) - 1:  # only the final record can be torn by a crash
                    self.torn_tail = True
                    break
                raise JournalCorrupt(f"corrupt record {i} before tail")
            out.append(rec)
        return out

    def state(self) -> dict[str, dict]:
        """Fold records into per-guest state (last write wins; 'destroyed' removes)."""
        st: dict[str, dict] = {}
        for r in self.replay():
            if r.get("op") == "snapshot":
                st = {k: dict(v) for k, v in r["state"].items()}
            elif "instance_id" not in r:
                raise JournalCorrupt("record without instance_id")
            elif r.get("state") == "destroyed":
                st.pop(r["instance_id"], None)
            else:
                st.setdefault(r["instance_id"], {}).update(r)
        return st

    def compact(self) -> None:
        st = self.state()
        tmp = self.path.with_suffix(".compact")
        with open(tmp, "wb") as fh:
            fh.write(_enc({"op": "snapshot", "state": st}))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)

    def export(self, dest: str | os.PathLike) -> None:
        self.compact()
        pathlib.Path(dest).write_bytes(self.path.read_bytes())

    @classmethod
    def restore(cls, backup: str | os.PathLike, path: str | os.PathLike) -> "Journal":
        j = cls(backup)
        j.replay()
        if j.torn_tail:
            raise JournalCorrupt("backup is torn")
        pathlib.Path(path).write_bytes(pathlib.Path(backup).read_bytes())
        return cls(path)
