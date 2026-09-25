#!/usr/bin/env python3
"""Validate JSON artifacts against the published schemas (M09), dependency-free.

Implements the JSON Schema 2020-12 keywords the published schemas use: $ref (local #/$defs),
type, const, enum, required, properties, additionalProperties, items, prefixItems, minItems,
maxItems, uniqueItems, pattern, minLength, minimum, maximum, anyOf. Any other keyword in a
schema is a hard error, so the subset can never silently under-validate. When the optional
`jsonschema` package is installed, --strict also runs it (including meta-schema checks).

  python tools/schema_check.py                      # validate every repository artifact
  python tools/schema_check.py SCHEMA INSTANCE      # validate one file
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
SUPPORTED = {"$schema", "$id", "$defs", "$ref", "title", "description", "type", "const", "enum", "required",
             "properties", "additionalProperties", "items", "prefixItems", "minItems", "maxItems", "uniqueItems",
             "pattern", "minLength", "minimum", "maximum", "anyOf"}
TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}
DEFAULT_PAIRS = [
    ("schemas/translation-map-v1.schema.json", "map/TRANSLATION_MAP.json"),
    ("schemas/toolchain-lock-v1.schema.json", "toolchains/LOCK.json"),
    ("schemas/verify-v2.schema.json", "schemas/fixtures/verify-v2.valid.json"),
]


def _is_type(v, t):
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, TYPES[t]) and not (t != "boolean" and isinstance(v, bool) and TYPES[t] is not bool)


def check_schema_keywords(schema, path="#"):
    if isinstance(schema, dict):
        unknown = set(schema) - SUPPORTED
        if unknown and not path.endswith("/properties") and not path.endswith("/$defs"):
            raise ValueError(f"unsupported schema keyword(s) at {path}: {sorted(unknown)}")
        for k, v in schema.items():
            check_schema_keywords(v, f"{path}/{k}")
    elif isinstance(schema, list):
        for i, v in enumerate(schema):
            check_schema_keywords(v, f"{path}/{i}")


def validate(inst, schema, root=None, where="$", errors=None, limit=50):
    root = root if root is not None else schema
    errors = [] if errors is None else errors
    if len(errors) >= limit:
        return errors
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            raise ValueError(f"only local $ref supported: {ref}")
        target = root
        for part in ref[2:].split("/"):
            target = target[part]
        validate(inst, target, root, where, errors, limit)
    t = schema.get("type")
    if t is not None:
        ts = t if isinstance(t, list) else [t]
        if not any(_is_type(inst, x) for x in ts):
            errors.append(f"{where}: expected type {t}, got {type(inst).__name__}")
            return errors
    if "const" in schema and inst != schema["const"]:
        errors.append(f"{where}: must equal {schema['const']!r}")
    if "enum" in schema and inst not in schema["enum"]:
        errors.append(f"{where}: {inst!r} not in {schema['enum']}")
    if "anyOf" in schema and not any(not validate(inst, s, root, where, [], limit) for s in schema["anyOf"]):
        errors.append(f"{where}: matches none of anyOf")
    if isinstance(inst, str):
        if "minLength" in schema and len(inst) < schema["minLength"]:
            errors.append(f"{where}: shorter than {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], inst):
            errors.append(f"{where}: {inst[:60]!r} does not match {schema['pattern']}")
    if _is_type(inst, "number"):
        if "minimum" in schema and inst < schema["minimum"]:
            errors.append(f"{where}: {inst} < minimum {schema['minimum']}")
        if "maximum" in schema and inst > schema["maximum"]:
            errors.append(f"{where}: {inst} > maximum {schema['maximum']}")
    if isinstance(inst, dict):
        for k in schema.get("required", []):
            if k not in inst:
                errors.append(f"{where}: missing required property {k!r}")
        props = schema.get("properties", {})
        for k, v in inst.items():
            if k in props:
                validate(v, props[k], root, f"{where}.{k}", errors, limit)
            elif "additionalProperties" in schema:
                ap = schema["additionalProperties"]
                if ap is False:
                    errors.append(f"{where}: unexpected property {k!r}")
                elif isinstance(ap, dict):
                    validate(v, ap, root, f"{where}.{k}", errors, limit)
    if isinstance(inst, list):
        if "minItems" in schema and len(inst) < schema["minItems"]:
            errors.append(f"{where}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(inst) > schema["maxItems"]:
            errors.append(f"{where}: more than {schema['maxItems']} items")
        if schema.get("uniqueItems"):
            seen = [json.dumps(x, sort_keys=True) for x in inst]
            if len(seen) != len(set(seen)):
                errors.append(f"{where}: items are not unique")
        pre = schema.get("prefixItems", [])
        for i, v in enumerate(inst):
            if i < len(pre):
                validate(v, pre[i], root, f"{where}[{i}]", errors, limit)
            elif "items" in schema:
                validate(v, schema["items"], root, f"{where}[{i}]", errors, limit)
    return errors


def validate_file(schema_path: Path, inst_path: Path, strict=False):
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    check_schema_keywords(schema)
    inst = json.loads(inst_path.read_text(encoding="utf-8"))
    errs = validate(inst, schema)
    if strict:
        import jsonschema  # optional release-environment dependency
        jsonschema.Draft202012Validator.check_schema(schema)
        errs += [f"jsonschema: {e.message}" for e in jsonschema.Draft202012Validator(schema).iter_errors(inst)]
    return errs


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    strict = "--strict" in args
    args = [a for a in args if a != "--strict"]
    pairs = [(args[0], args[1])] if len(args) == 2 else DEFAULT_PAIRS
    ev = PKG / "evidence/VERIFY.json"
    if len(args) != 2 and json.loads(ev.read_text(encoding="utf-8")).get("schema") == "IOS735_LCTL/VERIFY/2":
        pairs = pairs + [("schemas/verify-v2.schema.json", "evidence/VERIFY.json")]
    bad = 0
    for s, i in pairs:
        errs = validate_file(PKG / s if not Path(s).is_absolute() else Path(s), PKG / i if not Path(i).is_absolute() else Path(i), strict)
        if errs:
            bad += 1
            print(f"FAIL: {i} vs {Path(s).name}")
            for e in errs[:20]:
                print("   ", e)
        else:
            print(f"PASS: {i} vs {Path(s).name}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
