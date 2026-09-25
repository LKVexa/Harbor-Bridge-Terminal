"""GAP-05 - State replication/consistency model.

The state replication and consistency model makes the edge's divergence explicit.
Writes taken on both sides of a partition are kept, not silently lost: the model
merges what causally supersedes older state and surfaces genuine concurrency for a
resolution decision instead of choosing a winner by wall-clock time.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .model import (
    InvalidWrite,
    ReplicatedKey,
    UnknownReplica,
    VectorEquivocationError,
    Write,
    concurrent,
    dominates,
)


def _verify(condition: bool, message: str = "behavioural check failed") -> None:
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class StateReplicationConsistencyModelComponent(Component):
    """Master-applied component for GAP-05."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        replicas = frozenset({"dub", "ams"})
        w1 = Write("k", "v1", "dub", (("dub", 1),))
        w2 = Write("k", "v2", "ams", (("ams", 1),))
        w3 = Write("k", "v3", "dub", (("ams", 1), ("dub", 2)))

        forward = ReplicatedKey("k", replicas)
        for write in (w1, w2, w3):
            forward.apply(write)
        backward = ReplicatedKey("k", replicas)
        for write in (w3, w2, w1):
            backward.apply(write)
        _verify(
            forward.conflict_set() == backward.conflict_set(),
            "convergence depends on delivery order",
        )
        findings[5] = self.satisfied(
            items[5],
            f"Convergence is order-independent: forward and reverse delivery both settle on "
            f"{[s.value for s in forward.siblings]}.",
            *self._evidence("model.py::ReplicatedKey.apply"),
        )
        return findings

    def assess_requirements(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_requirements(items)
        replicas = frozenset({"dub", "ams"})
        key = ReplicatedKey("k", replicas)
        _verify(key.apply(Write("k", "v1", "dub", (("dub", 1),))) == "converged")
        _verify(key.apply(Write("k", "v2", "ams", (("ams", 1),))) == "conflict")
        _verify(not key.converged and len(key.siblings) == 2)
        findings[4] = self.satisfied(
            items[4],
            "Causally concurrent writes become a two-write conflict rather than a "
            "last-writer-wins resolution; both values survive until something decides.",
            *self._evidence("model.py::concurrent", "model.py::ReplicatedKey.apply"),
        )
        winner = key.resolve("merged", "dub")
        _verify(key.converged and key.value() == "merged" and len(key.discarded) == 2)
        findings[3] = self.satisfied(
            items[3],
            f"Resolution writes a value dominating every unresolved write "
            f"({list(winner.vector)}) and records each resolved write with its reason.",
            *self._evidence("model.py::ReplicatedKey.resolve"),
        )
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        key = ReplicatedKey("k", frozenset({"dub"}))
        try:
            key.apply(Write("k", "v", "rogue", (("rogue", 99),)))
        except UnknownReplica:
            findings[3] = self.satisfied(
                items[3],
                "Unknown replica identities are refused at the model boundary. This is an "
                "identity-membership check, not cryptographic authentication of a declared replica; "
                "signed provenance remains an external production requirement.",
                *self._evidence("model.py::ReplicatedKey.apply"),
            )
        else:
            raise AssertionError("expected UnknownReplica was not raised")
        findings[6] = self.satisfied(
            items[6],
            "Ordering is causal only: the merge state machine does not consult wall-clock time, "
            "so clock skew cannot be used as a last-writer-wins tie-breaker.",
            *self._evidence("model.py::dominates"),
        )
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        replicas = frozenset({"dub", "ams"})
        key = ReplicatedKey("k", replicas)
        write = Write("k", "v1", "dub", (("dub", 1),))
        key.apply(write)
        _verify(key.apply(write) == "duplicate", "replay was applied twice")
        _verify(key.discarded[-1]["reason"].startswith("duplicate"))
        findings[4] = self.satisfied(
            items[4],
            "Write application is idempotent for unresolved writes: a replay is recorded "
            "as a duplicate discard rather than re-applied.",
            *self._evidence("model.py::ReplicatedKey.apply"),
        )
        findings[8] = self.satisfied(
            items[8],
            f"Every causal discard carries a reason ({len(key.discarded)} recorded), while "
            "overflow writes remain live in quarantine rather than disappearing.",
            *self._evidence("model.py::ReplicatedKey.discarded", "model.py::ReplicatedKey.quarantine"),
        )

        sites = frozenset(f"s{i}" for i in range(6))
        bounded = ReplicatedKey("cart", sites, max_siblings=3)
        outcomes = [
            bounded.apply(Write("cart", f"v{i}", f"s{i}", ((f"s{i}", 1),)))
            for i in range(5)
        ]
        _verify(outcomes[:3] == ["converged", "conflict", "conflict"])
        _verify(len(bounded.siblings) == 3 and len(bounded.quarantine) == 2)
        winner = bounded.resolve("merged", "s0")
        _verify(not bounded.quarantine, "resolution left quarantined writes unresolved")
        _verify(set(dict(winner.vector)) >= {"s0", "s1", "s2", "s3", "s4"})
        _verify(
            bounded.apply(Write("cart", "late", "s5", (("s5", 1),))) == "conflict"
        )
        findings[2] = self.satisfied(
            items[2],
            "The active conflict set is bounded while overflow remains preserved in a "
            "deterministically ordered quarantine. Resolution causally covers both active and "
            "quarantined writes before clearing the quarantine.",
            *self._evidence("model.py::ReplicatedKey.apply", "model.py::ReplicatedKey.resolve"),
        )
        return findings


COMPONENT = StateReplicationConsistencyModelComponent

__all__ = [
    "COMPONENT",
    "StateReplicationConsistencyModelComponent",
    "Write",
    "ReplicatedKey",
    "UnknownReplica",
    "InvalidWrite",
    "VectorEquivocationError",
    "dominates",
    "concurrent",
]
