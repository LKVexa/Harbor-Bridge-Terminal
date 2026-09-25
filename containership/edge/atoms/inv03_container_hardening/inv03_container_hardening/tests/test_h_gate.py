"""Item 54 falsifier: the gate must refuse completions that carry no human approval."""
import importlib.util
import os
import unittest

import hkit  # noqa: F401  (path setup)

spec = importlib.util.spec_from_file_location(
    "gate", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "release_gate.py"))
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class Gate(unittest.TestCase):
    def test_forged_completion_refused(self):
        self.assertFalse(gate.approved({"complete": True}))
        for who in ("claude", "Claude Opus", "release_gate", "github-actions[bot]", "ci-runner"):
            self.assertFalse(gate.approved({"complete": True, "approval": {"approver": who, "kind": "human"}}), who)
        self.assertFalse(gate.approved({"complete": True, "approval": {"approver": "j.doe", "kind": "service"}}))

    def test_human_approval_accepted(self):
        # a synthetic approver proves the gate is a gate, not a wall; no such record ships
        self.assertTrue(gate.approved({"complete": True, "approval": {"approver": "NOT_A_REAL_PERSON", "kind": "human"}}))


if __name__ == "__main__":
    unittest.main()
