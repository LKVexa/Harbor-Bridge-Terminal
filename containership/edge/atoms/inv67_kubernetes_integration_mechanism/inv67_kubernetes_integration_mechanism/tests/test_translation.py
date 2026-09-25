"""Standalone unit/security tests for the INV-67 pure translation boundary."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("inv67_translator", PKG_DIR / "translator.py")
translator = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = translator
SPEC.loader.exec_module(translator)


class TranslationTests(unittest.TestCase):
    def pod(self):
        return {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "web",
                "namespace": "edge-a",
                "labels": {"app": "web"},
                "annotations": {"trace": "abc"},
            },
            "spec": {
                "containers": [{
                    "name": "c",
                    "image": "registry/web:1",
                    "resources": {
                        "requests": {"cpu": "250m", "memory": "512Mi"},
                        "limits": {"cpu": "1500m", "memory": "1Gi"},
                    },
                }]
            },
        }

    def test_quantity_matrix(self):
        cases = {
            "250m": 0.25,
            "1500m": 1.5,
            "500M": 500_000_000,
            "1Gi": 1024**3,
            "1.5Gi": 1.5 * 1024**3,
            "2k": 2000,
            "100u": 0.0001,
            "1e3": 1000,
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(translator.quantity(raw), expected)

    def test_quantity_rejects_invalid_or_dangerous_values(self):
        for raw in ("", "-1", "NaN", "inf", "1 Gi", "1KB", "1e999", "1e3Mi", "9223372036854775808"):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    translator.quantity(raw)

    def test_translation_preserves_supported_semantics(self):
        result = translator.translate(self.pod())
        self.assertEqual(result["schema"], "PK_K8S_TRANSLATE/1")
        self.assertEqual(result["namespace"], "edge-a")
        self.assertEqual(result["labels"], {"app": "web"})
        self.assertEqual(result["annotations"], {"trace": "abc"})
        unit = result["units"][0]
        self.assertEqual(unit["requests"], {"cpu": 0.25, "memory": 512 * 1024**2})
        self.assertEqual(unit["limits"], {"cpu": 1.5, "memory": 1024**3})
        self.assertEqual(unit["cpu"], 0.25)
        self.assertEqual(unit["memory"], 512 * 1024**2)

    def test_input_is_not_mutated(self):
        pod = self.pod()
        snapshot = repr(pod)
        translator.translate(pod)
        self.assertEqual(repr(pod), snapshot)

    def test_unknown_container_field_is_refused_not_dropped(self):
        pod = self.pod()
        pod["spec"]["containers"][0]["env"] = [{"name": "TOKEN", "value": "x"}]
        with self.assertRaises(translator.Unsupported) as ctx:
            translator.translate(pod)
        detail = ctx.exception.to_dict()
        self.assertEqual(detail["code"], "PK_K8S_UNSUPPORTED_FIELD")
        self.assertIn("spec.containers[0].env", {d["field"] for d in detail["details"]})

    def test_security_refusal_reports_all_fields(self):
        pod = self.pod()
        pod["spec"]["hostNetwork"] = True
        pod["spec"]["hostPID"] = True
        pod["spec"]["volumes"] = [{"name": "h", "hostPath": {"path": "/"}}]
        pod["spec"]["containers"][0]["securityContext"] = {"privileged": True}
        with self.assertRaises(translator.Unsupported) as ctx:
            translator.translate(pod)
        fields = {d.field for d in ctx.exception.details}
        self.assertEqual(
            fields,
            {
                "spec.hostNetwork",
                "spec.hostPID",
                "spec.volumes[0].hostPath",
                "spec.containers[0].securityContext.privileged",
            },
        )

    def test_init_containers_are_explicitly_refused(self):
        pod = self.pod()
        pod["spec"]["initContainers"] = [{"name": "setup", "image": "busybox"}]
        with self.assertRaises(translator.Unsupported) as ctx:
            translator.translate(pod)
        self.assertIn("spec.initContainers", {d.field for d in ctx.exception.details})

    def test_duplicate_container_name_is_invalid(self):
        pod = self.pod()
        pod["spec"]["containers"].append(dict(pod["spec"]["containers"][0]))
        with self.assertRaises(translator.InvalidPod):
            translator.translate(pod)

    def test_invalid_shape_fails_closed(self):
        with self.assertRaises(translator.InvalidPod):
            translator.translate({"metadata": {"name": "x"}, "spec": {"containers": []}})
        with self.assertRaises(translator.InvalidPod):
            translator.translate({"metadata": {"name": "x"}, "spec": {"containers": "oops"}})


    def test_version_files_are_consistent(self):
        version = (PKG_DIR / "VERSION").read_text().strip()
        init_text = (PKG_DIR / "__init__.py").read_text()
        readme = (PKG_DIR / "README.md").read_text()
        self.assertEqual(version, "4.3.0")
        self.assertRegex(init_text, r'__version__\s*=\s*["\']4\.3\.0["\']')
        self.assertIn("**Version:** 4.3.0", readme)

    def test_machine_readable_contract_files_parse(self):
        for path in sorted((PKG_DIR / "schemas").glob("*.json")):
            with self.subTest(path=path.name):
                doc = json.loads(path.read_text())
                self.assertEqual(doc.get("$schema"), "https://json-schema.org/draft/2020-12/schema")
                self.assertTrue(doc.get("$id"))

    def test_status_projection(self):
        self.assertEqual(translator.project_status("pending"), "Pending")
        self.assertEqual(translator.project_status("weird"), "Unknown")
        with self.assertRaises(TypeError):
            translator.project_status(None)


if __name__ == "__main__":
    unittest.main()
