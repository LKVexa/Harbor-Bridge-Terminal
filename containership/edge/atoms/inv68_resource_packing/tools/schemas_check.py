"""Schema conformance of examples and live documents (INV-68 MC-07, MC-29; C022, C029, C082).

    python -m inv68_resource_packing.tools.schemas_check [--out evidence/]

Validates every ``examples/*.json`` file and live documents produced by the
running code (service response, status, error, explain, audit record,
configuration) against ``schemas/*.schema.json`` using ``jsonschema``
(Draft 2020-12, with a local registry so ``$ref`` between schemas resolves
offline).  Negative fixtures must be rejected.  Without ``jsonschema`` the
result is FAIL (never silently skipped).
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from .common import PKG, write

EXAMPLE_SCHEMA = {
    "pack_request.json": "PK_PACK_REQUEST_1",
    "pack_response.json": "PK_PACK_RESPONSE_1",
    "capacity_report.json": "PK_PACK_CAPACITY_1",
    "fragmentation_report.json": "PK_PACK_FRAG_1",
    "config.json": "PK_PACK_CONFIG_1",
    "service_request.json": "PK_PACK_REQUEST_1",
}
NEGATIVE = [
    ("PK_PACK_REQUEST_1", {"workloads": [{"name": "", "cpu": 1, "mem": 1}]}),
    ("PK_PACK_REQUEST_1", {"workloads": [], "surprise": 1}),
    ("PK_PACK_CONFIG_1", {"schema": "PK_PACK_CONFIG/1", "mem_overcommit": 2}),
    ("PK_PACK_CAPACITY_1", {"cpu": 0, "mem": 1, "headroom": 1, "effective_cpu": 0, "effective_mem": 0}),
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG / "evidence"))
    a = ap.parse_args(argv)
    try:
        import jsonschema
        from referencing import Registry, Resource
    except ImportError as exc:
        write(Path(a.out) / "SCHEMAS.json", {"schema": "PK_PACK_SCHEMAS/1", "result": "FAIL",
                                             "reason": f"jsonschema unavailable: {exc}"})
        return 1
    schemas = {p.name.replace(".schema.json", ""): json.loads(p.read_text()) for p in (PKG / "schemas").glob("*.schema.json")}
    registry = Registry().with_resources([(s["$id"], Resource.from_contents(s)) for s in schemas.values()])

    def check(name, doc):
        v = jsonschema.Draft202012Validator(schemas[name], registry=registry)
        return [e.message[:160] for e in v.iter_errors(doc)]
    rows = []
    for meta in schemas.values():
        jsonschema.Draft202012Validator.check_schema(meta)
    for fname, sname in EXAMPLE_SCHEMA.items():
        path = PKG / "examples" / fname
        errs = check(sname, json.loads(path.read_text())) if path.exists() else ["missing example"]
        rows.append({"document": f"examples/{fname}", "schema": sname, "errors": errs})
    # live documents
    from inv68_resource_packing.audit import AuditLog
    from inv68_resource_packing.auth import Authorizer, mint
    from inv68_resource_packing.config import ConfigStore, defaults, plain
    from inv68_resource_packing.errors import PackError
    from inv68_resource_packing.service import PackingService
    key = {"k": b"s" * 32}
    with tempfile.TemporaryDirectory() as tmp:
        audit = AuditLog(Path(tmp) / "a.jsonl")
        store = ConfigStore(Path(tmp) / "c", audit=audit)
        store.activate(defaults(), actor="schemas", epoch=1)
        svc = PackingService(store, Authorizer(key), audit)
        tok = lambda: mint(key["k"], kid="k", sub="s", kind="workload-scheduler", tenants=["t"], caps=["pack:submit"])
        req = json.loads((PKG / "examples" / "service_request.json").read_text())
        resp = svc.pack(req, tok())
        try:
            svc.pack(dict(req, tenant="other"), tok())
            err = {}
        except PackError as e:
            err = e.to_dict()
        live = [("live:service_response", "PK_PACK_SERVICE_RESPONSE_1", resp),
                ("live:explain", "PK_PACK_EXPLAIN_1", resp["explain"]),
                ("live:status", "PK_PACK_STATUS_1", svc.status()),
                ("live:error", "PK_PACK_ERROR_1", err),
                ("live:config", "PK_PACK_CONFIG_1", plain(svc.config.document))]
        live += [(f"live:audit#{r['seq']}", "PK_PACK_AUDIT_1", r) for r in audit.records()]
        for name, sname, doc in live:
            rows.append({"document": name, "schema": sname, "errors": check(sname, json.loads(json.dumps(doc)))})
    for sname, doc in NEGATIVE:
        rows.append({"document": f"negative:{sname}", "schema": sname, "expect_reject": True,
                     "errors": [] if check(sname, doc) else ["negative fixture was accepted"]})
    bad = [r for r in rows if r["errors"]]
    write(Path(a.out) / "SCHEMAS.json", {"schema": "PK_PACK_SCHEMAS/1", "validator": f"jsonschema Draft 2020-12",
                                         "checked": len(rows), "failures": bad, "rows": rows,
                                         "result": "PASS" if not bad else "FAIL"})
    print(f"SCHEMAS {'PASS' if not bad else 'FAIL'}: {len(rows)} documents, {len(bad)} failures")
    for r in bad:
        print("  ", r["document"], r["errors"][:2])
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
