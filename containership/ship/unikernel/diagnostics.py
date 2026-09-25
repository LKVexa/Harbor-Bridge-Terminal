"""Offline local preflight; never equates test success with production isolation."""
from __future__ import annotations
import ast
import importlib.util
from . import strictjson as json
import os
import sys
from pathlib import Path
from . import UC_RELEASE, engines as E, host as H, safety as S, ucmanifest as M

def doctor():
    root = Path(E.ship_root())
    errors = []
    for p in sorted((root / "ship").rglob("*.py")):
        try:
            ast.parse(p.read_text(encoding="utf-8-sig"), filename=str(p.relative_to(root)))
        except (SyntaxError, UnicodeError) as exc:
            errors.append({"path": str(p.relative_to(root)), "error": str(exc)})
    pending = []
    txroot = root / "_runs" / "transactions"
    if txroot.exists():
        for p in sorted(txroot.glob("*/journal.json")):
            try:
                pending.append(json.loads(p.read_text(encoding="utf-8")))
            except (OSError, ValueError) as exc:
                pending.append({"journal": str(p), "error": str(exc)})
    from . import transactions
    try:
        pending.extend(r for r in transactions.list_transactions(root) if r['status'] not in transactions.FINAL)
    except Exception as exc:
        pending.append({'error':str(exc),'scope':'managed transactions'})
    integrity = {}
    for label, fn in (("checksums", lambda: M.check_sums(str(root))),
                      ("inventory", lambda: M.check_manifest_inventory(str(root), json.loads((root / "MANIFEST.json").read_text())))):
        try:
            integrity[label] = fn()
        except Exception as exc:
            integrity[label] = {"pass": False, "error": str(exc)}
    hold = E.hold_state()
    pillow = importlib.util.find_spec("PIL") is not None
    python_ok = sys.version_info >= (3, 10)
    return {"schema": "UC/DOCTOR/1", "uc_release": UC_RELEASE, "host": H.facts(),
            "python_minimum": "3.10", "python_ok": python_ok, "pillow_present": pillow,
            "source_parse_errors": errors, "hold": hold, "integrity": integrity,
            "pending_transactions": pending, "host_limits": H.limits(),
            "preflight_ok": python_ok and pillow and hold["pass"] and not errors and not pending
                and all(v.get("pass") for v in integrity.values()),
            "isolation": {"hypervisor_boundary": False, "os_enforced_network_deny": False,
                          "multi_tenant_ready": False, "bootable_unikernel_image": False,
                          "distributed_consensus": False, "external_release_authentication": False},
            "limits": {"archive": vars(S.DEFAULT_LIMITS), "ship_tiff_bytes": 8388608, "ship_tiff_pages": 512},
            "note": "Preflight success checks local prerequisites and integrity only; build and verify remain necessary. See SECURITY.md."}
