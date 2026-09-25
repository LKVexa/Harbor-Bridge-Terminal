"""Language-neutral JSON wire binding for the four interfaces (MC-012, MC-015, MC-018).

``handle(runtime, request_json) -> response_json``.  Requests are validated
against the packaged JSON Schemas (a dependency-free subset validator covering
exactly the keywords those schemas use) before dispatch; every failure returns a
``pk.error-envelope/1``.  Bytes travel as base64.
"""
from __future__ import annotations

import base64
import binascii
import json
import pathlib
import re
from typing import Any

from .envelope import dumps, to_envelope
from .runtime import InvalidRuntimeInput

SCHEMA_DIR = pathlib.Path(__file__).resolve().parent / "schemas"
MAX_REQUEST_BYTES = 2 * 1024 * 1024
_ROUTE = {"PK_STATE/1": "pk_state.v1.request", "PK_MESSAGE/1": "pk_message.v1.request",
          "PK_SECRET/1": "pk_secret.v1.request", "PK_INVOKE/1": "pk_invoke.v1.request"}
_CACHE: dict[str, dict] = {}
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def load_schema(name: str) -> dict:
    if name not in _CACHE:
        _CACHE[name] = json.loads((SCHEMA_DIR / f"{name}.json").read_text(encoding="utf-8"))
    return _CACHE[name]


def _type_ok(v: Any, t: str) -> bool:
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _TYPES[t])


def check(v: Any, s: dict, path: str = "$") -> None:
    def bad(msg: str) -> None:
        raise InvalidRuntimeInput(f"{path}: {msg}", field=path)
    if "const" in s and v != s["const"]:
        bad("const mismatch")
    if "enum" in s and v not in s["enum"]:
        bad("not in enum")
    if "type" in s:
        ts = s["type"] if isinstance(s["type"], list) else [s["type"]]
        if not any(_type_ok(v, t) for t in ts):
            bad(f"expected {ts}")
    if isinstance(v, str):
        if len(v) < s.get("minLength", 0) or len(v) > s.get("maxLength", 1 << 62):
            bad("length out of bounds")
        if "pattern" in s and not re.search(s["pattern"], v):
            bad("pattern mismatch")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if "exclusiveMinimum" in s and not v > s["exclusiveMinimum"]:
            bad("below minimum")
        if "minimum" in s and v < s["minimum"]:
            bad("below minimum")
        if "maximum" in s and v > s["maximum"]:
            bad("above maximum")
    if isinstance(v, dict):
        for r in s.get("required", []):
            if r not in v:
                bad(f"missing {r}")
        props = s.get("properties", {})
        for k, item in v.items():
            if k in props:
                check(item, props[k], f"{path}.{k}")
            elif s.get("additionalProperties") is False:
                bad(f"unexpected property {k}")
            elif isinstance(s.get("additionalProperties"), dict):
                check(item, s["additionalProperties"], f"{path}.{k}")
    if isinstance(v, list):
        if len(v) > s.get("maxItems", 1 << 62) or len(v) < s.get("minItems", 0):
            bad("item count out of bounds")
        pre = s.get("prefixItems", [])
        for i, item in enumerate(v):
            if i < len(pre):
                check(item, pre[i], f"{path}[{i}]")
            elif "items" in s:
                check(item, s["items"], f"{path}[{i}]")


def _b(v: str | None) -> bytes:
    try:
        return base64.b64decode(v or "", validate=True)
    except (binascii.Error, ValueError):
        raise InvalidRuntimeInput("invalid base64", field="payload") from None


def _e(b: bytes | None) -> str | None:
    return None if b is None else base64.b64encode(b).decode()


def handle(rt, request_json: str | bytes) -> str:
    trace = None
    try:
        if len(request_json) > MAX_REQUEST_BYTES:
            raise InvalidRuntimeInput("request exceeds wire ceiling", limit=MAX_REQUEST_BYTES)
        try:
            req = json.loads(request_json)
        except (ValueError, RecursionError):
            raise InvalidRuntimeInput("request is not valid JSON") from None
        if not isinstance(req, dict) or not isinstance(req.get("interface"), str) or req["interface"] not in _ROUTE:
            raise InvalidRuntimeInput("unknown interface")
        check(req, load_schema(_ROUTE[req["interface"]]))
        ctx = dict(token=req["token"], deadline_s=req.get("deadline_s"), traceparent=req.get("traceparent"))
        if req.get("traceparent"):
            trace = req["traceparent"].split("-")[1]
        w, t, op = req["workload"], req["tenant"], req["op"]
        if req["interface"] == "PK_STATE/1":
            if op == "get":
                result: Any = {"value": _e(rt.state_get(w, t, req["key"], **ctx))}
            elif op == "set":
                rt.state_set(w, t, req["key"], _b(req.get("value")), **ctx)
                result = {}
            elif op == "delete":
                result = {"deleted": rt.state_delete(w, t, req["key"], **ctx)}
            else:
                ops = [(v, k, None if x is None else _b(x)) for v, k, x in req.get("operations", [])]
                rt.state_transact(w, t, ops, **ctx)
                result = {}
        elif req["interface"] == "PK_MESSAGE/1":
            if op == "publish":
                r = rt.publish(w, t, req["topic"], _b(req.get("payload")), req.get("idempotency_key", ""), **ctx)
                result = {"accepted": r.accepted, "delivery": r.outcome}
            else:
                result = {"messages": [_e(m) for m in rt.subscribe(w, t, req["topic"], **ctx)]}
        elif req["interface"] == "PK_SECRET/1":
            result = {"value": _e(rt.secret_fetch(w, t, req["reference"], **ctx))}
        else:
            result = {"payload": _e(rt.invoke(w, t, req["component"], _b(req["payload"]), **ctx))}
        return json.dumps({"ok": True, "result": result}, sort_keys=True)
    except Exception as exc:  # noqa: BLE001 - every failure is enveloped
        return json.dumps({"ok": False, "error": json.loads(dumps(to_envelope(exc, trace_id=trace)))},
                          sort_keys=True)
