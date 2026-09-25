"""MC-016 CI secret scan over shipped text files."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from inv24_microvm_runtime.security.secrets import scan_for_secrets  # noqa: E402

SKIP = {".git", ".venv", "__pycache__", "evidence"}
hits = []
for p in ROOT.rglob("*"):
    if p.is_file() and not SKIP & set(p.parts) and p.suffix in {".py", ".json", ".md", ".yaml", ".yml", ".toml", ".sh", ".txt"}:
        if "tests" in p.parts or p.name == "secrets.py":
            continue  # fixtures/patterns intentionally contain look-alikes
        found = scan_for_secrets(p.read_text(errors="replace"))
        if found:
            hits.append((str(p.relative_to(ROOT)), found))
for h in hits:
    print("SECRET?", *h)
sys.exit(1 if hits else 0)
