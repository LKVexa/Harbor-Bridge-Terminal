"""INV-71 - Heavy agent sandbox.

The heavy agent sandbox is for code the fast sandbox cannot or should not hold: real interpreters, package installs, browsers. Each agent session gets its own microVM-class boundary with a filesystem that starts from a clean snapshot, egress limited to an allowlist, and a teardown that leaves nothing behind for the next session to find.

The component integrates with the 100-item INV-71 checklist. Selected bands
exercise the element's dependency-free reference behaviour directly. Framework
default findings must not be interpreted as proof that a production microVM
implementation exists; see AUDIT_AFTER.json and MISSING_COMPONENTS.md.
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



from .sandbox import (
    BASE,
    BASE_DIGEST,
    EgressDenied,
    LimitExceeded,
    Session,
    SessionClosed,
    digest,
    new_session,
)


class HeavyAgentSandboxComponent(Component):
    """Master-applied component for INV-71."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        s1 = new_session("s1", allow=["pypi.org"])
        s1.write("/tmp/stolen.txt", b"customer data")
        s1.connect("pypi.org")
        exfil = False
        try:
            s1.connect("paste.evil.example")
        except EgressDenied:
            exfil = True
        traversal_refused = False
        try:
            s1.write("../escape", b"nope")
        except ValueError:
            traversal_refused = True
        record = s1.teardown()
        s2 = new_session("s2")
        _verify(exfil and traversal_refused and record["verified"], "security refusal or teardown verification failed")
        _verify(record["audit_chain_valid"], "teardown audit chain is invalid")
        _verify("/tmp/stolen.txt" not in s2.fs and digest(s2.fs) == BASE_DIGEST, "clean snapshot isolation failed")
        findings[0] = self.satisfied(
            items[0],
            "The dependency-free reference model canonicalizes and allowlists egress, rejects traversal paths, "
            "clears guest-visible mutable state and capabilities on teardown, validates its bounded audit chain, "
            "and creates the next session from the immutable clean-snapshot digest. This evidence validates the "
            "reference semantics; it does not substitute for a production microVM escape/isolation test.",
            *self._evidence("sandbox.py::Session", "sandbox.py::new_session"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        s = new_session("s3")
        s.disk_quota = 1000
        s.write("/work/a", b"x" * 600)
        hit = False
        try:
            s.write("/work/b", b"x" * 600)
        except LimitExceeded:
            hit = True
        _verify(hit and "/work/b" not in s.fs, "check failed: hit and '/work/b' not in s.fs")
        findings[0] = self.satisfied(
            items[0],
            "A session's writes are held to its disk quota: the write that would exceed it is refused "
            "and not partially applied, so one session cannot fill the host.",
            *self._evidence("sandbox.py::Session.write"))
        return findings

COMPONENT = HeavyAgentSandboxComponent
