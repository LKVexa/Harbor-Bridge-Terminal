"""INV-69 - Agentic workload layer.

The agentic workload layer runs model-driven agents that plan and call tools. What makes that safe to operate is containment at the plan level: each agent has an allowlist of tools, a step budget, and any tool with side effects waits for a recorded approval before it runs. Every step lands in a transcript, so what an agent did is always reconstructable.

The component answers all 100 requirements of the INV-69 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build

def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``.

    Bare ``assert`` statements are stripped by the optimiser, which silently turned
    exercised checks into declared-only ones (and, where an assert carried a side
    effect, broke the element outright).  Every check goes through here instead.
    """
    if not condition:
        raise AssertionError(message)



from .runtime import Agent, TOOLS


class AgenticWorkloadLayerComponent(Component):
    """Master-applied component for INV-69."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        a = Agent("support-bot", frozenset({"search_docs", "send_email", "run_python"}))
        injected = a.step("delete_records", "all")
        held = a.step("send_email", "customer-9")
        a.approve("send_email", "customer-9", "alice")
        sent = a.step("send_email", "customer-9")
        code = a.step("run_python", "print(1)")
        _verify(injected["outcome"] == "refused" and held["outcome"] == "pending", "check failed: injected['outcome'] == 'refused' and held['outcome'] == 'pending'")
        _verify(sent["outcome"] == "ran" and code["sandbox"] == "heavy", "check failed: sent['outcome'] == 'ran' and code['sandbox'] == 'heavy'")
        findings[0] = self.satisfied(
            items[0],
            "An injected call to a tool outside the allowlist is refused; a side-effectful email is held "
            "until an approval is recorded (by alice) and only then runs; arbitrary code is routed to the "
            "heavy sandbox tier because of its risk class.",
            *self._evidence("runtime.py::Agent.step", "runtime.py::TOOLS"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        a = Agent("looper", frozenset({"search_docs"}), max_steps=5)
        outcomes = [a.step("search_docs", i)["outcome"] for i in range(8)]
        _verify(outcomes.count("ran") == 5 and outcomes[5:] == ["refused"] * 3, "check failed: outcomes.count('ran') == 5 and outcomes[5:] == ['refused'] * 3")
        findings[0] = self.satisfied(
            items[0],
            "A looping agent is stopped at its step budget: five steps run and every further step is "
            "refused and recorded, so a runaway plan cannot consume unbounded resources.",
            *self._evidence("runtime.py::Agent.step"))
        return findings

    def assess_observability(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_observability(items)
        a = Agent("x", frozenset({"send_email"}))
        a.step("send_email", 1)
        a.approve("send_email", 1, "bob")
        a.step("send_email", 1)
        a.step("nope", 0)
        kinds = [s["outcome"] for s in a.transcript]
        _verify(kinds == ["pending", "approved", "ran", "refused"], "check failed: kinds == ['pending', 'approved', 'ran', 'refused']")
        _verify([s["step"] for s in a.transcript] == [0, 1, 2, 3], "check failed: [s['step'] for s in a.transcript] == [0, 1, 2, 3]")
        findings[0] = self.satisfied(
            items[0],
            "The transcript records every step in order -- pending, approval with its approver, the run, "
            "and the refusal -- so what an agent did is reconstructable without trusting the agent.",
            *self._evidence("runtime.py::Agent.transcript"))
        return findings

COMPONENT = AgenticWorkloadLayerComponent
