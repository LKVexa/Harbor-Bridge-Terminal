"""Schema/contract, compatibility, fixtures and fuzz tests (C016, C021, C022, C027-C029, C082, C084, C085)."""
import json
import pathlib
import random
import unittest

from _support import PKG_DIR, covers, make_env, mod, req

schema = mod("schema")
errors = mod("errors")
FIX = PKG_DIR / "fixtures"


class SchemaTest(unittest.TestCase):
    @covers(22, 82)
    def test_every_contract_has_a_versioned_schema(self):
        for name, majors in schema.SUPPORTED.items():
            for m in majors:
                s = schema.load(name, m)
                self.assertEqual(s["$id"], f"urn:inv63:{name}/{m}")
                self.assertEqual(s["properties"]["schema"]["const"], f"{name}/{m}")
                self.assertFalse(s.get("additionalProperties", True))

    @covers(29, 82, 22)
    def test_conformance_fixtures(self):
        manifest = json.loads((FIX / "FIXTURES.json").read_text())
        self.assertEqual(manifest["schema_digests"], schema.all_schema_digests(),
                         "fixture manifest is stale: regenerate with tools/gen_fixtures.py")
        for f in manifest["fixtures"]:
            payload = json.loads((FIX / f["file"]).read_text())
            if f["expect"] == "valid":
                schema.validate(payload, f["schema"])
            else:
                with self.assertRaises(errors.DeploymentError, msg=f["file"]) as cm:
                    schema.validate(payload, f["schema"])
                self.assertEqual(cm.exception.code.value, f["expect_code"], f["file"])

    @covers(28, 82)
    def test_documented_limits_are_enforced(self):
        doc = (PKG_DIR / "docs/interfaces/LIMITS.md").read_text()
        self.assertIn(str(schema.MAX_PAYLOAD_BYTES), doc)
        self.assertIn(str(schema.MAX_DEPTH), doc)
        diff = {"schema": "PK_DEPLOY_DIFF/1", "start": [["a", "v", "h"]] * 2001, "stop": []}
        with self.assertRaises(errors.DeploymentError):
            schema.validate(diff, "PK_DEPLOY_DIFF/1")

    @covers(26, 82)
    def test_error_catalog_complete(self):
        doc = (PKG_DIR / "docs/interfaces/ERROR_CODES.md").read_text()
        for code in errors.ErrorCode:
            self.assertIn(code.value, doc)
            e = errors.DeploymentError(code, "m", {"a": 1})
            schema.validate(e.to_dict(), "PK_DEPLOY_ERROR/1")

    @covers(21, 82)
    def test_boundary_inventory_matches_code(self):
        inv = json.loads((PKG_DIR / "docs/interfaces/BOUNDARIES.json").read_text())
        ids = {b["contract"] for b in inv["boundaries"] if b.get("contract")}
        for name, majors in schema.SUPPORTED.items():
            for m in majors:
                self.assertIn(f"{name}/{m}", ids)
        ops = set(schema.load("PK_DEPLOY_REQUEST", 1)["properties"]["op"]["enum"])
        self.assertEqual(ops, set(inv["operations"]))
        for b in inv["boundaries"]:
            for k in ("id", "kind", "direction", "authn", "authz", "timeout", "limits", "owner"):
                self.assertIn(k, b, b.get("id"))


class CompatibilityTest(unittest.TestCase):
    @covers(16, 27, 84)
    def test_version_negotiation(self):
        self.assertEqual(schema.negotiate("PK_DEPLOY_DESIRED", [1, 2, 3]), 2)
        self.assertEqual(schema.negotiate("PK_DEPLOY_DESIRED", [1]), 1)
        with self.assertRaises(errors.DeploymentError) as cm:
            schema.negotiate("PK_DEPLOY_DESIRED", [7])
        self.assertEqual(cm.exception.code, errors.ErrorCode.UNSUPPORTED_VERSION)
        with self.assertRaises(errors.DeploymentError):
            schema.validate({"schema": "PK_DEPLOY_DIFF/9"}, "PK_DEPLOY_DIFF/9")

    @covers(16, 27, 84)
    def test_v1_desired_accepted_when_signing_not_required(self):
        env = make_env(config_over={"environment": "dev", "require_signed_artifacts": False})
        body = {"schema": "PK_DEPLOY_DESIRED/1", "tenant": "acme", "component": "api", "version": "v1", "count": 1}
        self.assertEqual(req(env, "set_desired", body)["outcome"], "SUCCESS")
        r = req(env, "set_desired", body, accept_versions=[9])
        self.assertEqual(r["error"]["code"], "INV63-E-UNSUPPORTED-VERSION")

    @covers(16)
    def test_legacy_manager_api_unchanged(self):
        Manager = mod("manager").Manager
        m = Manager({"h1": "z1", "h2": "z2"})
        d = m.diff("api", "v1", 2)
        self.assertEqual(d, {"start": [("api", "v1", "h1"), ("api", "v1", "h2")], "stop": []})

    @covers(84, 31)
    def test_wadm_manifest_rendering(self):
        adapter = mod("adapter")
        m = adapter.wadm_manifest("acme", "api", "v1", 3, "ghcr.io/x/api:v1", ["z1", "z2"])
        self.assertEqual(m["apiVersion"], "core.oam.dev/v1beta1")
        trait = m["spec"]["components"][0]["traits"][0]
        self.assertEqual((trait["type"], trait["properties"]["instances"]), ("spreadscaler", 3))
        w = adapter.WadmAdapter()
        self.assertFalse(w.ping())
        with self.assertRaises(errors.DeploymentError) as cm:
            w.deploy(m)
        self.assertEqual(cm.exception.code, errors.ErrorCode.DEPENDENCY_UNAVAILABLE)


class FuzzTest(unittest.TestCase):
    @covers(85, 50)
    def test_random_bytes_never_crash_and_always_structured(self):
        env = make_env()
        rng = random.Random(63)
        seeds = [json.dumps({"schema": "PK_DEPLOY_REQUEST/1", "op": "explain", "token": "a.b",
                             "idempotency_key": "abcdefgh", "body": {}}).encode()]
        for i in range(1500):
            base = bytearray(rng.choice(seeds))
            for _ in range(rng.randint(1, 8)):
                op = rng.random()
                pos = rng.randrange(len(base) or 1)
                if op < 0.4 and base:
                    base[pos] = rng.randrange(256)
                elif op < 0.7:
                    base.insert(pos, rng.randrange(256))
                elif base:
                    del base[pos]
            r = env.svc.handle(bytes(base))
            self.assertIn(r["outcome"], ("TERMINAL", "RETRYABLE"))
            schema.validate(r["error"], "PK_DEPLOY_ERROR/1")
            self.assertNotEqual(r["error"]["code"], "INV63-E-INTERNAL", bytes(base))

    @covers(85)
    def test_structured_fuzz_of_desired_schema(self):
        rng = random.Random(1263)
        values = [None, True, 0, -1, 1.5, "", "x" * 300, [], {}, "a\x00b", 10**12, "ok"]
        for _ in range(2000):
            body = {"schema": "PK_DEPLOY_DESIRED/1", "tenant": "acme", "component": "c", "version": "v", "count": 1}
            k = rng.choice(list(body) + ["spread", "junk"])
            body[k] = rng.choice(values)
            try:
                schema.validate(body, "PK_DEPLOY_DESIRED/1")
            except errors.DeploymentError as exc:
                self.assertIn(exc.code, (errors.ErrorCode.SCHEMA_VIOLATION, errors.ErrorCode.UNSUPPORTED_VERSION))


if __name__ == "__main__":
    unittest.main()
