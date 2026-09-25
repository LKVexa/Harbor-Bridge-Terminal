"""Repository / release secret scanner (MC-14; C039).

    python -m inv64_application_model.tools.secret_scan [PATH ...] [--json]

Lower-case path/identifier-shaped tokens (only ``[a-z0-9_./-]`` with a ``/``
or ``_``) are not entropy candidates; credentials are matched by pattern.

Wheels and sdists are scanned member by member (``RECORD`` digests excluded),
with member paths mapped back to package-relative paths so the same reviewed
suppressions apply. Scans every text file (default: the package tree, or given paths such as a
built wheel/sdist extraction) with the same pattern set the runtime uses
(:mod:`redaction`) plus a Shannon-entropy check for long opaque tokens.
Suppressions live in ``ops/secret_scan_allowlist.json`` — each entry names a
file, the exact probe value's SHA-256 (not the value), a reason, and who
reviewed it; unmatched hits fail the scan (exit 1).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

from inv64_application_model.redaction import classify_text

ROOT = Path(__file__).resolve().parents[1]
ALLOW = ROOT / "ops" / "secret_scan_allowlist.json"
SKIP_DIRS = {".git", "__pycache__", "dist", "build", "_build", ".pytest_cache"}
TEXT_EXT = {".py", ".md", ".json", ".toml", ".yml", ".yaml", ".txt", ".wit", ".cfg", ".ini", ".sh", ".ps1", ""}
TOKEN_RE = re.compile(r"[A-Za-z0-9+/_=-]{32,}")


def entropy(s: str) -> float:
    counts = {c: s.count(c) for c in set(s)}
    return -sum(n / len(s) * math.log2(n / len(s)) for n in counts.values())


def _lines_hits(rel: str, text: str, allowed: set) -> list[dict]:
    hits = []
    for ln, line in enumerate(text.splitlines(), 1):
        found = []
        cls = classify_text(line)
        if cls:
            found.append((cls, line.strip()))
        for tok in TOKEN_RE.findall(line):
            path_like = (bool(re.fullmatch(r"[a-z0-9_./-]+", tok)) and ("/" in tok or "_" in tok)) or \
                ("/" in tok and all(re.search(r"[a-z]{4,}", seg) for seg in tok.split("/") if seg))
            if entropy(tok) > 4.5 and not path_like and not re.fullmatch(r"[0-9a-f]{32,}", tok) \
                    and not tok.startswith(("sha256", "http")):
                found.append(("high-entropy", tok))
        for cls, val in found:
            digest = hashlib.sha256(val.encode()).hexdigest()
            if (rel, digest) not in allowed and (rel, "*") not in allowed:
                hits.append({"path": rel, "line": ln, "class": cls, "sha256": digest})
    return hits


def _archive_members(p: Path):
    """Yield (package-relative path, text) for text members of a wheel or sdist."""
    import tarfile
    import zipfile
    def rel(name: str) -> str:
        parts = name.split("/")
        if parts[0].startswith("inv64-application-model-") or parts[0] == "inv64_application_model":
            parts = parts[1:]
            if parts and parts[0] == "inv64_application_model":
                parts = parts[1:]
        return "/".join(parts)
    if p.suffix == ".whl":
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if n.endswith("/RECORD") or Path(n).suffix not in TEXT_EXT:
                    continue
                try:
                    yield rel(n), z.read(n).decode("utf-8")
                except UnicodeDecodeError:
                    continue
    elif p.name.endswith(".tar.gz"):
        with tarfile.open(p) as t:
            for m in t.getmembers():
                if not m.isfile() or Path(m.name).suffix not in TEXT_EXT:
                    continue
                try:
                    yield rel(m.name), t.extractfile(m).read().decode("utf-8")
                except UnicodeDecodeError:
                    continue


def scan(paths: list[Path]) -> list[dict]:
    allow = json.loads(ALLOW.read_text(encoding="utf-8"))["entries"] if ALLOW.exists() else []
    allowed = {(a["path"], a["sha256"]) for a in allow}
    hits = []
    for base in paths:
        files = [base] if base.is_file() else [p for p in sorted(base.rglob("*")) if p.is_file()
                                                and not SKIP_DIRS & set(p.relative_to(base).parts)]
        for p in files:
            if p.suffix == ".whl" or p.name.endswith(".tar.gz"):
                for rel, text in _archive_members(p):
                    hits += [dict(h, archive=p.name) for h in _lines_hits(rel, text, allowed)]
                continue
            if p.suffix not in TEXT_EXT or p.stat().st_size > 5_000_000:
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            rel = p.relative_to(base).as_posix() if base.is_dir() else p.name
            hits += _lines_hits(rel, text, allowed)
    return hits


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    paths = [Path(p) for p in a.paths] or [ROOT]
    hits = scan(paths)
    res = {"schema": "PK_APP_SECRET_SCAN/1", "result": "FAIL" if hits else "PASS", "hits": hits}
    print(json.dumps(res, indent=2) if a.json else (res["result"] + "".join(
        f"\n  {h['path']}:{h['line']} {h['class']} sha256={h['sha256'][:12]}" for h in hits)))
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
