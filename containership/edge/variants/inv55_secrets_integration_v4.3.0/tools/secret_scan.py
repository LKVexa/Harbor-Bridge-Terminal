#!/usr/bin/env python3
"""Secret-scanning / credential-exclusion gate (checklist #31).

Scans every tracked text file for credential-shaped content.  Exit 1 on any finding.
Allow-list a *line* with the marker ``inv55-scan: allow`` plus a justification.
Findings print the path, line and rule only -- never the matched text.
"""
from __future__ import annotations

import pathlib
import re
import sys

RULES = {
    "vault-token": re.compile(r"\bhvs\.[A-Za-z0-9_-]{20,}|\bs\.[A-Za-z0-9]{24}\b"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private-key": re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    "generic-assignment": re.compile(r"(?i)\b(password|passwd|secret_id|api_key|client_secret)['\"]?\s*[:=]\s*['\"][^'\"<>{}$]{8,}['\"]"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b"),
}
SKIP_DIRS = {".git", "__pycache__", "build", "dist", ".venv"}
TEXT_SUFFIX = {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".txt", ".cfg", ".ini", ".sh", ""}


def scan(root: pathlib.Path) -> list[tuple[str, int, str]]:
    out = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or any(part in SKIP_DIRS for part in p.parts) or p.suffix not in TEXT_SUFFIX:
            continue
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(lines, 1):
            if "inv55-scan: allow" in line:
                continue
            for rule, rx in RULES.items():
                if rx.search(line):
                    out.append((str(p.relative_to(root)), i, rule))
    return out


def main(argv: list[str]) -> int:
    root = pathlib.Path(argv[1] if len(argv) > 1 else ".").resolve()
    findings = scan(root)
    for path, line, rule in findings:
        print(f"SECRET-SCAN {rule}: {path}:{line}")
    print(f"secret-scan: {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
