"""SIEM / security-lake export with durable checkpointing (MC-014-T07, MC-070-T06).

``SiemExporter.run_once()`` reads journal records after the durable checkpoint,
ships them in batches to ``sink(batch)`` and advances the checkpoint only after the
sink acknowledges.  Each batch carries ``batch_id = "<first_seq>-<last_seq>"`` so a
receiver can deduplicate a re-sent batch after a lost acknowledgement (at-least-once
with idempotent receipt).  Sink failures are retried with the shared retry policy;
after ``max_failures`` consecutive failed runs the batch is recorded in the
dead-letter file (range only — the records stay in the journal) and the exporter
keeps retrying from the same checkpoint, so nothing is ever skipped silently.
Memory is bounded by ``batch_size``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .errors import EcpError
from .util import atomic_write, canonical_json


class SiemExporter:
    def __init__(self, journal, state_dir: Path, sink: Callable[[dict[str, Any]], None], *,
                 batch_size: int = 500, max_failures: int = 5):
        self.journal = journal
        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.sink = sink
        self.batch_size = batch_size
        self.max_failures = max_failures
        self.failures = 0

    @property
    def checkpoint(self) -> int:
        p = self.dir / "checkpoint.json"
        return json.loads(p.read_bytes())["last_seq"] if p.exists() else 0

    def _save(self, seq: int) -> None:
        atomic_write(self.dir / "checkpoint.json", canonical_json({"last_seq": seq}))

    def backlog(self) -> int:
        return max(0, self.journal.head[0] - self.checkpoint)

    def run_once(self) -> dict[str, Any]:
        start = self.checkpoint + 1
        batch = []
        for rec in self.journal.records(start):
            batch.append({k: v for k, v in rec.items() if k != "sealed"} | ({"body": self.journal.body(rec)}
                                                                             if "sealed" in rec else {}))
            if len(batch) >= self.batch_size:
                break
        if not batch:
            return {"sent": 0, "checkpoint": start - 1, "backlog": 0}
        env = {"schema": "PK_ECP_SIEM_BATCH/1", "batch_id": f"{batch[0]['seq']}-{batch[-1]['seq']}",
               "records": batch, "head_hash": batch[-1]["hash"]}
        try:
            self.sink(env)
        except Exception as e:  # noqa: BLE001 - any sink failure keeps the checkpoint
            self.failures += 1
            if self.failures >= self.max_failures:
                with (self.dir / "dead_letter.jsonl").open("a") as fh:
                    fh.write(json.dumps({"batch_id": env["batch_id"], "error": type(e).__name__}) + "\n")
            raise EcpError("ECP_DEPENDENCY_UNAVAILABLE", "SIEM sink failed", dependency="siem",
                           count=self.failures) from None
        self.failures = 0
        self._save(batch[-1]["seq"])
        return {"sent": len(batch), "batch_id": env["batch_id"], "checkpoint": batch[-1]["seq"],
                "backlog": self.backlog()}
