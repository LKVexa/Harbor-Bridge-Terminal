"""INV-57 - Durable execution conformance-framework adapter.

The executable replay semantics live in :mod:`.durable` and are deliberately
stdlib-only.  This adapter binds those semantics into the external ``pk_core``
100-item checklist when that framework is available.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .durable import Crash, NonDeterminism, Worker


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class DurableExecutionComponent(Component):
    """Framework adapter for INV-57."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        charges = []
        crash_once = {"armed": True}

        def order(w):
            w.activity("reserve", lambda: "r-1")
            w.activity("charge", lambda: charges.append(1) or "c-1")
            if crash_once["armed"]:
                crash_once["armed"] = False
                raise Crash()
            return w.activity("ship", lambda: "s-1")

        w = Worker()
        try:
            w.run(order)
        except Crash:
            pass
        else:
            raise AssertionError("crash injection did not interrupt the first workflow run")

        result = w.run(order)
        _verify(
            result == "s-1"
            and len(charges) == 1
            and w.executed == ["reserve", "charge", "ship"],
            "completed activities were not replayed exactly once after restart",
        )

        # C057: crash/restart/resume/replay semantics.
        findings[6] = self.satisfied(
            items[6],
            "A workflow that crashes after charging resumes from its append-only history: completed "
            "activities replay from recorded outcomes and only the unfinished next activity executes.",
            *self._evidence("durable.py::Worker.run"),
        )
        # C058: duplicate execution / duplicate ownership protection, at reference-engine scope.
        findings[7] = self.satisfied(
            items[7],
            "Completed activity effects are not executed again during replay, and a started activity "
            "without a durable outcome is stopped as ActivityInDoubt rather than retried blindly.",
            *self._evidence("durable.py::Worker.activity"),
        )
        return findings

    def assess_testing(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_testing(items)
        w = Worker()
        w.run(lambda worker: [worker.activity("a", lambda: 1), worker.activity("b", lambda: 2)])
        try:
            w.run(lambda worker: [worker.activity("a", lambda: 1), worker.activity("c", lambda: 3)])
        except NonDeterminism:
            pass
        else:
            raise AssertionError("replay divergence was not rejected")

        _verify(w.executed == ["a", "b"], "divergent replay executed new activity code")
        findings[0] = self.satisfied(
            items[0],
            "Stdlib unit tests exercise replay, crash ambiguity, divergence, tamper detection, history "
            "bounds, legacy migration, failure replay, and same-worker concurrency refusal.",
            *self._evidence("tests/test_durable.py"),
        )
        return findings


COMPONENT = DurableExecutionComponent
