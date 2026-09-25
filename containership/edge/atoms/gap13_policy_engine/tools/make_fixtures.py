"""Regenerate golden fixtures (deterministic Ed25519 test keys).  Run from repo parent:
python -m gap13_policy_engine.tools.make_fixtures
"""
from __future__ import annotations

import base64
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tests"))
import testkit as k  # noqa: E402

FX = HERE / "fixtures"


def build() -> dict[str, object]:
    out: dict[str, object] = {}
    ts = k.trust_store()
    out["trust_store.json"] = {"schema": "PK_POLICY_TRUST_STORE/1", "version": ts.version, "fetched_at": 0, "keys": [
        {"key_id": t.key_id, "algorithm": t.algorithm, "public_key_b64": base64.b64encode(t.public_key).decode(),
         "issuer": t.issuer, "environments": list(t.environments), "not_before": t.not_before,
         "not_after": t.not_after} for t in ts.keys.values()]}
    out["bundle_v1.json"] = k.bundle_doc(1)
    out["envelope_v1.json"] = json.loads(k.envelope(1))
    r = k.verified(1)
    eng = k.g.PolicyEngine("prod")
    eng.activate(r)
    out["verdict_allow.golden.json"] = eng.evaluate({"action": "read", "classification": "public"})
    out["verdict_deny_specific.golden.json"] = eng.evaluate({"action": "read", "classification": "pii"})
    out["verdict_default_deny.golden.json"] = eng.evaluate({"action": "write"})
    out["explanation.golden.json"] = eng.explain({"action": "read", "classification": "pii"})
    return out


def main() -> None:
    FX.mkdir(exist_ok=True)
    for name, doc in build().items():
        (FX / name).write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("fixtures written:", len(build()))


if __name__ == "__main__":
    main()
