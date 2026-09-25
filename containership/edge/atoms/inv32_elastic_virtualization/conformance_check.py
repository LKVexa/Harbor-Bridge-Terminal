"""Run the published conformance vectors against this implementation (WS 3).  Exit 0 == conformant."""
from __future__ import annotations

import json
from pathlib import Path
import sys

from . import errors as E
from .model import _canonical_hash
from .validation import decode_request, iter_errors, load_schema

FIXTURES = Path(__file__).resolve().parent / "conformance"


def run() -> list[str]:
    failures: list[str] = []
    vec = json.loads((FIXTURES / "request_v2_vectors.json").read_text())
    schema = load_schema("request")
    for i, doc in enumerate(vec["valid"]):
        if iter_errors(doc, schema):
            failures.append(f"valid[{i}] rejected")
        try:
            decode_request(json.dumps(doc))
        except E.ControlError as exc:
            failures.append(f"valid[{i}] decoder rejected: {exc.code}")
    for case in vec["invalid"]:
        try:
            decode_request(json.dumps(case["doc"]))
            failures.append(f"invalid:{case['name']} accepted")
        except E.ControlError:
            pass
    for case in json.loads((FIXTURES / "decoder_negative_vectors.json").read_text()):
        try:
            decode_request(case["raw"])
            failures.append(f"decoder:{case['name']} accepted")
        except E.ControlError as exc:
            if "code" in case and exc.code != case["code"]:
                failures.append(f"decoder:{case['name']} wrong code {exc.code}")
    canon = json.loads((FIXTURES / "audit_canonical_v1.json").read_text(encoding="utf-8"))
    if _canonical_hash(canon["event_without_hash"]) != canon["sha256"]:
        failures.append("audit canonical hash mismatch")
    return failures


def main() -> int:
    failures = run()
    print(json.dumps({"schema": "PK_CONFORMANCE_RESULT/1", "ok": not failures, "failures": failures}, indent=1))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
