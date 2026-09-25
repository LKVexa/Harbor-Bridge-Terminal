"""Operator explain view (C077): why did INV-61 decide what it decided?

    python tools/explain.py AUDIT.jsonl --key-file audit.key [--principal P] [--request R] [--event E]

Verifies the audit chain first (refuses to explain from a tampered log),
then prints each matching decision with its inputs (principal, tenant,
interface, function), the policy version and the reason code.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
security = __import__(f"{PKG.name}.security", fromlist=["x"])


def explain(path, key: bytes, principal=None, request=None, event=None) -> list[str]:
    ok, n, head = security.AuditLog.verify(path, key)
    if not ok:
        raise SystemExit(f"audit chain INVALID after {n} records - refusing to explain")
    out = [f"audit chain verified: {n} records, head {head[:16]}"]
    for line in pathlib.Path(path).read_text().splitlines():
        rec = json.loads(json.loads(line)["body"])
        if principal and rec.get("principal") != principal:
            continue
        if request and rec.get("request_id") != request:
            continue
        if event and rec.get("event") != event:
            continue
        who = rec.get("principal") or rec.get("key_id") or rec.get("actor") or "-"
        what = "/".join(x for x in (rec.get("interface"), rec.get("function")) if x) or "-"
        why = rec.get("reason") or rec.get("expected") and f"expected {rec['expected']}" or "-"
        pol = f" policy v{rec['policy']}" if "policy" in rec else ""
        out.append(f"#{rec['seq']:>6} {rec['event']:<20} who={who} what={what} tenant={rec.get('tenant', '-')} why={why}{pol}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("audit"); ap.add_argument("--key-file", required=True)
    ap.add_argument("--principal"); ap.add_argument("--request"); ap.add_argument("--event")
    a = ap.parse_args()
    print("\n".join(explain(a.audit, pathlib.Path(a.key_file).read_bytes().strip(), a.principal, a.request, a.event)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
