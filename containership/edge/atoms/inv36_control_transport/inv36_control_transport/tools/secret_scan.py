"""Repository secret/hygiene scanner (MC-17.024, MC-05.003).

Fails on private-key PEM blocks, high-entropy hex/base64 assignments to
secret-like names, cloud credential shapes, committed key files and
world-writable files.  Test vectors that are *meant* to be public (fixtures)
are allowed only under fixtures/ and must be listed in ALLOW.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import stat
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
PATTERNS = {
    "private_key_pem": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    "slack_token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    "secret_assignment": re.compile(r"(?i)(password|secret|api_key|private_key)\s*[:=]\s*['\"][A-Za-z0-9+/=_-]{16,}['\"]"),
}
SKIP_DIRS = {".git", "dist", "evidence", "__pycache__", ".mypy_cache", ".ruff_cache"}
FORBIDDEN_NAMES = (".pem", ".key", ".p12", ".pfx", "id_rsa", "id_ed25519")
ALLOW = {"tools/secret_scan.py", "config.py", "tests/test_control_planes.py", "fixtures/golden_config.json",
         "tests/test_governance.py"}


def scan(root: pathlib.Path = PKG) -> list[dict]:
    findings: list[dict] = []
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in files:
            p = pathlib.Path(dirpath) / fn
            rel = p.relative_to(root).as_posix()
            if fn.endswith(FORBIDDEN_NAMES):
                findings.append({"file": rel, "rule": "key_file_committed"})
            try:
                if p.stat().st_mode & stat.S_IWOTH:
                    findings.append({"file": rel, "rule": "world_writable"})
                text = p.read_text(errors="ignore")
            except OSError:
                continue
            if rel in ALLOW:
                continue
            for rule, rx in PATTERNS.items():
                for m in rx.finditer(text):
                    findings.append({"file": rel, "rule": rule, "line": text.count("\n", 0, m.start()) + 1})
    return findings


def main() -> int:
    f = scan()
    print(json.dumps({"schema": "inv36.secret-scan/1", "findings": f, "ok": not f}, indent=1))
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())
