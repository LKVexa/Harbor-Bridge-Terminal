"""Component 39 - tamper-evident, append-only, hash-chained audit log with
signed checkpoints, monotonic sequence, verification tooling and retention/
legal-hold policy.  Storage is a JSONL file opened in append mode only."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

from .core import TrustRoot, canonical, redact, sha256_hex

SCHEMA = "PK_DYN_AUDIT/1"
GENESIS = "0" * 64
REQUIRED = ("schema", "seq", "ts", "actor", "action", "resource", "outcome", "prev", "hash")


def _entry_hash(body: dict) -> str:
    return sha256_hex(canonical({k: v for k, v in body.items() if k != "hash"}))


class AuditLog:
    def __init__(self, path: str | os.PathLike, *, clock=None) -> None:
        self.path = Path(path)
        self._clock = clock
        self._seq, self._head, self._last_ts = 0, GENESIS, None
        if self.path.exists():
            ok, problems, entries = verify_file(self.path)
            if not ok:
                raise ValueError("refusing to append to a tampered log: " + "; ".join(problems[:3]))
            if entries:
                last = entries[-1]
                self._seq, self._head, self._last_ts = last["seq"], last["hash"], last["ts"]

    @property
    def head(self) -> str:
        return self._head

    def append(self, actor: str, action: str, resource: str, outcome: str,
               details: dict | None = None, ts: float | None = None) -> dict:
        if not actor or not action:
            raise ValueError("actor and action are required")
        if ts is None:
            ts = self._clock() if self._clock else float(self._seq + 1)
        if self._last_ts is not None and ts < self._last_ts:
            raise ValueError("audit timestamps must be non-decreasing")
        body = {"schema": SCHEMA, "seq": self._seq + 1, "ts": ts, "actor": actor,
                "action": action, "resource": resource, "outcome": outcome,
                "details": redact(details or {}), "prev": self._head}
        body["hash"] = _entry_hash(body)
        with open(self.path, "ab") as fh:  # append-only
            fh.write(canonical(body) + b"\n")
            fh.flush()
            os.fsync(fh.fileno())
        self._seq, self._head, self._last_ts = body["seq"], body["hash"], ts
        return body

    def checkpoint(self, trust: TrustRoot, kid: str) -> dict:
        payload = {"schema": SCHEMA + "#checkpoint", "seq": self._seq, "head": self._head}
        return {"checkpoint": payload, "signature": trust.sign(kid, payload)}


def read_entries(path: Path) -> list[dict]:
    out = []
    for n, line in enumerate(path.read_bytes().splitlines(), 1):
        if line.strip():
            try:
                out.append(json.loads(line))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                out.append({"__corrupt__": n, "error": str(exc)})
    return out


def verify_entries(entries: Iterable[dict]) -> tuple[bool, list[str]]:
    problems, prev, seq, last_ts = [], GENESIS, 0, None
    for e in entries:
        if "__corrupt__" in e:
            problems.append(f"line {e['__corrupt__']}: unparseable")
            break
        missing = [k for k in REQUIRED if k not in e]
        if missing:
            problems.append(f"seq {e.get('seq')}: missing {missing}")
            break
        if e["seq"] != seq + 1:
            problems.append(f"sequence gap/reorder at {e['seq']} (expected {seq + 1})")
        if e["prev"] != prev:
            problems.append(f"seq {e['seq']}: chain break")
        if _entry_hash(e) != e["hash"]:
            problems.append(f"seq {e['seq']}: content hash mismatch")
        if last_ts is not None and e["ts"] < last_ts:
            problems.append(f"seq {e['seq']}: timestamp regression")
        prev, seq, last_ts = e["hash"], e["seq"], e["ts"]
    return (not problems), problems


def verify_file(path: Path) -> tuple[bool, list[str], list[dict]]:
    entries = read_entries(Path(path))
    ok, problems = verify_entries(entries)
    return ok, problems, entries


def verify_against_checkpoint(path: Path, cp: dict, trust: TrustRoot) -> tuple[bool, str]:
    """Detects tail truncation, which a bare chain cannot: the signed checkpoint
    pins (seq, head) externally."""
    if not trust.verify(cp["checkpoint"], cp["signature"]):
        return False, "checkpoint signature invalid"
    ok, problems, entries = verify_file(path)
    if not ok:
        return False, problems[0]
    want = cp["checkpoint"]
    if len(entries) < want["seq"]:
        return False, f"log truncated: {len(entries)} < checkpoint seq {want['seq']}"
    if entries[want["seq"] - 1]["hash"] != want["head"] if want["seq"] else False:
        return False, "checkpoint head does not match log"
    return True, "ok"


RETENTION_POLICY = {
    "security_audit": {"retain_days": 400, "export": "JSONL + signed checkpoint", "legal_hold": "suspends deletion"},
    "deletion": "only whole files older than retain_days and not under legal hold; never in-place edits",
}


def may_delete(age_days: float, legal_hold: bool, klass: str = "security_audit") -> bool:
    return (not legal_hold) and age_days > RETENTION_POLICY[klass]["retain_days"]


def main(argv: list[str] | None = None) -> int:
    import sys
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: python -m ...production.audit LOG.jsonl")
        return 64
    ok, problems, entries = verify_file(Path(args[0]))
    print(json.dumps({"ok": ok, "entries": len(entries), "problems": problems}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
