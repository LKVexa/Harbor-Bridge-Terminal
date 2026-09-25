"""Secret scan lane: no private keys, bearer tokens or credential assignments committed to the tree."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [re.compile(p) for p in (
    r"-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----",
    r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{20,}",  # JWT
    r"(?i)(password|secret|api[_-]?key)\s*[:=]\s*['\"][^'\"$<{]{8,}['\"]",
    r"AKIA[0-9A-Z]{16}",
)]
hits = []
for p in ROOT.rglob("*"):
    if not p.is_file() or set(p.relative_to(ROOT).parts) & {".git", "__pycache__"} or p.suffix in (".zip", ".whl"):
        continue
    if p.name == "check_secrets.py":
        continue
    try:
        text = p.read_text()
    except (UnicodeDecodeError, OSError):
        continue
    for pat in PATTERNS:
        for m in pat.finditer(text):
            hits.append(f"{p.relative_to(ROOT)}: {pat.pattern[:30]}... at {m.start()}")
for h in hits:
    print("SECRET?", h)
print(f"secret scan: {len(hits)} findings")
sys.exit(1 if hits else 0)
