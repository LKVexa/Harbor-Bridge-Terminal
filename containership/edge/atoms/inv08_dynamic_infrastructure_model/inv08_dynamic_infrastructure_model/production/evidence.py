"""Component 03 - production acceptance evidence bundle (contract PK_DYN_EVIDENCE/1).

Bundle layout (canonical JSON)::

  {"schema": "PK_DYN_EVIDENCE/1", "build_id": str, "created": float,
   "gate": {"results": [{"control": "INV-08-C0NN", "status": PASS|FAIL|BLOCKED|NOT_RUN,
                          "detail": str}], "overall": PASS|FAIL|BLOCKED},
   "manifest": {"<control id>": [{"path": rel, "sha256": hex, "bytes": int}]},
   "approvals": [{"role": str, "identity": "UNASSIGNED"|str, "ts": null|float}],
   "bundle_digest": "sha256:..."}   # digest over everything except itself/signature

``verify_bundle`` deterministically replays: schema, digest, per-artifact sha256,
control-id format, gate overall recomputation and (optionally) approvals.
CLI: ``python -m inv08_dynamic_infrastructure_model.production.evidence verify
<bundle.json> --root <dir> [--require-approvals]``.

Approver identity is BLOCKED: no accountable human exists; slots stay UNASSIGNED
and ``require_approvals=True`` fails on them.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .core import TrustRoot, digest, sha256_hex

SCHEMA = "PK_DYN_EVIDENCE/1"
CONTROL_RE = re.compile(r"^INV-08-C(0\d\d|100)$")
STATUSES = {"PASS", "FAIL", "BLOCKED", "NOT_RUN"}
APPROVER_ROLES = ("service_owner", "security_reviewer", "release_approver")
UNASSIGNED = "UNASSIGNED"


def overall(results: list[dict]) -> str:
    sts = {r["status"] for r in results}
    if not results or "FAIL" in sts:
        return "FAIL"
    if sts - {"PASS"}:
        return "BLOCKED"
    return "PASS"


def _safe_rel(root: Path, rel: str) -> Path:
    p = (root / rel).resolve()
    if Path(rel).is_absolute() or root.resolve() not in (p, *p.parents):
        raise ValueError(f"artifact path escapes root: {rel}")
    return p


def build_bundle(gate_results: list[dict], artifacts: dict[str, list[str]], root: str | Path,
                 *, build_id: str, clock=lambda: 0.0) -> dict:
    root = Path(root)
    for r in gate_results:
        if not CONTROL_RE.match(str(r.get("control"))) or r.get("status") not in STATUSES:
            raise ValueError(f"bad gate result {r!r}")
    manifest: dict[str, list] = {}
    for control, paths in sorted(artifacts.items()):
        if not CONTROL_RE.match(control):
            raise ValueError(f"bad control id {control!r}")
        entries = []
        for rel in sorted(paths):
            data = _safe_rel(root, rel).read_bytes()
            entries.append({"path": rel, "sha256": sha256_hex(data), "bytes": len(data)})
        manifest[control] = entries
    results = sorted(({"control": r["control"], "status": r["status"], "detail": str(r.get("detail", ""))}
                      for r in gate_results), key=lambda r: r["control"])
    body = {"schema": SCHEMA, "build_id": build_id, "created": clock(),
            "gate": {"results": results, "overall": overall(results)},
            "manifest": manifest,
            "approvals": [{"role": r, "identity": UNASSIGNED, "ts": None} for r in APPROVER_ROLES]}
    body["bundle_digest"] = digest(body)
    return body


def _body(bundle: dict) -> dict:
    return {k: v for k, v in bundle.items() if k not in {"bundle_digest", "signature"}}


def sign_bundle(bundle: dict, trust: TrustRoot, kid: str) -> dict:
    out = dict(bundle)
    out["signature"] = trust.sign(kid, _body(bundle))
    return out


def verify_bundle(bundle: dict, root: str | Path, *, require_approvals: bool = False,
                  trust: TrustRoot | None = None, require_production: bool = False) -> tuple[bool, list[str]]:
    root = Path(root)
    p: list[str] = []
    if not isinstance(bundle, dict) or bundle.get("schema") != SCHEMA:
        return False, ["schema mismatch"]
    if digest(_body(bundle)) != bundle.get("bundle_digest"):
        p.append("bundle_digest mismatch")
    results = bundle.get("gate", {}).get("results", [])
    if overall(results) != bundle.get("gate", {}).get("overall"):
        p.append("gate overall inconsistent with results")
    for control, entries in bundle.get("manifest", {}).items():
        if not CONTROL_RE.match(control):
            p.append(f"bad control id {control}")
        for e in entries:
            try:
                f = _safe_rel(root, e["path"])
                if not f.is_file():
                    p.append(f"{control}: missing {e['path']}")
                elif sha256_hex(f.read_bytes()) != e["sha256"]:
                    p.append(f"{control}: digest mismatch {e['path']}")
            except ValueError as exc:
                p.append(str(exc))
    if require_approvals:
        for a in bundle.get("approvals", []):
            if a.get("identity") in (None, "", UNASSIGNED) or a.get("ts") is None:
                p.append(f"approval {a.get('role')} UNASSIGNED")
    if trust is not None:
        sig = bundle.get("signature")
        if not sig or not trust.verify(_body(bundle), sig, require_production=require_production):
            p.append("signature missing or rejected")
    return not p, p


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="evidence")
    ap.add_argument("cmd", choices=["verify"])
    ap.add_argument("bundle")
    ap.add_argument("--root", required=True)
    ap.add_argument("--require-approvals", action="store_true")
    a = ap.parse_args(argv)
    bundle = json.loads(Path(a.bundle).read_text(encoding="utf-8"))
    ok, problems = verify_bundle(bundle, a.root, require_approvals=a.require_approvals)
    print(json.dumps({"ok": ok, "problems": problems, "overall": bundle.get("gate", {}).get("overall")},
                     sort_keys=True))
    return 0 if ok and bundle["gate"]["overall"] == "PASS" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
