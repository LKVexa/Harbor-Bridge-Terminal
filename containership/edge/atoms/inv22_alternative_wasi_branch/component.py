"""INV-22 - Alternative WASI branch.

Fail-closed compatibility management for a standards WASI branch and an
alternative branch.  Unknown interfaces, invalid classifications, unsupported
branches, and semantically divergent interfaces are never treated as
compatible by default.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


def _verify(condition: bool, message: str = "behavioural check failed") -> None:
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


IDENTICAL, SHIMMABLE, DIVERGENT = "identical", "shimmable", "divergent"
VALID_CLASSIFICATIONS = frozenset({IDENTICAL, SHIMMABLE, DIVERGENT})
BRANCHES = ("standards", "fork")

# Keep the authoritative matrix immutable so runtime code cannot silently alter
# compatibility after certification.
_MATRIX_DATA = {
    "clocks": IDENTICAL,
    "random": IDENTICAL,
    "filesystem": SHIMMABLE,
    "sockets": DIVERGENT,
    "threads": DIVERGENT,
}
MATRIX: Mapping[str, str] = MappingProxyType(_MATRIX_DATA)


class Unclassified(KeyError):
    """Raised for an interface not in the matrix."""

    code = "INV22.CLASSIFY.UNCLASSIFIED"  # stable external code (MC-16); see errors.REGISTRY


class InvalidClassification(ValueError):
    """Raised when a matrix contains an unknown classification value."""

    code = "INV22.CLASSIFY.INVALID"  # stable external code (MC-16); see errors.REGISTRY


class SemanticDivergence(RuntimeError):
    """Raised when a shim is requested for a semantically divergent interface."""

    code = "INV22.TRANSLATE.DIVERGENT"  # stable external code (MC-16); see errors.REGISTRY


class UncertifiedBranch(RuntimeError):
    """Raised when a component is run on a branch it was not certified against."""

    code = "INV22.CERT.UNCERTIFIED_BRANCH"  # stable external code (MC-16); see errors.REGISTRY


def _require_nonempty_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _validate_branch(branch: str) -> str:
    branch = _require_nonempty_text(branch, "branch")
    if branch not in BRANCHES:
        raise ValueError(f"unknown branch: {branch!r}")
    return branch


def validate_matrix(matrix: Mapping[str, str]) -> None:
    """Validate matrix shape and classification values, failing closed."""
    if not isinstance(matrix, Mapping):
        raise TypeError("matrix must be a mapping")
    for interface, classification in matrix.items():
        _require_nonempty_text(interface, "interface")
        if classification not in VALID_CLASSIFICATIONS:
            raise InvalidClassification(
                f"{interface!r} has unsupported classification {classification!r}"
            )


def classify(interface: str, matrix: Mapping[str, str] = MATRIX) -> str:
    interface = _require_nonempty_text(interface, "interface")
    validate_matrix(matrix)
    if interface not in matrix:
        raise Unclassified(interface)
    return matrix[interface]


def shim(interface: str, value: Any, frm: str, to: str) -> Any:
    """Translate a value between branches, or refuse.

    Same-branch calls are an identity operation.  Cross-branch calls pass
    identical interfaces through unchanged, wrap shimmable values in an
    explicit envelope, and fail closed for divergent or unknown interfaces.
    """
    frm = _validate_branch(frm)
    to = _validate_branch(to)
    kind = classify(interface)
    if frm == to or kind == IDENTICAL:
        return value
    if kind == DIVERGENT:
        raise SemanticDivergence(
            f"{interface} has different semantics on each branch; no shim can be correct"
        )
    return {"branch": to, "source_branch": frm, "interface": interface, "value": value}


@dataclass
class Certification:
    """Branch certification with fail-closed enforcement and refusal telemetry."""

    component: str
    branch: str
    uncertified_runs: int = 0

    def __post_init__(self) -> None:
        self.component = _require_nonempty_text(self.component, "component id")
        self.branch = _validate_branch(self.branch)
        if not isinstance(self.uncertified_runs, int) or isinstance(self.uncertified_runs, bool) or self.uncertified_runs < 0:
            raise ValueError("uncertified_runs must be a non-negative integer")

    def run_on(self, branch: str) -> str:
        branch = _validate_branch(branch)
        if branch != self.branch:
            self.uncertified_runs += 1
            raise UncertifiedBranch(
                f"{self.component} is certified for '{self.branch}', not '{branch}'"
            )
        return "ok"


@dataclass
class DriftReport:
    """Divergence measured per release in insertion order."""

    releases: dict[str, int] = field(default_factory=dict)

    def record(self, release: str, matrix: Mapping[str, str]) -> int:
        release = _require_nonempty_text(release, "release")
        validate_matrix(matrix)
        divergent = sum(1 for value in matrix.values() if value == DIVERGENT)
        self.releases[release] = divergent
        return divergent

    def growing(self) -> bool:
        counts = list(self.releases.values())
        return len(counts) > 1 and counts[-1] > counts[0]

    def delta(self) -> int:
        counts = list(self.releases.values())
        return 0 if len(counts) < 2 else counts[-1] - counts[-2]


class AlternativeWasiBranchComponent(Component):
    """Master-applied component for INV-22."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        _verify(shim("clocks", 5, "standards", "fork") == 5)
        translated = shim("filesystem", "/data", "standards", "fork")
        _verify(translated["branch"] == "fork" and translated["source_branch"] == "standards")
        refused = False
        try:
            shim("sockets", None, "standards", "fork")
        except SemanticDivergence:
            refused = True
        unknown = False
        try:
            classify("some-new-interface")
        except Unclassified:
            unknown = True
        _verify(refused and unknown)
        counts = {k: sum(1 for v in MATRIX.values() if v == k)
                  for k in (IDENTICAL, SHIMMABLE, DIVERGENT)}
        findings[0] = self.satisfied(
            items[0],
            f"Every interface carries an explicit classification ({counts}); identical ones pass through, "
            "shimmable ones translate, divergent ones refuse, and an interface nobody has compared raises "
            "rather than defaulting to compatible.",
            *self._evidence("component.py::MATRIX", "component.py::shim", "component.py::validate_matrix"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        cert = Certification("edge-handler", "standards")
        _verify(cert.run_on("standards") == "ok")
        blocked = False
        try:
            cert.run_on("fork")
        except UncertifiedBranch:
            blocked = True
        _verify(blocked and cert.uncertified_runs == 1)
        findings[1] = self.satisfied(
            items[1],
            "A component records the branch it was certified against and is refused on any other, so a "
            "deployment cannot quietly move a workload onto semantics it was never tested under.",
            *self._evidence("component.py::Certification.run_on"))
        return findings

    def assess_observability(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_observability(items)
        drift = DriftReport()
        drift.record("v1", {"clocks": IDENTICAL})
        now = drift.record("v2", MATRIX)
        _verify(drift.growing() and now == 2 and drift.delta() == 2)
        findings[1] = self.satisfied(
            items[1],
            f"Divergence is counted per release (v1: 0, v2: {now}) and growth is reported explicitly, so "
            "branch drift is measurable before workload behaviour changes.",
            *self._evidence("component.py::DriftReport"))
        return findings

    def assess_testing(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_testing(items)
        validate_matrix(MATRIX)
        classified = sum(1 for interface in MATRIX if classify(interface))
        _verify(classified == len(MATRIX))
        findings[0] = self.satisfied(
            items[0],
            f"All {classified} matrix entries resolve to a validated classification and each classification "
            "path (pass-through, shim, refusal, unclassified) is exercised.",
            *self._evidence("component.py::classify", "component.py::MATRIX"))
        return findings


COMPONENT = AlternativeWasiBranchComponent
