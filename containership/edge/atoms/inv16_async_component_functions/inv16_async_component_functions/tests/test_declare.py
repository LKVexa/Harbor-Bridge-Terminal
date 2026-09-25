"""Closure #3 (INV-16 side): interface -> PK_ASYNC_DECL/1 -> runtime; golden, negative, drift, evolution."""
import json
import unittest

from _util import PKG_DIR, rt, sub

d = sub("declare")
IFACES = PKG_DIR / "fixtures" / "interfaces"
GOLDEN = PKG_DIR / "fixtures" / "golden_demo_descriptor.json"


class Declarations(unittest.TestCase):
    def setUp(self):
        self.desc = d.parse_interface((IFACES / "demo.pkif").read_text(), "fixtures/interfaces/demo.pkif")

    def test_golden_bytes_and_hash(self):
        golden = json.loads(GOLDEN.read_text())
        self.assertEqual(d.canonical_bytes(self.desc).decode(), golden["canonical"])
        self.assertEqual(d.digest(self.desc), golden["digest"])

    def test_deterministic_rebuild(self):
        again = d.parse_interface((IFACES / "demo.pkif").read_text(), "elsewhere.pkif")
        self.assertEqual(d.digest(again), d.digest(self.desc))   # source path is not semantic

    def test_namespaced_identity_no_collision(self):
        fns = self.desc["functions"]
        self.assertIn("pk:demo/api#now", fns)
        self.assertIn("pk:demo/admin#now", fns)
        self.assertEqual(fns["pk:demo/api#now"]["line"], 6)

    def test_negative(self):
        cases = {
            "dup": (IFACES / "bad_duplicate.pkif").read_text(),
            "nopkg": "interface a {\n func x;\n}\n",
            "badver": "package pk:x@1;\ninterface a {\n func x;\n}\n",
            "unterminated": "package pk:x@1.0.0;\ninterface a {\n func x;\n",
            "malformed": "package pk:x@1.0.0;\ninterface a {\n asynk func x;\n}\n",
            "empty": "package pk:x@1.0.0;\n",
            "dupiface": "package pk:x@1.0.0;\ninterface a {\nfunc x;\n}\ninterface a {\nfunc y;\n}\n",
        }
        for name, text in cases.items():
            with self.subTest(name), self.assertRaises(d.DeclarationError):
                d.parse_interface(text)
        with self.assertRaises(d.DeclarationError):
            d.verify_descriptor({**self.desc, "schema": "PK_ASYNC_DECL/2"})
        with self.assertRaises(d.DeclarationError):
            d.verify_descriptor({**self.desc, "functions": {"x#y": {"async": "yes"}}})

    def test_end_to_end_and_drift(self):
        dig = d.digest(self.desc)
        f = rt.AsyncFunctions.from_descriptor("i", self.desc, expected_digest=dig)
        self.assertTrue(f.is_async("pk:demo/api#fetch"))
        self.assertFalse(f.is_async("pk:demo/api#now"))
        c = f.invoke("pk:demo/api#fetch")
        self.assertEqual(f.complete(c.call_id, 1), 1)
        with self.assertRaises(TypeError):
            f.declared["pk:demo/api#now"] = True           # runtime mutation still impossible
        tampered = json.loads(json.dumps(self.desc))
        tampered["functions"]["pk:demo/api#now"]["async"] = True
        with self.assertRaises(d.DeclarationError):
            rt.AsyncFunctions.from_descriptor("i", tampered, expected_digest=dig)

    def test_evolution_classification(self):
        new_text = (IFACES / "demo.pkif").read_text().replace("    func now;\n    async func stream-body;",
                                                             "    async func now;\n    async func extra;")
        new = d.parse_interface(new_text)
        diff = d.compare(self.desc, new)
        self.assertEqual(diff["sync_to_async"], ["pk:demo/api#now"])
        self.assertEqual(diff["removed"], ["pk:demo/api#stream-body"])
        self.assertEqual(diff["added"], ["pk:demo/api#extra"])
        self.assertEqual(set(diff["breaking"]), {"pk:demo/api#now", "pk:demo/api#stream-body"})


if __name__ == "__main__":
    unittest.main()
