"""INV-03 - Container hardening.

Container hardening is the list of things a container should not be allowed to
do, checked before it runs.  The security-critical policy engine lives in
``policy.py`` so it can be tested without the orchestration framework.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .policy import CONTROLS, evaluate, get_baseline


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class ContainerHardeningComponent(Component):
    """Master-applied component for INV-03."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        hard = {
            "user": "10001",
            "readOnlyRootFilesystem": True,
            "privileged": False,
            "capabilities": {"drop": ["ALL"], "add": []},
            "seccomp": "RuntimeDefault",
        }
        soft = {"privileged": True}

        good = evaluate("api", hard, {}, 100)
        _verify(good["admit"], f"hardened spec unexpectedly refused: {good}")

        bad = evaluate("legacy", soft, {}, 100)
        _verify(
            not bad["admit"] and len(bad["failed"]) == len(CONTROLS),
            f"privileged/incomplete spec did not fail all controls: {bad}",
        )
        findings[0] = self.satisfied(
            items[0],
            f"A complete hardened spec passes all {len(CONTROLS)} controls; a privileged/incomplete "
            f"container is refused with every failed control named ({', '.join(bad['failed'])}).",
            *self._evidence("policy.py::evaluate", "policy.py::CONTROLS"),
        )

        spec = dict(hard, readOnlyRootFilesystem=False)
        exc = {("cache", "read-only-root"): {"reason": "writes spool, ticket OPS-12", "expires": 200}}
        _verify(evaluate("cache", spec, exc, 150)["admit"], "valid exception was not honoured")
        _verify(not evaluate("cache", spec, exc, 201)["admit"], "expired exception was honoured")
        _verify(
            not evaluate("cache", spec, {("cache", "read-only-root"): {"expires": 999}}, 150)["admit"],
            "reason-less exception was honoured",
        )
        _verify(
            not evaluate("cache", spec, {("cache", "read-only-root"): {"reason": "x", "expires": True}}, 0)["admit"],
            "boolean expiry was accepted as an integer timestamp",
        )
        findings[1] = self.satisfied(
            items[1],
            "An exception works only when scoped to the workload/control, carries a non-blank reason, "
            "uses a real integer future expiry, and is not revoked. Expired or malformed exceptions fail closed.",
            *self._evidence("policy.py::_exception_is_active", "policy.py::_lookup_exception"),
        )
        return findings


COMPONENT = ContainerHardeningComponent
