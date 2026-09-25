"""Secret scanning (MC-035).  Scans every text file in the repository (vendored code included).

Patterns: PEM private keys, AWS access keys, GitHub/Slack/generic bearer tokens, and assignments of
high-entropy literals to names containing secret/token/password/api_key.  64-hex SHA-256 digests are
content hashes, not secrets, and are ignored unless assigned to a secret-looking name.  Matched values
are never printed or stored - only file, line and rule.
"""
from __future__ import annotations

import math
import re
import sys
from collections import Counter

from ._common import CACHE_DIRS, EVIDENCE, ROOT, write_json

RULES = {
    "pem-private-key": re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "slack-token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
    "bearer": re.compile(r"(?i)authorization:\s*bearer\s+[A-Za-z0-9._\-]{20,}"),
    "assigned-secret": re.compile(r"(?i)\b(secret|token|password|passwd|api_key|apikey)\w*\s*[:=]\s*[\"']([^\"'\s]{16,})[\"']"),
}
TEXT_EXT = {".py", ".md", ".json", ".toml", ".yml", ".yaml", ".txt", ".cfg", ".lock", ""}
SKIP = {"SHA256SUMS.txt", "RELEASE_MANIFEST.json"}


def entropy(s: str) -> float:
    c = Counter(s)
    return -sum(n / len(s) * math.log2(n / len(s)) for n in c.values())


def scan() -> list[dict]:
    out = []
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT).as_posix()
        cached = bool(CACHE_DIRS & set(p.parts))
        if not p.is_file() or cached or p.suffix not in TEXT_EXT or rel in SKIP or rel.startswith("evidence/"):
            continue
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for n, line in enumerate(lines, 1):
            for rule, rx in RULES.items():
                m = rx.search(line)
                if not m:
                    continue
                if rule == "assigned-secret":
                    val = m.group(2)
                    if entropy(val) < 3.5 or val.startswith(("<", "fixture", "example", "mailto:")):
                        continue
                out.append({"rule": rule, "file": rel, "line": n})
    return out


def main(argv=None) -> int:
    f = scan()
    write_json(EVIDENCE / "SECRET_SCAN.json", {"schema": "PK_SECRET_SCAN/1", "tool": "tools/secret_scan.py",
                                               "rules": sorted(RULES), "findings": f, "pass": not f})
    for x in f:
        print("SECRET", x["rule"], f"{x['file']}:{x['line']}")
    print("SECRETS", "PASS" if not f else f"FAIL ({len(f)})")
    return 0 if not f else 1


if __name__ == "__main__":
    sys.exit(main())
