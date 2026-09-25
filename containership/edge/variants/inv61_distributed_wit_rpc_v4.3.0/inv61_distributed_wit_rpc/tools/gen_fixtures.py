"""Regenerate golden conformance fixtures (tests/fixtures/golden.json).

Fixtures are deterministic byte encodings of reference values under the
reference WIT interface plus one fully signed request frame with a fixed
test key.  An independent implementation passes conformance when it
produces/accepts exactly these bytes.  ``--check`` fails on drift.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
_pkg = PKG.name
codec = __import__(f"{_pkg}.codec", fromlist=["x"])
wit_model = __import__(f"{_pkg}.wit_model", fromlist=["x"])
security = __import__(f"{_pkg}.security", fromlist=["x"])
rpc = __import__(f"{_pkg}.rpc", fromlist=["x"])
OUT = PKG / "tests" / "fixtures" / "golden.json"

TEST_KEY = security.Key("fixture-k1", "fixture-client", bytes(range(32)))


def build() -> dict:
    kv = wit_model.parse((PKG / "wit" / "kv.wit").read_text())[0]
    entry = kv.resolve(("ref", "entry"))
    values = [
        ("u64", 2**64 - 1), ("s32", -5), ("f64-nan", float("nan")), ("string", "héllo \U0001F600"),
        ("option<u64>", None), ("option<u64>", 7), ("result<_, string>", ("err", "no")),
        ("entry", {"key": "k", "value": 1, "tags": ["a", "b"]}), ("consistency", "strong"),
        ("list<u8>", [0, 1, 255]),
    ]
    types = {"u64": "u64", "s32": "s32", "f64-nan": "f64", "string": "string",
             "option<u64>": ("option", "u64"), "result<_, string>": ("result", None, "string"),
             "entry": entry, "consistency": kv.resolve(("ref", "consistency")), "list<u8>": ("list", "u8")}
    vals = [{"type": n, "hex": codec.encode(types[n], v).hex()} for n, v in values]
    f = kv.funcs["get"]
    env = {"request_id": "fixture-0001", "sender": "", "tenant": "default", "nonce": "00112233445566778899aabbccddeeff",
           "issued_ms": 1_790_000_000_000, "deadline_ms": 1_790_000_005_000, "interface": kv.qualified,
           "version": kv.version, "function": "get", "fp": rpc.fingerprint(f.param_types(), f.result_types()),
           "idempotency_key": None, "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
           "args": codec.encode(("tuple", ("string",)), ["k"]), "key_id": "", "mac": b""}
    env = security.sign(env, TEST_KEY)
    frame = codec.pack_frame(codec.KIND_REQUEST, codec.encode(codec.REQUEST_ENVELOPE, env), 2, 1)
    return {"schema": "inv61-fixtures/1", "interface_digest": kv.digest,
            "fingerprints": {n: rpc.fingerprint(fn.param_types(), fn.result_types()) for n, fn in sorted(kv.funcs.items())},
            "values": vals, "test_key_hex": TEST_KEY.secret.hex(), "request_frame_hex": frame.hex()}


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true")
    text = json.dumps(build(), indent=2) + "\n"
    if ap.parse_args().check:
        ok = OUT.exists() and OUT.read_text() == text
        print("fixtures", "OK" if ok else "DRIFT")
        return 0 if ok else 1
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
