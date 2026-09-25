"""SHA256SUMS.txt + RELEASE_MANIFEST.json (MC-085, MC-036 checksum part).

SHA256SUMS.txt covers every file except itself, RELEASE_MANIFEST.json and evidence/RELEASE_EVIDENCE.json
(which records the SHA256SUMS digest); RELEASE_MANIFEST.json pins all three.
    python -B -m inv28_unikernel_implementations.tools.manifest [--verify]
"""
from __future__ import annotations

import hashlib
import json
import sys

from ._common import CACHE_DIRS, ROOT

EXCLUDE = {"SHA256SUMS.txt", "RELEASE_MANIFEST.json", "evidence/RELEASE_EVIDENCE.json", "evidence/CHECK_ALL.json"}


def files():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT).as_posix()
        if p.is_file() and not CACHE_DIRS & set(p.parts) and not rel.endswith(".pyc") and rel not in EXCLUDE:
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
    prov = json.loads((ROOT / "evidence" / "PROVENANCE.json").read_text()) if (ROOT / "evidence" / "PROVENANCE.json").exists() else {}
    manifest = {
        "schema": "PK_RELEASE_MANIFEST/1", "component": "INV-28 Unikernel implementations",
        "version": (ROOT / "VERSION").read_text().strip(), "release_date": "2026-09-23",
        "source_archive": prov.get("source_archive"), "applied_package": prov.get("applied_package"),
        "sha256sums_digest": hashlib.sha256(s.encode()).hexdigest(),
        "release_evidence_sha256": hashlib.sha256(ev.read_bytes()).hexdigest() if ev.exists() else None,
        "file_count": len(s.splitlines()),
        "signature": None, "signature_note": "unsigned: no signing identity/KMS (D-005, W-002)",
    }
    if ev.exists():
        e = json.loads(ev.read_text())
        manifest["release_verdict"] = e.get("verdict")
        manifest["mc_summary"] = e.get("mc_summary")
    (ROOT / "RELEASE_MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print("wrote SHA256SUMS.txt and RELEASE_MANIFEST.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
