"""INV-07 - GitOps transition layer.

The GitOps transition layer makes a git repository the source of desired state: a controller applies whatever the approved branch says, reverts changes made behind its back, and reports them. It only follows commits signed by an allowed key, and rolling back means reverting a commit -- so every change to the estate has an author, a review and an undo.

The component integrates with the 100-requirement INV-07 checklist. Bands
with high-value behavioral claims are overridden below so evidence is produced
by exercising the element's own behavior rather than merely restating contract
metadata. Full 100-item conformance still requires the external ``pk_core`` gate.
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



from .gitops_model import GitOps, NothingToSync, Unsigned, sign


class GitopsTransitionLayerComponent(Component):
    """Master-applied component for INV-07."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        g = GitOps({"release": b"k1"})
        g.commit({"api": "v1"}, "release", sign(b"k1", {"api": "v1"}))
        g.sync()
        g.commit({"api": "evil"}, "release", sign(b"stolen-guess", {"api": "evil"}))
        refused = False
        try:
            g.sync()
        except Unsigned:
            refused = True
        _verify(refused and g.live == {"api": "v1"}, "check failed: refused and g.live == {'api': 'v1'}")
        findings[0] = self.satisfied(
            items[0],
            "The controller applies only commits signed by an allowed key: a commit with a bad signature "
            "is refused and the live state stays on the last verified commit.",
            *self._evidence("gitops_model.py::GitOps.sync"))
        return findings

    def assess_operations(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_operations(items)
        g = GitOps({"r": b"k"})
        g.commit({"api": "v1", "replicas": 3}, "r", sign(b"k", {"api": "v1", "replicas": 3}))
        g.sync()
        g.live["replicas"] = 9                     # manual hotfix behind git's back
        g.sync()
        _verify(g.live["replicas"] == 3 and g.reports[-1]["reverted"] == ["replicas"], "check failed: g.live['replicas'] == 3 and g.reports[-1]['reverted'] == ['replicas']")
        g.commit({"api": "v2", "replicas": 3}, "r", sign(b"k", {"api": "v2", "replicas": 3}))
        g.sync()
        g.revert("r")
        g.sync()
        _verify(g.live["api"] == "v1" and len(g.applied) == 3, "check failed: g.live['api'] == 'v1' and len(g.applied) == 3")
        findings[0] = self.satisfied(
            items[0],
            "A manual change made behind git's back is reverted on the next sync and reported by name; "
            "rolling back from v2 is a signed revert commit, so the rollback has its own history entry.",
            *self._evidence("gitops_model.py::GitOps.sync", "gitops_model.py::GitOps.revert"))
        return findings

COMPONENT = GitopsTransitionLayerComponent
