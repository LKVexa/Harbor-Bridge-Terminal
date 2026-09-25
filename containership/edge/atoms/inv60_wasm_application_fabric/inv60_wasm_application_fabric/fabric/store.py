"""M47 - durable desired/observed state: write-ahead log + atomic snapshots.

Every mutation is appended to a WAL (fsync) before being applied. Snapshots are
written atomically (tmp + fsync + rename) and truncate the WAL logically by
recording the last applied sequence. On restart: load snapshot, replay WAL
entries with seq > snapshot seq, ignore a torn final line (crash mid-write).
Replay is deterministic and idempotent.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

SCHEMA = "inv60.state/1"


class StateStore:
    def __init__(self, directory: str | os.PathLike):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.wal = self.dir / "state.wal"
        self.snap = self.dir / "state.snapshot.json"
        self.state: dict = {"schema": SCHEMA, "components": {}, "links": {}, "hosts": {}, "config_generation": 0}
        self.seq = 0
        self.torn_lines = 0
        self._recover()

    # -- mutation --------------------------------------------------
    def apply(self, op: str, **args) -> int:
        self.seq += 1
        entry = {"seq": self.seq, "op": op, "args": args}
        with open(self.wal, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self._apply(entry)
        return self.seq

    def _apply(self, e: dict) -> None:
        op, a, s = e["op"], e["args"], self.state
        if op == "component.put":
            s["components"][a["name"]] = a["record"]
        elif op == "component.del":
            s["components"].pop(a["name"], None)
            for k in [k for k in s["links"] if k.startswith(a["name"] + "|")]:
                del s["links"][k]
        elif op == "link.put":
            s["links"][a["component"] + "|" + a["link"]] = a["record"]
        elif op == "link.del":
            s["links"].pop(a["component"] + "|" + a["link"], None)
        elif op == "host.put":
            s["hosts"][a["name"]] = a["record"]
        elif op == "host.del":
            s["hosts"].pop(a["name"], None)
        elif op == "config.generation":
            s["config_generation"] = max(s["config_generation"], int(a["generation"]))
        else:
            raise ValueError(f"unknown op {op}")

    def snapshot(self) -> None:
        tmp = self.snap.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"seq": self.seq, "state": self.state}, fh, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.snap)

    # -- recovery --------------------------------------------------
    def _recover(self) -> None:
        if self.snap.exists():
            data = json.loads(self.snap.read_text())
            self.seq, self.state = data["seq"], data["state"]
        if self.wal.exists():
            lines = self.wal.read_text().split("\n")
            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    if i >= len(lines) - 2:     # torn tail from a crash mid-append
                        self.torn_lines += 1
                        continue
                    raise
                if e["seq"] > self.seq:
                    self._apply(e)
                    self.seq = e["seq"]
