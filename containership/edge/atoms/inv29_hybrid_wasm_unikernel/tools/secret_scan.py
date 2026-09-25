"""Minimal secret scanner (MC022).  Exit 1 on findings.  Used by CI and build_release.

Patterns: private-key blocks, AWS/GCP/GitHub/Slack/generic tokens, high-entropy
assignments to secret-looking names.  Allow-list: test fixture keys made of a
single repeated character (b"A" * 32) are not secrets.
"""
import json
import math
import pathlib
import re
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "slack-token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
    "google-api-key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "generic-assignment": re.compile(r"(?i)\b(secret|password|passwd|api[_-]?key|token)\b\s*[:=]\s*['\"]([^'\"\s]{12,})['\"]"),
}
SKIP_DIRS = {"__pycache__", ".git", "release", "sbom", "security", "conformance", "fuzz", "dist"}


def entropy(s):
    return -sum(s.count(c) / len(s) * math.log2(s.count(c) / len(s)) for c in set(s)) if s else 0.0


def scan(root=PKG):
    findings, files = [], 0
    for p in sorted(root.rglob("*")):
        if not p.is_file() or set(p.relative_to(root).parts) & SKIP_DIRS or p.suffix in {".bin", ".pyc"}:
            continue
        files += 1
        text = p.read_text("utf-8", errors="replace")
        for n, line in enumerate(text.splitlines(), 1):
            for kind, rx in PATTERNS.items():
                for m in rx.finditer(line):
                    val = m.group(m.lastindex or 0)
                    if kind == "generic-assignment" and entropy(val) < 3.0:
                        continue
                    findings.append({"file": p.relative_to(root).as_posix(), "line": n, "kind": kind})
    return {"tool": "inv29-secret-scan/1", "files_scanned": files, "findings": findings, "clean": not findings}


if __name__ == "__main__":
    r = scan()
    print(json.dumps(r, indent=2))
    sys.exit(0 if r["clean"] else 1)
