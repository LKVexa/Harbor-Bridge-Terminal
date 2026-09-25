"""GAP-15 - Runtime compatibility certification.

Runtime compatibility certification answers the question a heterogeneous edge
estate asks constantly: will this artifact actually run on that node? It
certifies against a declared matrix and refuses to guess, because an untested
pair is not a supported pair.

The component answers all 100 requirements of the GAP-15 checklist. Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


CERTIFIED, INCOMPATIBLE, UNTESTED, EXPIRED, END_OF_LIFE = (
    "certified",
    "incompatible",
    "untested",
    "expired",
    "end-of-life",
)

#: How long a positive certification remains deployable before re-testing.
CERTIFICATION_TTL_SECONDS = 500
#: Backward-compatible alias retained for callers of v4.1.x.
CERTIFICATION_TTL = CERTIFICATION_TTL_SECONDS

SUPPORTED, DEPRECATED, EOL = "supported", "deprecated", "end-of-life"
_LIFECYCLE_ORDER = {SUPPORTED: 0, DEPRECATED: 1, EOL: 2}
_MAX_IDENTIFIER_LENGTH = 512


def _verify(condition: bool, message: str = "behavioural check failed") -> None:
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


def _validate_identifier(value: object, *, field_name: str) -> str:
    """Validate an externally supplied identifier without silently normalising it."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string, got {type(value).__name__}")
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be non-empty and have no edge whitespace")
    if len(value) > _MAX_IDENTIFIER_LENGTH:
        raise ValueError(f"{field_name} exceeds {_MAX_IDENTIFIER_LENGTH} characters")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError(f"{field_name} contains control characters")
    return value


def _validate_timestamp(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be a non-negative integer, got {value!r}")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative, got {value!r}")
    return value


@dataclass(frozen=True)
class Triple:
    """The unit of certification: one artifact on one runtime on one node profile."""

    artifact: str
    runtime: str
    profile: str

    def __post_init__(self) -> None:
        _validate_identifier(self.artifact, field_name="triple artifact")
        _validate_identifier(self.runtime, field_name="triple runtime")
        _validate_identifier(self.profile, field_name="triple profile")

    def as_dict(self) -> dict[str, str]:
        """Return stable machine-readable coordinates for external schemas."""
        return {
            "artifact": self.artifact,
            "runtime": self.runtime,
            "profile": self.profile,
        }


@dataclass
class CompatibilityMatrix:
    """Sparse compatibility evidence with fail-closed certification semantics.

    ``results`` stores only the latest accepted result for a triple. ``revision``
    increases after each accepted mutation so exported matrix/lifecycle views can
    be correlated with certification decisions. Older evidence cannot overwrite
    newer evidence and contradictory evidence at the same timestamp is rejected.
    """

    environment: str
    #: Triple -> (compatible: bool, tested_at: unix-like integer seconds)
    results: dict[Triple, tuple[bool, int]] = field(default_factory=dict)
    #: runtime version -> lifecycle state
    lifecycle: dict[str, str] = field(default_factory=dict)
    revision: int = 0

    def __post_init__(self) -> None:
        _validate_identifier(self.environment, field_name="environment")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int):
            raise TypeError("revision must be a non-negative integer")
        if self.revision < 0:
            raise ValueError("revision must be a non-negative integer")

        # Validate caller-provided initial state. Copy it so subsequent mutation of
        # the caller's original dict cannot alter the matrix behind this object.
        raw_results = dict(self.results)
        raw_lifecycle = dict(self.lifecycle)
        self.results = {}
        self.lifecycle = {}
        for triple, record in raw_results.items():
            if not isinstance(triple, Triple):
                raise TypeError(f"results key must be Triple, got {type(triple).__name__}")
            if not isinstance(record, tuple) or len(record) != 2:
                raise TypeError("results values must be (compatible: bool, tested_at: int) tuples")
            compatible, tested_at = record
            if not isinstance(compatible, bool):
                raise TypeError(f"compatible must be a bool, got {compatible!r}")
            _validate_timestamp(tested_at, field_name="tested_at")
            self.results[triple] = (compatible, tested_at)
        for runtime, state in raw_lifecycle.items():
            self._validate_lifecycle(runtime, state)
            self.lifecycle[runtime] = state

    @staticmethod
    def _validate_lifecycle(runtime: object, state: object) -> tuple[str, str]:
        runtime_id = _validate_identifier(runtime, field_name="runtime")
        if not isinstance(state, str) or state not in _LIFECYCLE_ORDER:
            raise ValueError(f"unknown lifecycle state: {state!r}")
        return runtime_id, state

    def record(self, triple: Triple, *, compatible: bool, at: int) -> None:
        """Record test evidence, rejecting rollback/replay ambiguity.

        A newer result may supersede an older result. The same result at the same
        timestamp is idempotent. An older result, or a contradictory result with
        the same timestamp, is rejected so stale/replayed evidence cannot silently
        replace the current source of truth.
        """
        if not isinstance(triple, Triple):
            raise TypeError(f"expected Triple, got {type(triple).__name__}")
        if not isinstance(compatible, bool):
            raise TypeError(f"compatible must be a bool, got {compatible!r}")
        tested_at = _validate_timestamp(at, field_name="test time")

        existing = self.results.get(triple)
        if existing is not None:
            previous_compatible, previous_at = existing
            if tested_at < previous_at:
                raise ValueError(
                    f"stale test evidence at {tested_at} cannot replace newer evidence at {previous_at}"
                )
            if tested_at == previous_at:
                if compatible != previous_compatible:
                    raise ValueError("contradictory test evidence at the same timestamp")
                return  # exact replay is idempotent and does not advance revision

        self.results[triple] = (compatible, tested_at)
        self.revision += 1

    def set_lifecycle(
        self, runtime: str, state: str, *, allow_reactivation: bool = False
    ) -> None:
        """Set lifecycle state while preventing accidental state regression."""
        if not isinstance(allow_reactivation, bool):
            raise TypeError("allow_reactivation must be a bool")
        runtime_id, state_id = self._validate_lifecycle(runtime, state)
        current = self.lifecycle.get(runtime_id)
        if current == state_id:
            return
        if (
            current is not None
            and _LIFECYCLE_ORDER[state_id] < _LIFECYCLE_ORDER[current]
            and not allow_reactivation
        ):
            raise ValueError(
                f"lifecycle regression {current!r} -> {state_id!r} requires allow_reactivation=True"
            )
        self.lifecycle[runtime_id] = state_id
        self.revision += 1

    def _record_for(self, triple: Triple) -> Optional[tuple[bool, int]]:
        """Return a validated stored result, failing closed on direct-state corruption."""
        record = self.results.get(triple)
        if record is None:
            return None
        if not isinstance(record, tuple) or len(record) != 2:
            raise ValueError(f"malformed result stored for {triple!r}")
        compatible, tested_at = record
        if not isinstance(compatible, bool):
            raise ValueError(f"malformed compatibility value stored for {triple!r}")
        _validate_timestamp(tested_at, field_name="stored test time")
        return compatible, tested_at

    def _lifecycle_state_for(self, runtime: str) -> str:
        """Return a validated lifecycle state, detecting direct-state corruption."""
        state = self.lifecycle.get(runtime, SUPPORTED)
        if not isinstance(state, str) or state not in _LIFECYCLE_ORDER:
            raise ValueError(f"invalid lifecycle state stored for {runtime!r}: {state!r}")
        return state

    def _base_verdict(self, triple: Triple, state: str) -> dict[str, object]:
        return {
            "schema": "PK_CERTIFICATION/1",
            "environment": self.environment,
            "matrix_revision": self.revision,
            # Keep the v4.1 string field for compatibility and add typed coordinates.
            "triple": str(triple),
            "coordinates": triple.as_dict(),
            "deprecated": state == DEPRECATED,
        }

    def certify(self, triple: Triple, now: int) -> dict[str, object]:
        """Return a fail-closed verdict for one exact artifact/runtime/profile triple."""
        if not isinstance(triple, Triple):
            raise TypeError(f"expected Triple, got {type(triple).__name__}")
        current_time = _validate_timestamp(now, field_name="now")
        state = self._lifecycle_state_for(triple.runtime)

        base = self._base_verdict(triple, state)
        if state == EOL:
            return {
                **base,
                "verdict": END_OF_LIFE,
                "reason": f"runtime {triple.runtime} is end-of-life",
                "deployable": False,
            }

        record = self._record_for(triple)
        if record is None:
            return {
                **base,
                "verdict": UNTESTED,
                "reason": "no recorded test result for this triple; compatibility is not inferred",
                "deployable": False,
            }
        compatible, tested_at = record

        # Timestamp validity must be checked before either positive or negative
        # evidence is trusted. v4.1.0 only applied this check to compatible results.
        if tested_at > current_time:
            return {
                **base,
                "verdict": UNTESTED,
                "reason": (
                    f"test result dated {tested_at} is later than now ({current_time}); not evidence"
                ),
                "deployable": False,
            }

        if not compatible:
            return {
                **base,
                "verdict": INCOMPATIBLE,
                "reason": f"tested at {tested_at} and found incompatible",
                "deployable": False,
                "tested_at": tested_at,
            }

        age = current_time - tested_at
        expires_at = tested_at + CERTIFICATION_TTL_SECONDS
        if age > CERTIFICATION_TTL_SECONDS:
            return {
                **base,
                "verdict": EXPIRED,
                "reason": (
                    f"certified at {tested_at}, older than {CERTIFICATION_TTL_SECONDS} seconds"
                ),
                "deployable": False,
                "tested_at": tested_at,
                "expires_at": expires_at,
                "age": age,
            }
        return {
            **base,
            "verdict": CERTIFIED,
            "reason": f"tested compatible at {tested_at}",
            "deployable": True,
            "tested_at": tested_at,
            "expires_at": expires_at,
            "age": age,
        }

    def coverage(self, requested: Iterable[Triple]) -> float:
        """Return tested coverage over unique requested triples."""
        try:
            unique = set(requested)
        except TypeError as exc:
            raise TypeError("requested must be an iterable of hashable Triple values") from exc
        if any(not isinstance(triple, Triple) for triple in unique):
            raise TypeError("requested must contain only Triple values")
        if not unique:
            return 1.0
        return sum(1 for triple in unique if self._record_for(triple) is not None) / len(unique)

    def matrix_view(self) -> dict[str, object]:
        """Export the versioned compatibility matrix interface deterministically."""
        rows = []
        triples = list(self.results)
        if any(not isinstance(triple, Triple) for triple in triples):
            raise ValueError("malformed non-Triple result key stored")
        for triple in sorted(
            triples, key=lambda item: (item.artifact, item.runtime, item.profile)
        ):
            record = self._record_for(triple)
            if record is None:  # impossible for an iterated key, defensive only
                raise ValueError(f"result disappeared while exporting {triple!r}")
            compatible, tested_at = record
            rows.append(
                {
                    **triple.as_dict(),
                    "compatible": compatible,
                    "tested_at": tested_at,
                }
            )
        return {
            "schema": "PK_COMPATIBILITY_MATRIX/1",
            "environment": self.environment,
            "revision": self.revision,
            "results": rows,
        }

    def lifecycle_view(self) -> dict[str, object]:
        """Export the versioned runtime lifecycle interface deterministically."""
        runtimes = list(self.lifecycle)
        if any(not isinstance(runtime, str) for runtime in runtimes):
            raise ValueError("malformed non-string lifecycle key stored")
        return {
            "schema": "PK_RUNTIME_LIFECYCLE/1",
            "environment": self.environment,
            "revision": self.revision,
            "runtimes": [
                {"runtime": runtime, "state": self._lifecycle_state_for(runtime)}
                for runtime in sorted(runtimes)
            ],
        }


class RuntimeCompatibilityCertificationComponent(Component):
    """Master-applied component for GAP-15."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        matrix = CompatibilityMatrix("prod")
        good = Triple("svc:1", "wasmtime-21", "arm64-sev")
        bad = Triple("svc:1", "wasmtime-20", "arm64-sev")
        matrix.record(good, compatible=True, at=0)
        matrix.record(bad, compatible=False, at=0)
        _verify(
            matrix.certify(good, now=1)["verdict"] == CERTIFIED,
            "check failed: compatible evidence must certify",
        )
        _verify(
            matrix.certify(bad, now=1)["verdict"] == INCOMPATIBLE,
            "check failed: incompatible evidence must remain distinct from untested",
        )
        _verify(
            matrix.matrix_view()["revision"] == 2,
            "check failed: accepted matrix mutations must advance revision",
        )
        findings[5] = self.satisfied(
            items[5],
            "Certification reads directly from recorded test results and exports a revisioned matrix, "
            "so certified and incompatible triples are both answered from exact evidence.",
            *self._evidence("component.py::CompatibilityMatrix.certify"),
        )
        return findings

    def assess_requirements(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_requirements(items)
        matrix = CompatibilityMatrix("prod")
        matrix.record(Triple("svc:1", "wasmtime-21", "arm64-sev"), compatible=True, at=0)
        near = matrix.certify(Triple("svc:1", "wasmtime-21", "arm64-tdx"), now=1)
        _verify(
            near["verdict"] == UNTESTED and not near["deployable"],
            "check failed: nearby profiles must not inherit certification",
        )
        findings[6] = self.satisfied(
            items[6],
            "A neighbouring profile that differs only in its isolation primitive returns untested rather "
            "than inheriting the certified verdict: similarity is never evidence.",
            *self._evidence("component.py::CompatibilityMatrix.certify"),
        )
        _verify(
            matrix.coverage(
                [
                    Triple("svc:1", "wasmtime-21", "arm64-sev"),
                    Triple("svc:1", "wasmtime-21", "arm64-tdx"),
                ]
            )
            == 0.5,
            "check failed: matrix coverage must be measurable",
        )
        findings[1] = self.satisfied(
            items[1],
            "Matrix coverage is measurable (0.5 over a two-triple request), so sparseness is reported "
            "rather than hidden.",
            *self._evidence("component.py::CompatibilityMatrix.coverage"),
        )
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        matrix = CompatibilityMatrix("prod")
        triple = Triple("svc:1", "wasmtime-21", "arm64-sev")
        matrix.record(triple, compatible=True, at=0)
        _verify(
            matrix.certify(triple, now=CERTIFICATION_TTL_SECONDS)["verdict"] == CERTIFIED,
            "check failed: certification is valid through its TTL boundary",
        )
        expired = matrix.certify(triple, now=CERTIFICATION_TTL_SECONDS + 1)
        _verify(
            expired["verdict"] == EXPIRED and not expired["deployable"],
            "check failed: stale certification must fail closed",
        )
        findings[3] = self.satisfied(
            items[3],
            f"A positive certification expires after {CERTIFICATION_TTL_SECONDS} seconds and stops being "
            "deployable, so stale positive evidence cannot carry a rollout.",
            *self._evidence("component.py::CompatibilityMatrix.certify"),
        )
        matrix.set_lifecycle("wasmtime-21", EOL)
        eol = matrix.certify(triple, now=1)
        _verify(
            eol["verdict"] == END_OF_LIFE and not eol["deployable"],
            "check failed: EOL must override fresh compatible evidence",
        )
        findings[1] = self.satisfied(
            items[1],
            "An end-of-life runtime overrides even a fresh passing test result, so an unsupported runtime "
            "cannot stay in service on the strength of old evidence.",
            *self._evidence("component.py::CompatibilityMatrix.certify"),
        )
        return findings


COMPONENT = RuntimeCompatibilityCertificationComponent
