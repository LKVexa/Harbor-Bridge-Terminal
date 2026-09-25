"""SHA256SUMS.txt + RELEASE_MANIFEST.json (MC-088, MC-086).

    python -B -m inv27_unikernel_execution.tools.manifest [--verify]

SHA256SUMS.txt covers every file except itself, RELEASE_MANIFEST.json and evidence/RELEASE_EVIDENCE.json
(which records the SHA256SUMS digest).  RELEASE_MANIFEST.json pins all three plus the source archive and
applied checklist identities.
"""
from __future__ import annotations

import hashlib
import json
import sys

from ._refs import ROOT

EXCLUDE = {"SHA256SUMS.txt", "RELEASE_MANIFEST.json", "evidence/RELEASE_EVIDENCE.json"}
SOURCE = {"name": "inv27_unikernel_execution_v4.2.0_hardened.zip",
          "sha256": "6289b240585081ef6029c041f0602aef671a6eb0d95b8c36ba824ab692d43267"}
APPLIED = {"name": "INV27_v4.2.0_Missing_Component_Implementation_Checklist.md",
           "sha256": "c025260a32eebb52a381fd3f865a111f510265a64643a2f8a946e89cee747f67"}


def files():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT).as_posix()
        if p.is_file() and "__pycache__" not in p.parts and not rel.endswith(".pyc") and rel not in EXCLUDE:
            yield rel, p


def sums() -> str:
    return "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {rel}\n" for rel, p in files())


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--verify" in argv:
        ok = (ROOT / "SHA256SUMS.txt").exists() and (ROOT / "SHA256SUMS.txt").read_text() == sums()
        print("MANIFEST", "OK" if ok else "MISMATCH")
        return 0 if ok else 1
    s = sums()
    (ROOT / "SHA256SUMS.txt").write_text(s)
    ev = ROOT / "evidence" / "RELEASE_EVIDENCE.json"
    m = {"component": "INV-27 Unikernel execution", "version": (ROOT / "VERSION").read_text().strip(),
         "release_date": "2026-09-23", "source_archive": SOURCE, "applied_package": APPLIED,
         "sha256sums_digest": hashlib.sha256(s.encode()).hexdigest(),
         "release_evidence_sha256": hashlib.sha256(ev.read_bytes()).hexdigest() if ev.exists() else None,
         "file_count": len(s.splitlines()) + 3,
         "files": [{"path": rel, "size": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                   for rel, p in files()]}
    if ev.exists():
        e = json.loads(ev.read_text())
        m["release_verdict"], m["mc_summary"], m["rtm_summary"] = e.get("verdict"), e.get("mc_summary"), e.get("rtm_summary")
    (ROOT / "RELEASE_MANIFEST.json").write_text(json.dumps(m, indent=1))
    print("wrote SHA256SUMS.txt and RELEASE_MANIFEST.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
