"""Item 19: produced artifacts validate against the shipped JSON Schemas.

Needs ``jsonschema``; without it the test SKIPs with the reason, and the
release gate counts that skip as NOT_RUN, never as PASS.
"""
import json
import os
import unittest

from hkit import REQUESTER, build, hardened_pod, request

from inv03_container_hardening.hardening.baseline import Keyring, default_document, sign_baseline

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

SCHEMAS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schemas")


def load(name):
    with open(os.path.join(SCHEMAS, name)) as fh:
        return json.load(fh)


@unittest.skipIf(jsonschema is None, "jsonschema not installed (lane: schema)")
class Schemas(unittest.TestCase):
    def test_schemas_are_valid_2020_12(self):
        for f in os.listdir(SCHEMAS):
            jsonschema.Draft202012Validator.check_schema(load(f))

    def test_decisions_conform(self):
        eng, *_ = build()
        v = jsonschema.Draft202012Validator(load("pk_harden_eval.v2.schema.json"))
        bad = hardened_pod()
        bad["hostPID"] = True
        for d in (eng.decide(request()), eng.decide(request(bad)), eng.decide(None), eng.decide(request(workload=""))):
            v.validate(json.loads(json.dumps(d)))
        forged = dict(eng.decide(request()), failed=["seccomp"])
        self.assertFalse(v.is_valid(forged))

    def test_signed_baseline_conforms(self):
        art = sign_baseline(default_document(), Keyring({"r": b"s" * 32}), "r")
        jsonschema.Draft202012Validator(load("pk_harden_baseline.v2.schema.json")).validate(art)

    def test_exception_events_conform(self):
        eng, *_ = build()
        eng.exceptions.request(REQUESTER, "w", "seccomp", "r", "T-1", "o", 60)
        v = jsonschema.Draft202012Validator(load("pk_harden_exception.v2.schema.json"))
        ev = [e for e in eng.ledger.events() if e["kind"] == "exception.requested"][0]
        v.validate(ev["data"])


if __name__ == "__main__":
    unittest.main()
