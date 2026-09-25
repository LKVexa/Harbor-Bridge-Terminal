"""Component 04 CI gate: fail on unsigned, untrusted or mismatched release artifacts.

Usage::

  python -m inv08_dynamic_infrastructure_model.production.ci.release_check \
      --root <artifact dir> --envelope provenance.json --key-file k.json [--allow-nonproduction]

``k.json`` = {"kid": str, "key_hex": str} (a NONPRODUCTION HMAC key; test use only).
Without ``--allow-nonproduction`` the gate requires a production signature, which no
key in this overlay can produce, so it fails closed.  Exit codes: 0 pass, 1 reject,
2 usage/input error.  Output is one machine-readable JSON line.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from ..core import TrustRoot, sha256_hex
from ..provenance import VerificationPolicy


def run(root: Path, envelope: dict, kid: str, key: bytes, *, allow_nonproduction: bool) -> dict:
    trust = TrustRoot()
    trust.add(kid, key)
    artifacts = {str(p.relative_to(root)): sha256_hex(p.read_bytes())
                 for p in sorted(root.rglob("*")) if p.is_file()}
    pol = VerificationPolicy(trusted_kids={kid}, require_production=not allow_nonproduction)
    ok, reasons = pol.verify(envelope, trust, artifacts)
    return {"ok": ok, "reasons": reasons, "artifacts": len(artifacts),
            "policy": "nonproduction-allowed" if allow_nonproduction else "production-required"}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="release_check")
    ap.add_argument("--root", required=True)
    ap.add_argument("--envelope", required=True)
    ap.add_argument("--key-file", required=True)
    ap.add_argument("--allow-nonproduction", action="store_true")
    a = ap.parse_args(argv)
    try:
        env = json.loads(Path(a.envelope).read_text(encoding="utf-8"))
        k = json.loads(Path(a.key_file).read_text(encoding="utf-8"))
        res = run(Path(a.root), env, k["kid"], bytes.fromhex(k["key_hex"]),
                  allow_nonproduction=a.allow_nonproduction)
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"ok": False, "reasons": [f"input error: {type(exc).__name__}: {exc}"]}))
        return 2
    print(json.dumps(res, sort_keys=True))
    return 0 if res["ok"] else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
