"""Dependency-free unit tests for the INV-03 admission policy."""
import importlib.util
import pathlib
import unittest

POLICY_PATH = pathlib.Path(__file__).resolve().parents[1] / "policy.py"
spec = importlib.util.spec_from_file_location("inv03_policy_under_test", POLICY_PATH)
policy = importlib.util.module_from_spec(spec)
if spec.loader is None:
    raise RuntimeError("unable to load policy module")
spec.loader.exec_module(policy)


def hardened_spec():
    return {
        "user": "10001",
        "readOnlyRootFilesystem": True,
        "privileged": False,
        "capabilities": {"drop": ["ALL"], "add": []},
        "seccomp": "RuntimeDefault",
    }


class PolicyTest(unittest.TestCase):
    def test_hardened_spec_admitted(self):
        result = policy.evaluate("api", hardened_spec(), {}, 100)
        self.assertTrue(result["admit"], result)
        self.assertEqual(result["failed"], [])
        self.assertEqual(result["input_errors"], [])

    def test_omitted_privileged_field_fails_closed(self):
        workload = hardened_spec()
        workload.pop("privileged")
        result = policy.evaluate("api", workload, {}, 100)
        self.assertFalse(result["admit"])
        self.assertIn("not-privileged", result["failed"])

    def test_non_boolean_privileged_field_fails_closed(self):
        workload = hardened_spec()
        workload["privileged"] = 0
        self.assertFalse(policy.evaluate("api", workload, {}, 100)["admit"])

    def test_malformed_capabilities_fail_without_crash(self):
        for value in (None, "ALL", {"drop": "ALL"}, {"drop": ["ALL"], "add": ""}):
            workload = hardened_spec()
            workload["capabilities"] = value
            result = policy.evaluate("api", workload, {}, 100)
            self.assertFalse(result["admit"], (value, result))
            self.assertIn("drop-all-capabilities", result["failed"])

    def test_root_uid_spellings_refused(self):
        for value in (0, "0", "00", "root", " ROOT ", ""):
            workload = hardened_spec()
            workload["user"] = value
            self.assertFalse(policy.evaluate("api", workload, {}, 100)["admit"], value)

    def test_exception_legacy_and_json_safe_forms(self):
        workload = hardened_spec()
        workload["readOnlyRootFilesystem"] = False
        record = {"reason": "approved OPS-12", "expires": 200}
        forms = [
            {("cache", "read-only-root"): record},
            {"cache": {"read-only-root": record}},
            {"cache/read-only-root": record},
            [{"workload": "cache", "control": "read-only-root", **record}],
        ]
        for exc in forms:
            self.assertTrue(policy.evaluate("cache", workload, exc, 150)["admit"], exc)

    def test_bad_exception_expiry_or_reason_is_refused(self):
        workload = hardened_spec()
        workload["readOnlyRootFilesystem"] = False
        bad_records = [
            {"reason": "x", "expires": 100},
            {"reason": "x", "expires": True},
            {"reason": "   ", "expires": 200},
            {"expires": 200},
            {"reason": "x", "expires": 200, "revoked": True},
            {"reason": "x", "expires": 200, "revoked": "true"},
        ]
        for record in bad_records:
            result = policy.evaluate("cache", workload, {("cache", "read-only-root"): record}, 100)
            self.assertFalse(result["admit"], record)

    def test_malformed_top_level_inputs_do_not_throw(self):
        result = policy.evaluate(None, None, None, True)
        self.assertFalse(result["admit"])
        self.assertIn("invalid-workload", result["input_errors"])
        self.assertIn("invalid-spec", result["input_errors"])
        self.assertIn("invalid-exceptions", result["input_errors"])
        self.assertIn("invalid-time", result["input_errors"])

    def test_control_registry_is_immutable(self):
        with self.assertRaises(TypeError):
            policy.CONTROLS["bypass"] = lambda _: True

    def test_baseline_is_json_serializable_shape(self):
        baseline = policy.get_baseline()
        self.assertEqual(baseline["version"], "4.2.0")
        self.assertEqual(baseline["controls"], list(policy.CONTROLS))
        self.assertEqual(baseline["schema"], "PK_HARDEN_BASELINE/1")


if __name__ == "__main__":
    unittest.main()
