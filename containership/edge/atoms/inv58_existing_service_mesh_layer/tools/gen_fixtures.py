"""Regenerate golden conformance fixtures (MC-006 C029).  Deterministic.

    python -B tools/gen_fixtures.py          # writes fixtures/
    python -B tools/gen_fixtures.py --check  # exit 1 on drift (used by CI)
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.dont_write_bytecode = True
import _support as S  # noqa: E402

CASES = {
    "reconcile": [
        ("both_request_retries", ("orders->payments", 3, 3, None)),
        ("mesh_only", ("a->b", 1, 9, 3)),
        ("budget_one_disables", ("a->b", 5, 5, 1)),
        ("no_retry", ("a->b", 1, 1, None)),
        ("err_zero_attempts", ("a->b", 0, 3, None)),
        ("err_over_max_budget", ("a->b", 3, 3, 99)),
        ("err_whitespace_route", (" a->b", 3, 3, None)),
    ],
    "identity": [
        ("ok_alpha", ("alpha", "spiffe://estate.local/ns/alpha/sa/orders")),
        ("err_foreign_domain", ("alpha", "spiffe://evil.example/ns/alpha/sa/orders")),
        ("err_dot_segment", ("alpha", "spiffe://estate.local/ns/alpha/../admin")),
        ("err_cross_tenant", ("alpha", "spiffe://estate.local/ns/beta/sa/orders")),
        ("err_query", ("alpha", "spiffe://estate.local/ns/alpha/sa/x?y=1")),
    ],
    "bypass": [
        ("plaintext_to_meshed", ("alpha", "legacy-cron", "payments", False)),
        ("mtls_to_meshed", ("alpha", "orders", "payments", True)),
        ("plaintext_to_unmeshed", ("alpha", "cron", "weather", False)),
        ("err_non_bool_mtls", ("alpha", "cron", "payments", "false")),
    ],
}


def run_case(svc, iface, args):
    try:
        if iface == "reconcile":
            route, app, mesh, budget = args
            return {"response": svc.reconcile(S.CTRL_A, "alpha", route, app, mesh, budget)}
        if iface == "identity":
            tenant, san = args
            return {"response": svc.map_identity(S.NODE, tenant, san)}
        tenant, src, dst, mtls = args
        return {"response": svc.report_flow(S.NODE, tenant, src, dst, mtls)}
    except S.errors.MeshError as e:
        env = e.to_envelope()
        env["correlation_id"] = None  # nondeterministic; schema allows null
        env["message"] = "<omitted>"
        return {"error": env}


def build() -> dict[str, dict]:
    out = {}
    svc, _, _ = S.make_service()
    for iface, cases in CASES.items():
        for name, args in cases:
            out[f"{iface}/{name}.json"] = {"interface": iface, "request": list(args), **run_case(svc, iface, args)}
    out["config/secure_defaults.json"] = S.config.SECURE_DEFAULTS
    out["config/example_site_overlay.json"] = {"version": "site-eu-1", "tenants": ["alpha"], "meshed_destinations": ["payments"],
                                                "limits": {"max_inflight": 64}}
    return out


def main(argv):
    files = build()
    drift = []
    for rel, data in files.items():
        p = ROOT / "fixtures" / rel
        text = json.dumps(data, indent=2, sort_keys=True) + "\n"
        if "--check" in argv:
            if not p.exists() or p.read_text() != text:
                drift.append(rel)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
    if drift:
        print("fixture drift:", ", ".join(drift))
        return 1
    print(f"{len(files)} fixtures {'verified' if '--check' in argv else 'written'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
