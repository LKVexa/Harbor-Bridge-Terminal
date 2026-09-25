"""Execute every ``fixtures/v<major>/*.json`` conformance fixture (C029)."""
from __future__ import annotations

import json
import pathlib

from . import wire
from .adapters import RemoteEndpoint
from .auth import Authenticator, KeyRing
from .config import ConfigStore
from .errors import ErrorRecord
from .runtime import Runtime

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _subst(obj, env):
    if isinstance(obj, str) and obj.startswith("$"):
        return env[obj[1:]]
    if isinstance(obj, dict):
        return {k: _subst(v, env) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_subst(v, env) for v in obj]
    return obj


def run_fixture(fx: dict) -> dict:
    if "expected_text" in fx:
        rec = ErrorRecord.from_dict(fx["record"])
        got = wire.encode(rec.to_dict()).decode()
        ok = got == fx["expected_text"] and not wire.validate(fx["record"], "PK_FUTURE_ERROR/1")
        return {"id": fx["id"], "passed": ok, "detail": None if ok else got}
    rt = Runtime(ConfigStore({"environment": "test"}))
    kr = KeyRing()
    kr.add("fx", b"f" * 32)
    au = Authenticator(kr)
    ep = RemoteEndpoint(rt, au)
    env: dict = {}
    for i, st in enumerate(fx["steps"]):
        tok = au.issue(st.get("sub", "fixture-tenant"), st["caps"])
        if "raw" in st:
            blob = st["raw"].encode()
        elif "raw_size" in st:
            blob = b" " * st["raw_size"]
        else:
            blob = wire.encode(_subst(st["doc"], env))
        resp = json.loads(ep.handle(st["op"], blob, tok))
        exp = st["expect"]
        problems = []
        if resp["ok"] != exp["ok"]:
            problems.append(f"ok={resp['ok']} expected {exp['ok']} ({resp.get('error')})")
        if "code" in exp and (resp.get("error") or {}).get("code") != exp["code"]:
            problems.append(f"code={(resp.get('error') or {}).get('code')} expected {exp['code']}")
        if "result" in exp and resp.get("result") != exp["result"]:
            problems.append(f"result={resp.get('result')} expected {exp['result']}")
        if not resp["ok"] and wire.validate(resp["error"], "PK_FUTURE_ERROR/1"):
            problems.append("error record violates PK_FUTURE_ERROR/1")
        if problems:
            return {"id": fx["id"], "passed": False, "step": i, "detail": "; ".join(problems)}
        if st.get("save") and resp["ok"]:
            env[st["save"]] = resp["result"]["future_id"]
    return {"id": fx["id"], "passed": True}


def run_all(major: int = 1) -> list[dict]:
    out = []
    for p in sorted((FIXTURES / f"v{major}").glob("*.json")):
        out.append(run_fixture(json.loads(p.read_text())))
    return out
