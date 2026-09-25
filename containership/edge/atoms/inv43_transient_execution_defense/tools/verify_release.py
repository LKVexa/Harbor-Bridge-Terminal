"""Item 23: independently verify a built INV-43 release directory.

    python tools/verify_release.py [--root DIR]

Checks: every SHA256SUMS entry matches and no unlisted file exists outside
release/ and conformance/; the in-toto statement's subject is SHA256SUMS; the
Ed25519 signature verifies (and reports that the key is an ephemeral dev key);
the evidence ledger chain verifies and its head equals the head anchored in
conformance/INV43_LOCAL_GATE.json; the gate's release digest equals SHA256SUMS.
Exit 0 = intact, 1 = integrity failure.  Intact is NOT the same as approved.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify(root: pathlib.Path) -> dict:
    problems, notes = [], []
    listed = {}
    for line in (root / "SHA256SUMS.txt").read_text().splitlines():
        digest, rel = line.split("  ", 1)
        listed[rel[2:]] = digest
    for rel, digest in listed.items():
        p = root / rel
        if not p.exists():
            problems.append(f"missing: {rel}")
        elif sha(p) != digest:
            problems.append(f"digest mismatch: {rel}")
    for p in root.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts:
            rel = p.relative_to(root).as_posix()
            if rel.split("/")[0] not in {"release", "conformance"} and rel != "SHA256SUMS.txt" and rel not in listed:
                problems.append(f"unlisted file: {rel}")
    sums = sha(root / "SHA256SUMS.txt")
    stmt = json.loads((root / "release" / "provenance.intoto.json").read_text())
    if stmt["subject"][0]["digest"]["sha256"] != sums:
        problems.append("provenance subject != SHA256SUMS")
    sig = json.loads((root / "release" / "signature.json").read_text())
    if sig.get("algorithm") == "Ed25519":
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(sig["public_key_b64"]))
            pub.verify(base64.b64decode(sig["signature_b64"]),
                       json.dumps(stmt, sort_keys=True, separators=(",", ":")).encode())
            notes.append(f"signature valid; key_class={sig['key_class']}")
        except ImportError:
            notes.append("cryptography not installed: signature NOT checked")
        except Exception:
            problems.append("signature invalid")
    else:
        notes.append("release is unsigned")
    prev, n = "0" * 64, -1
    for line in (root / "evidence" / "ledger.jsonl").read_text().splitlines():
        e = json.loads(line)
        body = {k: e[k] for k in ("seq", "path", "sha256")}
        h = hashlib.sha256(prev.encode() + json.dumps(body, sort_keys=True).encode()).hexdigest()
        if e["prev"] != prev or e["hash"] != h or e["seq"] != n + 1:
            problems.append(f"ledger chain broken at {e.get('seq')}")
            break
        if sha(root / e["path"]) != e["sha256"]:
            problems.append(f"evidence changed: {e['path']}")
        prev, n = h, e["seq"]
    gate = json.loads((root / "conformance" / "INV43_LOCAL_GATE.json").read_text())
    if gate["evidence"]["ledger_head"] != {"seq": n, "hash": prev}:
        problems.append("ledger head differs from the head anchored in the gate (truncation or substitution)")
    if gate["release_digest"]["SHA256SUMS.txt"] != sums:
        problems.append("gate is bound to a different release")
    return {"intact": not problems, "problems": problems, "notes": notes, "gate_verdict": gate["verdict"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    a = ap.parse_args(argv)
    rep = verify(pathlib.Path(a.root))
    print(json.dumps(rep, indent=2))
    return 0 if rep["intact"] else 1


if __name__ == "__main__":
    sys.exit(main())
