"""Release hygiene (61.04/05/13/14/25): broken relative links in Markdown,
JSON parse of every .json, and a secret scan over the whole tree."""
from __future__ import annotations

import json
import pathlib
import re

PKG = pathlib.Path(__file__).resolve().parents[1]
SECRET_PATTERNS = [re.compile(p) for p in (
    r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----", r"AKIA[0-9A-Z]{16}", r"ghp_[A-Za-z0-9]{36}",
    r"xox[baprs]-[A-Za-z0-9-]{10,}", r"(?i)password\s*[:=]\s*['\"][^'\"]{6,}['\"]")]
SKIP = ("evidence/", "__pycache__", "docs/GAP01_Professional_Missing_Components_Checklist")


def main() -> int:
    problems = []
    for p in sorted(PKG.rglob("*")):
        rel = p.relative_to(PKG).as_posix()
        if not p.is_file() or rel.startswith(SKIP) or rel.endswith(".pyc"):
            continue
        text = p.read_text(errors="replace")
        if rel != "tools/check_repo.py":
            for pat in SECRET_PATTERNS:
                if pat.search(text):
                    problems.append(f"{rel}: possible secret ({pat.pattern[:30]})")
        if p.suffix == ".json":
            try:
                json.loads(text)
            except ValueError as exc:
                problems.append(f"{rel}: invalid JSON ({exc})")
        if p.suffix == ".md":
            for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text):
                if re.match(r"[a-z]+://", target) or target.startswith("mailto:"):
                    continue
                if not (p.parent / target).exists():
                    problems.append(f"{rel}: broken link -> {target}")
            for target in re.findall(r"`((?:docs|deploy|tools|tests|schemas|examples)/[\w./*-]+)`", text):
                if "*" not in target and not (PKG / target).exists():
                    problems.append(f"{rel}: missing referenced path {target}")
    for pr in problems:
        print("FAIL", pr)
    print(f"{'PASS' if not problems else 'FAIL'}: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
