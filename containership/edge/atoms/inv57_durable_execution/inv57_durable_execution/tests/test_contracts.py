"""MC-51/MC-10: public boundary documents conform to the checked-in schemas,
and the schemas have not drifted from the code (stdlib mini-validator)."""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import unittest

from . import _path  # noqa: F401

from inv57_durable_execution import config, errors
from inv57_durable_execution.durable import NonDeterminism
from inv57_durable_execution.identity import WorkflowIdentity
from inv57_durable_execution.status import StatusSurface

PKG = pathlib.Path(__file__).resolve().parents[1]
_T = {"object": dict, "string": str, "integer": int, "number": (int, float), "boolean": bool,
      "array": list, "null": type(None)}


def check(doc, schema, path="$"):
    errs = []
    t = schema.get("type")
    if t:
        types = t if isinstance(t, list) else [t]
        ok = any(isinstance(doc, _T[x]) and not (x in ("integer", "number") and isinstance(doc, bool))
                 for x in types)
        if not ok:
            return [f"{path}: type {type(doc).__name__} not in {types}"]
    if "const" in schema and doc != schema["const"]:
        errs.append(f"{path}: != const")
    if "enum" in schema and doc not in schema["enum"]:
        errs.append(f"{path}: {doc!r} not in enum")
    if isinstance(doc, str):
        if "pattern" in schema and not re.fullmatch(schema["pattern"].strip("^$"), doc):
            errs.append(f"{path}: pattern")
        if len(doc) > schema.get("maxLength", 1 << 30) or len(doc) < schema.get("minLength", 0):
            errs.append(f"{path}: length")
    if isinstance(doc, (int, float)) and not isinstance(doc, bool):
        if doc < schema.get("minimum", float("-inf")) or doc > schema.get("maximum", float("inf")):
            errs.append(f"{path}: range")
    if isinstance(doc, dict):
        for r in schema.get("required", []):
            if r not in doc:
                errs.append(f"{path}: missing {r}")
        props = schema.get("properties", {})
        for k, v in doc.items():
            if k in props:
                errs += check(v, props[k], f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: extra {k}")
    if isinstance(doc, list) and "items" in schema:
        for i, v in enumerate(doc):
            errs += check(v, schema["items"], f"{path}[{i}]")
    return errs


def schema(name):
    return json.loads((PKG / "schemas" / f"{name}.schema.json").read_text())


class ContractTests(unittest.TestCase):
    def test_no_schema_drift(self):
        r = subprocess.run([sys.executable, str(PKG / "tools" / "gen_schemas.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_documents_conform(self):
        ident = WorkflowIdentity("t", "e", "s", "n", "w", "r")
        self.assertEqual(check(ident.to_dict(), schema("identity")), [])
        for exc in (NonDeterminism("x"), errors.StaleOwner("y"), KeyError("z")):
            self.assertEqual(check(errors.describe(exc), schema("error")), [])
        st = StatusSurface(version="4.3.0", config_digest="d", config_generation=0, environment="dev",
                           site="s", probes={"config": lambda: (True, "ok")}).document()
        self.assertEqual(check(st, schema("status")), [])
        self.assertEqual(check(config.defaults(), schema("config")), [])
        for ev in json.loads((PKG / "fixtures" / "history_v2_golden.json").read_text()):
            self.assertEqual(check(ev, schema("history_event")), [])

    def test_validator_rejects_bad_documents(self):
        bad = WorkflowIdentity("t", "e", "s", "n", "w", "r").to_dict()
        bad["tenant"] = "a\nb"
        bad["extra"] = 1
        errs = check(bad, schema("identity"))
        self.assertTrue(any("pattern" in e for e in errs) and any("extra" in e for e in errs))
        self.assertTrue(check({"max_history_events": 1}, schema("config")))


if __name__ == "__main__":
    unittest.main()
