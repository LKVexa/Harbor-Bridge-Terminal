"""Generate language-neutral golden fixtures (M23). Deterministic: re-running
must produce byte-identical files (CI checks this)."""
import hashlib, json, pathlib, sys
PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent)); sys.dont_write_bytecode = True
from inv60_wasm_application_fabric.fabric.errors import REGISTRY, Result
from inv60_wasm_application_fabric.fabric.wasm_backend import build_module

OP = "op-" + "0" * 31 + "1"
META = {"protocol": "1.0", "operation_id": OP}
D = "sha256:" + "ab" * 32
C = []
def fx(name, schema, inst, valid, note):
    C.append({"name": name, "schema": schema, "instance": inst, "expect_valid": valid, "note": note})
fx("start.ok", "PK_LATTICE_START", {"meta": META, "component": "api", "artifact": D, "tenant": "tenant-a"}, True, "success")
fx("start.regions.boundary", "PK_LATTICE_START", {"meta": META, "component": "a" * 63, "artifact": D, "tenant": "t", "regions": ["eu"] * 16}, True, "max lengths")
fx("start.regions.over", "PK_LATTICE_START", {"meta": META, "component": "api", "artifact": D, "tenant": "t", "regions": ["eu"] * 17}, False, "limit+1")
fx("start.unknown_field", "PK_LATTICE_START", {"meta": META, "component": "api", "artifact": D, "tenant": "t", "tag": "latest"}, False, "unknown field rejected (tag substitution)")
fx("start.bad_digest", "PK_LATTICE_START", {"meta": META, "component": "api", "artifact": "sha1:abc", "tenant": "t"}, False, "algorithm not allowed")
fx("start.unknown_enum_protocol", "PK_LATTICE_START", {"meta": {**META, "protocol": "9.9"}, "component": "api", "artifact": D, "tenant": "t"}, False, "unknown enum")
fx("start.deadline.zero", "PK_LATTICE_START", {"meta": {**META, "deadline_ms": 0}, "component": "api", "artifact": D, "tenant": "t"}, False, "deadline boundary")
fx("link.ok", "PK_LATTICE_LINK", {"meta": META, "component": "api", "link": "kv", "tenant": "t", "interface": "wasi:keyvalue/store@0.2.0", "operations": ["get", "set"], "ttl_s": 3600}, True, "success")
fx("link.no_ops", "PK_LATTICE_LINK", {"meta": META, "component": "api", "link": "kv", "tenant": "t", "interface": "wasi:keyvalue/store@0.2.0", "operations": []}, False, "wildcard/empty authority refused")
fx("link.malformed", "PK_LATTICE_LINK", {"meta": META, "component": "API!", "link": "kv", "tenant": "t", "interface": "x", "operations": ["get"]}, False, "malformed identifiers")
fx("call.ok", "PK_LATTICE_CALL", {"meta": {**META, "deadline_ms": 250, "traceparent": "00-" + "1" * 32 + "-" + "2" * 16 + "-01"}, "component": "api", "link": "kv", "tenant": "t", "operation": "get"}, True, "success with deadline + trace")
fx("call.idem_short", "PK_LATTICE_CALL", {"meta": {**META, "idempotency_key": "short"}, "component": "api", "link": "kv", "tenant": "t", "operation": "get"}, False, "idempotency key too short")
for code in sorted(REGISTRY):
    w = Result(code, message=f"golden {code}", operation_id=OP, timestamp=0.0).to_wire()
    if w["retry"] == "after": w["retry_after_s"] = 1.0
    fx(f"result.{code}", "RESULT", w, True, "golden result/error envelope")
fx("result.unknown_outcome", "RESULT", {**Result("OK", operation_id=OP, timestamp=0.0).to_wire(), "outcome": "maybe"}, False, "unknown enum")
out = PKG / "fixtures"; out.mkdir(exist_ok=True)
for c in C:
    body = json.dumps(c, sort_keys=True, indent=1) + "\n"
    (out / f"{c['name']}.json").write_text(body)
wasm = build_module("add")
(out / "add.wasm").write_bytes(wasm)
index = {"fixture_version": "1.0.0", "interface_version": "1.0", "normalization": "UTF-8 JSON, keys sorted, 1-space indent; compare parsed values, not bytes",
         "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob("*")) if p.name not in ("INDEX.json", "validate.mjs")}}
(out / "INDEX.json").write_text(json.dumps(index, sort_keys=True, indent=1) + "\n")
print(len(C), "fixtures")
