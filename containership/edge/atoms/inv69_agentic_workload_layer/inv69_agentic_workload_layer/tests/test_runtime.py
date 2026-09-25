"""Standalone safety-kernel tests for INV-69.

These tests intentionally do not require pk_core or network access.
"""
from concurrent.futures import ThreadPoolExecutor
import importlib
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pkg = importlib.import_module(PKG_DIR.name)
Agent = pkg.Agent


class RuntimeSafetyTest(unittest.TestCase):
    def test_package_import_and_version_without_pk_core(self):
        self.assertEqual(pkg.__version__, "4.3.0")

    def test_unknown_tool_cannot_enter_allowlist(self):
        with self.assertRaises(ValueError):
            Agent("a", frozenset({"search_docs", "unknown"}))

    def test_unhashable_arguments_can_be_approved_and_approval_is_one_use(self):
        a = Agent("a", frozenset({"send_email"}))
        payload = {"to": "x@example.invalid", "body": ["hello"]}
        self.assertEqual(a.step("send_email", payload)["outcome"], "pending")
        a.approve("send_email", payload, "reviewer")
        self.assertEqual(a.step("send_email", payload)["outcome"], "ran")
        self.assertEqual(a.step("send_email", payload)["outcome"], "pending")

    def test_approval_is_bound_to_exact_arguments(self):
        a = Agent("a", frozenset({"send_email"}))
        a.approve("send_email", {"to": "a"}, "reviewer")
        self.assertEqual(a.step("send_email", {"to": "b"})["outcome"], "pending")

    def test_self_or_irrelevant_approval_is_rejected(self):
        a = Agent("a", frozenset({"send_email", "search_docs"}))
        with self.assertRaises(PermissionError):
            a.approve("send_email", 1, "a")
        with self.assertRaises(ValueError):
            a.approve("search_docs", 1, "reviewer")
        with self.assertRaises(PermissionError):
            Agent("b", frozenset({"search_docs"})).approve("send_email", 1, "reviewer")

    def test_step_budget_counts_refused_attempts(self):
        a = Agent("a", frozenset({"search_docs"}), max_steps=2)
        self.assertEqual(a.step("not_allowed", 1)["outcome"], "refused")
        self.assertEqual(a.step("search_docs", 2)["outcome"], "ran")
        third = a.step("search_docs", 3)
        self.assertEqual(third["outcome"], "refused")
        self.assertEqual(third["reason"], "step budget exhausted")

    def test_cost_budget_is_enforced(self):
        a = Agent("a", frozenset({"run_python"}), max_steps=3, max_cost=10)
        self.assertEqual(a.step("run_python", "1+1")["outcome"], "ran")
        second = a.step("run_python", "2+2")
        self.assertEqual(second["outcome"], "refused")
        self.assertEqual(second["reason"], "cost budget exhausted")
        self.assertEqual(a.cost_used, 10)

    def test_transcript_does_not_store_raw_secret_values_and_chain_verifies(self):
        a = Agent("a", frozenset({"send_email"}))
        secret = "super-secret-value"
        a.step("send_email", {"authorization": secret, "body": secret})
        serialized = repr(a.transcript)
        self.assertNotIn(secret, serialized)
        self.assertTrue(a.verify_transcript())
        a.transcript[0]["reason"] = "tampered"
        self.assertFalse(a.verify_transcript())

    def test_nonfinite_and_cyclic_arguments_do_not_crash_policy(self):
        a = Agent("a", frozenset({"search_docs"}))
        cyclic = []
        cyclic.append(cyclic)
        self.assertEqual(a.step("search_docs", float("nan"))["outcome"], "ran")
        self.assertEqual(a.step("search_docs", cyclic)["outcome"], "ran")

    def test_transcript_export_is_versioned(self):
        a = Agent("a", frozenset({"search_docs"}))
        a.step("search_docs", {"q": "x"})
        exported = a.export_transcript()
        self.assertEqual(exported["schema"], "PK_AGENT_TRANSCRIPT/1")
        self.assertEqual(exported["agent"], "a")
        self.assertEqual(exported["head"], a.transcript_head)
        self.assertEqual(exported["events"][0]["schema"], "PK_AGENT_STEP/1")

    def test_high_risk_tool_routes_to_heavy_sandbox(self):
        a = Agent("a", frozenset({"run_python"}))
        self.assertEqual(a.step("run_python", "print(1)")["sandbox"], "heavy")

    def test_concurrent_callers_cannot_execute_past_step_budget(self):
        a = Agent("a", frozenset({"search_docs"}), max_steps=12, max_transcript_events=64)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda i: a.step("search_docs", i), range(40)))
        self.assertEqual(sum(r["outcome"] == "ran" for r in results), 12)
        self.assertEqual(a.attempts, 12)
        self.assertTrue(a.verify_transcript())

    def test_invalid_tool_type_fails_closed_without_crashing(self):
        a = Agent("a", frozenset({"search_docs"}))
        result = a.step(["search_docs"], 1)
        self.assertEqual(result["outcome"], "refused")
        self.assertIn("not in allowlist", result["reason"])
        self.assertTrue(a.verify_transcript())

    def test_failed_approval_recording_does_not_leave_live_approval(self):
        a = Agent("a", frozenset({"send_email"}), max_steps=10, max_transcript_events=2)
        a.step("send_email", 1)
        a.step("send_email", 2)
        with self.assertRaises(RuntimeError):
            a.approve("send_email", 1, "reviewer")
        self.assertEqual(a.approvals, set())

    def test_audit_capacity_exhaustion_fails_closed(self):
        a = Agent("a", frozenset({"search_docs"}), max_steps=20, max_transcript_events=2)
        self.assertEqual(a.step("search_docs", 1)["outcome"], "ran")
        self.assertEqual(a.step("search_docs", 2)["outcome"], "ran")
        third = a.step("search_docs", 3)
        self.assertEqual(third["outcome"], "refused")
        self.assertFalse(third["recorded"])


if __name__ == "__main__":
    unittest.main()
