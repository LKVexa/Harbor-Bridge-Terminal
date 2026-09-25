"""MC-006 / MC-028: golden fixtures, schema conformance of every output, seeded fuzz/property tests."""
from __future__ import annotations

import json
import pathlib
import random
import string
import subprocess
import sys
import unittest

from _support import CTRL_A, NODE, PKG_DIR, config, errors, make_service, mesh, operator

try:
    import jsonschema
except ModuleNotFoundError:  # pragma: no cover
    jsonschema = None

SCHEMAS = PKG_DIR / "schemas"
FIX = PKG_DIR / "fixtures"
FUZZ_N = 4000


def schema(name):
    return json.loads((SCHEMAS / name).read_text())


@unittest.skipIf(jsonschema is None, "jsonschema not installed (declared test dependency, see pyproject.toml)")
class ConformanceTest(unittest.TestCase):
    def test_all_schemas_are_valid_draft_2020_12(self):
        for p in SCHEMAS.glob("*.json"):
            jsonschema.Draft202012Validator.check_schema(json.loads(p.read_text()))

    def test_golden_fixtures_validate(self):
        names = {"reconcile": "PK_MESH_RECONCILE-1", "identity": "PK_MESH_IDENTITY-1", "bypass": "PK_MESH_BYPASS-1"}
        n = 0
        for iface, s in names.items():
            for p in (FIX / iface).glob("*.json"):
                d = json.loads(p.read_text())
                if "response" in d:
                    jsonschema.validate(d["response"], schema(s + ".schema.json"))
                else:
                    jsonschema.validate(d["error"], schema("PK_MESH_ERROR-1.schema.json"))
                n += 1
        self.assertGreaterEqual(n, 16)
        jsonschema.validate(json.loads((FIX / "config/secure_defaults.json").read_text()), schema("PK_MESH_CONFIG-1.schema.json"))

    def test_fixtures_have_not_drifted(self):
        r = subprocess.run([sys.executable, "-B", str(PKG_DIR / "tools" / "gen_fixtures.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_live_outputs_conform(self):
        svc, clock, _ = make_service()
        svc.migrate_route(CTRL_A, "alpha", "a->b", 3, 3, fence=1, idempotency_key="conf-00001")
        jsonschema.validate(svc.status(operator(clock)), schema("PK_MESH_STATUS-1.schema.json"))
        for e in svc.explain(CTRL_A, "alpha"):
            jsonschema.validate(e, schema("PK_MESH_DECISION-1.schema.json"))
        for r in svc.audit.records():
            jsonschema.validate(r, schema("PK_MESH_AUDIT-1.schema.json"))
        jsonschema.validate(svc.snapshot(), schema("PK_MESH_SNAPSHOT-1.schema.json"))
        for c in errors.ERROR_CODES:
            jsonschema.validate(errors.MeshError(c, "m", {"k": "v"}).to_envelope(), schema("PK_MESH_ERROR-1.schema.json"))


class FuzzTest(unittest.TestCase):
    ALPH = string.printable + "\x00\x7fé‮/%.:@?#"

    def _s(self, rng, n=40):
        return "".join(rng.choice(self.ALPH) for _ in range(rng.randint(0, n)))

    def test_map_identity_never_crashes_and_output_is_canonical(self):
        rng = random.Random(1)
        prefixes = ["spiffe://estate.local/", "spiffe://estate.local/ns/", "spiffe://", "SPIFFE://estate.local/", ""]
        for _ in range(FUZZ_N):
            san = rng.choice(prefixes) + self._s(rng)
            try:
                out = mesh.map_identity(san, "estate.local")
            except mesh.Unmappable:
                continue
            self.assertTrue(out.startswith("runtime:"))
            path = out[len("runtime:"):]
            self.assertNotIn("..", path.split("/"))
            self.assertNotIn("", path.split("/"))
            self.assertEqual(san, "spiffe://estate.local/" + path)  # bijective: no normalisation happened

    def test_reconcile_invariants_hold_for_all_inputs(self):
        rng = random.Random(2)
        for _ in range(FUZZ_N):
            vals = [rng.choice([rng.randint(-3, 20), 0, True, 1.5, "3", None]) for _ in range(3)]
            try:
                r = mesh.reconcile("r", *vals)
            except ValueError:
                continue
            self.assertLessEqual(r["effective_attempts"], r["budget"])
            self.assertFalse(r["app"] > 1 and r["mesh"] > 1)

    def test_config_validator_never_crashes(self):
        rng = random.Random(3)
        keys = list(config.SECURE_DEFAULTS)
        junk = [None, -1, 0, 10**12, "x", [], {}, True, 1.5, ["a"], {"a": 1}, "secretref://kms/x", "fail_open"]
        for _ in range(1500):
            over = {rng.choice(keys): rng.choice(junk) for _ in range(rng.randint(1, 4))}
            try:
                config.validate(config.compose(over))
            except config.ConfigError:
                pass

    def test_boundary_service_never_leaks_non_mesh_errors(self):
        svc, clock, _ = make_service()
        rng = random.Random(4)
        for i in range(1500):
            cred = rng.choice([CTRL_A, NODE, None, {}, {"san": self._s(rng)}, {"token": self._s(rng)}, {"san": 1, "token": 2}])
            tenant = rng.choice(["alpha", "beta", "", None, self._s(rng, 8)])
            try:
                svc.reconcile(cred, tenant, self._s(rng, 20) or "r", rng.randint(-1, 5), rng.randint(-1, 5))
                svc.report_flow(cred, tenant, self._s(rng, 10) or "s", rng.choice(["payments", self._s(rng, 5)]), rng.choice([True, False, 0]))
            except errors.MeshError:
                pass
        self.assertEqual(svc._admission._inflight, 0)


if __name__ == "__main__":
    unittest.main()
