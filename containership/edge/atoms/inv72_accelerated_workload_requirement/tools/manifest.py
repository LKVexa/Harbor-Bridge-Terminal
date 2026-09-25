"""Write SHA256SUMS.txt and RELEASE_MANIFEST.json (C016 packaging consistency, C090 evidence retention).

SHA256SUMS.txt covers every file except itself, RELEASE_MANIFEST.json and evidence/RELEASE_EVIDENCE.json
(which records the SHA256SUMS digest).  RELEASE_MANIFEST.json then pins all three.
    python -m inv72_accelerated_workload_requirement.tools.manifest [--verify]
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {"SHA256SUMS.txt", "RELEASE_MANIFEST.json", "evidence/RELEASE_EVIDENCE.json"}


def files():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT).as_posix()
        if p.is_file() and "__pycache__" not in p.parts and not rel.endswith(".pyc") and rel not in EXCLUDE:
            yield rel, p


def sums() -> str:
    return "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {rel}\n" for rel, p in files())


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if "--verify" in argv:
        cur = (ROOT / "SHA256SUMS.txt").read_text()
        ok = cur == sums()
        print("MANIFEST", "OK" if ok else "MISMATCH")
        return 0 if ok else 1
    s = sums()
    (ROOT / "SHA256SUMS.txt").write_text(s)
    ev = ROOT / "evidence" / "RELEASE_EVIDENCE.json"
    manifest = {
        "component": "INV-72 Accelerated workload requirement", "version": (ROOT / "VERSION").read_text().strip(),
        "release_date": "2026-09-23",
        "source_archive": {"name": "inv72_accelerated_workload_requirement_v4.2.0_hardened.zip",
                           "sha256": "55c8044ab08e1b50805e3a094406b0dc3eca97c1a22c778e37d3e58a38c60247"},
        "applied_package": {"name": "INV72_MISSING_COMPONENTS_PROFESSIONAL_CHECKLIST.md",
                            "sha256": "6e4df91b31152e76e2990735b2f5aa45cb04b7f85bc567d9a73a09ed52641367"},
        "sha256sums_digest": hashlib.sha256(s.encode()).hexdigest(),
        "release_evidence_sha256": hashlib.sha256(ev.read_bytes()).hexdigest() if ev.exists() else None,
        "file_count": len(s.splitlines()) + 3,
        "files": [{"path": rel, "size": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                  for rel, p in files()],
    }
    if ev.exists():
        e = json.loads(ev.read_text())
        manifest["release_verdict"] = e.get("verdict")
        manifest["rtm_summary"] = e.get("rtm_summary")
    (ROOT / "RELEASE_MANIFEST.json").write_text(json.dumps(manifest, indent=1))
    print("wrote SHA256SUMS.txt and RELEASE_MANIFEST.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
