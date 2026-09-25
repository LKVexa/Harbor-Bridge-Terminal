"""MC50-010 CI check: every file referenced in backticks from a Markdown document must
exist in the package, unless it is listed in EVIDENCE_GAPS.json as a recorded gap.
A recorded gap is NOT a waiver: the checker prints it on every run so it stays visible."""
import json
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
gaps = {}
if (root / "EVIDENCE_GAPS.json").exists():
    gaps = {g["path"]: g for g in json.loads((root / "EVIDENCE_GAPS.json").read_text())["gaps"]}
ref = re.compile(r"`([A-Za-z0-9_./-]+\.(?:md|json|txt|toml|py|tla|sh))`")
missing = []
for md in sorted(root.rglob("*.md")):
    if "tests/" in str(md.relative_to(root)) or "evidence/" in str(md.relative_to(root)):
        continue
    for name in set(ref.findall(md.read_text(encoding="utf-8"))):
        if "/" not in name and not (root / name).exists() and not list(root.rglob(name)):
            if name in gaps:
                print(f"RECORDED GAP  {name}  ({gaps[name]['status']}) referenced from {md.name}")
            else:
                missing.append((md.name, name))
for src, name in missing:
    print(f"MISSING  {name}  referenced from {src}")
sys.exit(1 if missing else 0)
