"""Verify evidence/pk_evidence.jsonl (M30): schema, hash chain, head, and that
every cited artifact still has the recorded digest."""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
    __package__ = "inv65_capability_providers.tools"

from ..schemas import validate, load  # noqa: E402

PKG = pathlib.Path(__file__).resolve().parents[1]
GENESIS = "0" * 64


def rec_digest(r: dict) -> str:
    return hashlib.sha256(json.dumps({k: v for k, v in r.items() if k != "digest"}, sort_keys=True).encode()).hexdigest()


def verify(path=PKG / "evidence/pk_evidence.jsonl", expected_head: str | None = None) -> tuple[bool, list[str], str]:
    errs, prev = [], GENESIS
    schema = load("evidence_record")
    lines = [l for l in pathlib.Path(path).read_text().splitlines() if l.strip()]
    for i, l in enumerate(lines):
        r = json.loads(l)
        errs += [f"rec {i}: {e}" for e in validate(r, schema)]
        if r.get("prev") != prev:
            errs.append(f"rec {i}: chain break")
        if rec_digest(r) != r.get("digest"):
            errs.append(f"rec {i}: digest mismatch")
        art = PKG / r["artifact"]
        if not art.exists() or hashlib.sha256(art.read_bytes()).hexdigest() != r["artifact_digest"]:
            errs.append(f"rec {i}: artifact {r['artifact']} missing or changed")
        prev = r.get("digest", "")
    if expected_head and prev != expected_head:
        errs.append("head mismatch")
    return not errs, errs, prev


if __name__ == "__main__":
    ok, errs, head = verify()
    print(json.dumps({"ok": ok, "head": head, "errors": errs[:20]}))
    sys.exit(0 if ok else 1)
