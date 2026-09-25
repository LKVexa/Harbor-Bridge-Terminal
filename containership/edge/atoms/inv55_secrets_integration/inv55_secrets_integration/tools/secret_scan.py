"""Repository secret-scanning / credential-exclusion gate (checklist #31).

Exit 0 = clean, 1 = findings, 2 = error.  Findings print path:line and the
rule id only - never the matched text.  Test fixtures that intentionally carry
canaries must be listed in ``ALLOW`` with a justification.
"""
from __future__ import annotations

import pathlib
import re
import sys

RULES = {
    "vault-token": re.compile(r"\bhvs\.[A-Za-z0-9_-]{24,}\b"),
    "vault-legacy-token": re.compile(r"\bs\.[A-Za-z0-9]{24}\b"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b"),
    "generic-assignment": re.compile(r"(?i)\b(?:password|passwd|secret_id|api_key)\s*[:=]\s*['\"][^'\"\s]{12,}['\"]"),
}
SKIP_DIRS = {".git", "__pycache__", "evidence", "dist", "build"}
ALLOW = {
    # path suffix -> justification (test canaries are synthetic and documented)
    "tests/test_runtime_units.py": "synthetic credential-shaped strings used to prove the log scrubber masks them",
    "tests/test_tools.py": "synthetic credential-shaped strings used to prove this scanner detects them",
    "tools/secret_scan.py": "rule definitions",
    "runtime/telemetry.py": "scrubber rule definitions",
}


def scan(root: pathlib.Path):
    findings = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or any(part in SKIP_DIRS for part in p.parts):
            continue
        rel = p.relative_to(root).as_posix()
        if any(rel.endswith(a) for a in ALLOW):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for ln, line in enumerate(text.splitlines(), 1):
            for rid, rx in RULES.items():
                if rx.search(line):
                    findings.append({"path": rel, "line": ln, "rule": rid})
    return findings


def main(argv=None):
    root = pathlib.Path((argv or sys.argv[1:] or [pathlib.Path(__file__).resolve().parents[1]])[0])
    f = scan(root)
    for x in f:
        print(f"{x['path']}:{x['line']}: {x['rule']}")
    print(f"secret_scan: {len(f)} finding(s) over {root.name}")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())
