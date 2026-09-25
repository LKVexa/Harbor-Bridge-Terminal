"""Public contract/schema conformance (item 48) and CRD/manifest artifacts (items 10, 17)."""
import json
import subprocess
import sys
import unittest

import _support as S

V = S.mod("schema")
SCH = S.PKG_DIR / "schemas"


def load(name):
    return json.loads((SCH / name).read_text())


class Schemas(unittest.TestCase):
    def test_every_schema_is_2020_12_with_id_and_only_supported_keywords(self):
        for p in sorted(SCH.glob("*.json")):
            doc = json.loads(p.read_text())
            self.assertEqual(doc["$schema"], "https://json-schema.org/draft/2020-12/schema")
            V.errors(doc, {} if doc.get("type") == "object" else "Unknown")  # raises on unsupported keyword

    def test_translation_output_conforms(self):
        out = S.translator.translate({"metadata": {"name": "a", "labels": {"x": "y"}}, "spec": {"containers": [
            {"name": "c", "image": "i", "resources": {"requests": {"cpu": "1"}, "limits": {"memory": "1Gi"}}}]}})
        self.assertEqual(V.errors(load("PK_K8S_TRANSLATE_v1.schema.json"), out), [])

    def test_refusal_conforms_and_bad_refusal_does_not(self):
        try:
            S.translator.translate({"metadata": {"name": "a"}, "spec": {"containers": [{"name": "c", "image": "i", "env": []}]}})
        except S.translator.TranslationError as e:
            doc = e.to_dict()
        schema = load("PK_K8S_REFUSE_v1.schema.json")
        self.assertEqual(V.errors(schema, doc), [])
        self.assertTrue(V.errors(schema, dict(doc, code="WHATEVER")))
        self.assertTrue(V.errors(schema, dict(doc, extra=1)))

    def test_place_envelope_and_conditions_from_live_run_conform(self):
        h = S.Harness()
        sent = []
        orig = h.rt.place
        h.rt.place = lambda env: (sent.append(env), orig(env))[1]
        h.kube.apply(S.workload())
        h.settle(3)
        self.assertEqual(len(sent), 1)
        self.assertEqual(V.errors(load("PK_K8S_PLACE_v1.schema.json"), sent[0]), [])
        self.assertEqual(V.errors(load("PK_K8S_TRANSLATE_v1.schema.json"), sent[0]["request"]), [])
        cs = load("INV67_CONDITION_v1.schema.json")
        conds = h.obj()["status"]["conditions"]
        self.assertTrue(conds)
        for c in conds:
            self.assertEqual(V.errors(cs, c), [], c)

    def test_validator_negative_cases(self):
        s = {"type": "object", "required": ["a"], "additionalProperties": False,
             "properties": {"a": {"type": "integer", "minimum": 0}}}
        self.assertTrue(V.errors(s, {}))
        self.assertTrue(V.errors(s, {"a": -1}))
        self.assertTrue(V.errors(s, {"a": True}))
        self.assertTrue(V.errors(s, {"a": 1, "b": 2}))
        with self.assertRaises(ValueError):
            V.errors({"frobnicate": 1}, 1)


class Manifests(unittest.TestCase):
    def test_on_disk_manifests_match_generator(self):
        r = subprocess.run([sys.executable, "-m", S.PKG_DIR.name + ".plane.manifests"], cwd=str(S.ROOT),
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_crd_shape(self):
        crd = S.mod("manifests").crd()
        v = crd["spec"]["versions"]
        self.assertEqual(sum(x["storage"] for x in v), 1)
        self.assertIn("status", v[0]["subresources"])
        spec = v[0]["schema"]["openAPIV3Schema"]["properties"]["spec"]
        tmpl_spec = spec["properties"]["template"]["properties"]["spec"]
        # unknown pod fields must reach the controller to be refused by path, not pruned silently
        self.assertTrue(tmpl_spec["x-kubernetes-preserve-unknown-fields"])
        self.assertEqual(crd["spec"]["group"], S.kube.GROUP)

    def test_deployment_hardening(self):
        d = S.mod("manifests").deployment()
        c = d["spec"]["template"]["spec"]["containers"][0]
        self.assertFalse(c["securityContext"]["allowPrivilegeEscalation"])
        self.assertTrue(c["securityContext"]["readOnlyRootFilesystem"])
        self.assertEqual(c["securityContext"]["capabilities"]["drop"], ["ALL"])
        self.assertIn("@sha256:", c["image"])
        self.assertEqual(d["spec"]["strategy"]["rollingUpdate"]["maxUnavailable"], 0)

    def test_yaml_parses_when_pyyaml_available(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML not installed (dev-only dependency)")
        M = S.mod("manifests")
        for rel, text in M.files().items():
            docs = list(yaml.safe_load_all(text))
            self.assertTrue(docs and all(isinstance(d, dict) for d in docs), rel)
        self.assertEqual(yaml.safe_load(M.files()["api/crds/wasmworkloads.inv67.linearfinance.org.yaml"]), M.crd())
        self.assertEqual(list(yaml.safe_load_all(M.files()["deploy/base/rbac.yaml"])), M.rbac())


if __name__ == "__main__":
    unittest.main()
