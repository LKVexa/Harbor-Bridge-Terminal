"""Secret scan of source, docs, examples and evidence (C039). Uses redaction.classify_text."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..redaction import classify_text

SKIP = {"__pycache__", ".git", "dist", "build"}
ALLOW = {  # deliberate test vectors: path -> reason
    "tests/test_security_units.py": "contains PEM header literal as a negative config test",
    "tests/test_service.py": "contains fake bearer string as a redaction test",
    "redaction.py": "pattern definitions",
    "tools/fuzz.py": "none expected",
}


def scan(root: Path) -> dict:
    hits = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or SKIP & set(p.relative_to(root).parts) or p.suffix in (".pyc", ".whl", ".gz", ".zip"):
            continue
        rel = p.relative_to(root).as_posix()
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            cls = classify_text(line)
            if cls:
                hits.append({"file": rel, "line": i, "class": cls, "allowlisted": rel in ALLOW})
    bad = [h for h in hits if not h["allowlisted"]]
    return {"schema": "PK_SNAPSHOT_SECRET_SCAN/1", "hits": hits, "unallowlisted": len(bad),
            "result": "PASS" if not bad else "FAIL"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = scan(Path(a.root))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({"result": res["result"], "hits": len(res["hits"]), "unallowlisted": res["unallowlisted"]}))
    return 0 if res["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
