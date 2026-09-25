"""Source-corpus provenance, extraction and drift check (MC-01).

    python -m inv64_application_model.tools.source_integrity            # verify (CI)
    python -m inv64_application_model.tools.source_integrity --write    # regenerate derived files

Normalization before hashing (documented in provenance/master-source.json):
UTF-8 decode (strict), strip a leading BOM, CRLF/CR -> LF, strip trailing
whitespace on each line, exactly one trailing LF.

Checks (each failure is listed; exit 1 on any):

1. every source recorded in ``provenance/master-source.json`` exists and its
   normalized SHA-256 equals the recorded digest;
2. no two recorded sources share a logical name with different digests;
3. the extracted item ledger ``source/items.json`` regenerates byte-identically
   (generated-output drift);
4. item IDs are unique;
5. every normative clause (every ``MC-nn`` section) maps to an entry in
   ``COMPONENTS_STATUS.json`` and every item ID has a ledger status.

Missing sources (``MASTER.md``) are carried as BLOCKED entries, not hidden.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROV = ROOT / "provenance" / "master-source.json"
ITEMS = ROOT / "source" / "items.json"
STATUS = ROOT / "COMPONENTS_STATUS.json"

_MC = re.compile(r"^## (MC-\d{2}) — (.+)$")
_SUB = re.compile(r"^### (Required deliverables|Engineering / implementation checklist|Acceptance / closure criteria)")
_ITEM = re.compile(r"^- \[[ x]\] (.+)$")
_KIND = {"Required deliverables": "D", "Engineering / implementation checklist": "E",
         "Acceptance / closure criteria": "A"}


def normalize(raw: bytes) -> bytes:
    text = raw.decode("utf-8")
    if text.startswith("﻿"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]
    return ("\n".join(lines).rstrip("\n") + "\n").encode("utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(normalize(path.read_bytes())).hexdigest()


def extract(path: Path) -> list[dict]:
    items: list[dict] = []
    mc, kind, n, severity = None, None, 0, None
    for line in normalize(path.read_bytes()).decode().split("\n"):
        m = _MC.match(line)
        if m:
            mc, kind, n, severity = m.group(1), None, 0, None
            continue
        if mc and line.startswith("**Severity:**"):
            severity = line.split("**Severity:**", 1)[1].strip()
        s = _SUB.match(line)
        if s and mc:
            kind, n = _KIND[s.group(1)], 0
            continue
        if line.startswith("# "):
            mc, kind = None, None
            continue
        it = _ITEM.match(line)
        if it and mc and kind:
            n += 1
            items.append({"id": f"{mc}.{kind}{n:02d}", "mc": mc, "kind": kind, "severity": severity,
                          "text": it.group(1)})
    return items


def render(items: list[dict], source_name: str, source_digest: str) -> bytes:
    doc = {"format": "PK_APP_SOURCE_ITEMS/1", "source": source_name, "source_sha256": source_digest,
           "count": len(items), "items": items}
    return (json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


def check(write: bool = False) -> list[str]:
    errors: list[str] = []
    prov = json.loads(PROV.read_text(encoding="utf-8"))
    names: dict[str, str] = {}
    primary = None
    for s in prov["sources"]:
        p = ROOT / s["path"]
        if not p.is_file():
            errors.append(f"missing source {s['path']}")
            continue
        d = digest(p)
        if write:
            s["sha256"] = d
        elif d != s["sha256"]:
            errors.append(f"digest mismatch for {s['path']}: recorded {s['sha256'][:12]} actual {d[:12]}")
        if s["name"] in names and names[s["name"]] != d:
            errors.append(f"ambiguous copies of logical source {s['name']}")
        names[s["name"]] = d
        if s.get("extract"):
            primary = (p, s["name"], d)
    if write:
        PROV.write_text(json.dumps(prov, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if primary is None:
        errors.append("no extractable normative source recorded")
        return errors
    items = extract(primary[0])
    rendered = render(items, primary[1], primary[2])
    if write:
        ITEMS.write_bytes(rendered)
    elif not ITEMS.is_file() or ITEMS.read_bytes() != rendered:
        errors.append("source/items.json drifted from the source (run --write and commit)")
    ids = [i["id"] for i in items]
    if len(ids) != len(set(ids)):
        errors.append("duplicate item ids")
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    mapped = {c["id"] for c in status["components"]}
    for mc in sorted({i["mc"] for i in items}):
        if mc not in mapped:
            errors.append(f"normative clause {mc} not mapped in COMPONENTS_STATUS.json")
    ledger = ROOT / "evidence" / "ITEM_LEDGER.json"
    if ledger.is_file():
        have = {r["id"] for r in json.loads(ledger.read_text(encoding="utf-8"))["items"]}
        missing = sorted(set(ids) - have)
        if missing:
            errors.append(f"{len(missing)} source items have no ledger status (first: {missing[0]})")
    else:
        errors.append("evidence/ITEM_LEDGER.json missing")
    return errors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    errs = check(write=a.write)
    out = {"schema": "PK_APP_SOURCE_CHECK/1", "result": "PASS" if not errs else "FAIL", "errors": errs}
    print(json.dumps(out) if a.json else (out["result"] + ("" if not errs else "\n  " + "\n  ".join(errs))))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
