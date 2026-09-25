"""M13 - parser resource governor.

All ceilings apply *while* decoding (before allocation), not after.  A
:class:`Governor` also enforces a work budget (abstract steps) and a monotonic
wall-clock deadline; exceeding either is a refusal, never a partial accept.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, asdict
import hashlib
import json

from .errors import Code, InvalidModule


@dataclass(frozen=True)
class Limits:
    max_module_bytes: int = 4 * 1024 * 1024
    max_sections: int = 64
    max_custom_sections: int = 32
    max_vector_count: int = 100_000
    max_types: int = 10_000
    max_type_arity: int = 1_000
    max_imports: int = 10_000
    max_functions: int = 50_000
    max_tables: int = 100
    max_memories: int = 1
    max_globals: int = 10_000
    max_exports: int = 10_000
    max_elem_segments: int = 10_000
    max_data_segments: int = 10_000
    max_name_bytes: int = 1_024
    max_locals_per_function: int = 50_000
    max_function_body_bytes: int = 1_024 * 1_024
    max_control_depth: int = 1_024
    max_operand_stack: int = 65_536
    max_br_table_targets: int = 65_536
    max_steps: int = 50_000_000
    deadline_seconds: float = 10.0

    def revision(self) -> str:
        blob = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return "limits:sha256:" + hashlib.sha256(blob.encode()).hexdigest()[:16]


DEFAULT_LIMITS = Limits()


class Governor:
    """Counts work and checks the deadline.  Not shared between threads."""

    __slots__ = ("limits", "_steps", "_deadline", "_check_every", "_clock", "_next_check")

    def __init__(self, limits: Limits = DEFAULT_LIMITS, *, clock=time.monotonic):
        self.limits = limits
        self._steps = 0
        self._deadline = clock() + limits.deadline_seconds
        self._check_every = 4096
        self._clock = clock
        self._next_check = 0  # first step always checks the deadline

    def step(self, n: int = 1) -> None:
        self._steps += n
        if self._steps > self.limits.max_steps:
            raise InvalidModule(Code.LIMIT_EXCEEDED, "work budget exhausted")
        if self._steps >= self._next_check:
            self._next_check = self._steps + self._check_every
            if self._clock() > self._deadline:
                raise InvalidModule(Code.DEADLINE_EXCEEDED, "validation deadline exceeded")

    def cap(self, value: int, ceiling: int, what: str, offset: int | None = None) -> int:
        if value > ceiling:
            raise InvalidModule(Code.LIMIT_EXCEEDED, f"{what} {value} > {ceiling}", offset=offset)
        return value

    @property
    def steps(self) -> int:
        return self._steps
