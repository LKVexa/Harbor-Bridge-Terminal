"""Resource-exhaustion controls (INV11-MC-15).  Every limit fails closed."""
from __future__ import annotations

from dataclasses import asdict, dataclass


class LimitExceeded(Exception):
    """Raised when a configured resource limit is breached (fail closed)."""

    def __init__(self, limit: str, value: int, maximum: int) -> None:
        super().__init__(f"limit {limit} exceeded: {value} > {maximum}")
        self.limit, self.value, self.maximum = limit, value, maximum
        self.code = "E-LIMIT-" + limit.upper().replace("_", "-")


@dataclass(frozen=True)
class Limits:
    max_source_bytes: int = 4 * 1024 * 1024
    max_files: int = 4096
    max_tokens: int = 1_000_000
    max_nesting: int = 64
    max_identifier: int = 256
    max_declarations: int = 100_000
    max_diagnostics: int = 200
    max_graph_nodes: int = 500_000
    max_compare_steps: int = 5_000_000
    max_json_bytes: int = 16 * 1024 * 1024

    def check(self, limit: str, value: int) -> None:
        maximum = getattr(self, "max_" + limit)
        if value > maximum:
            raise LimitExceeded(limit, value, maximum)

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


DEFAULT_LIMITS = Limits()


class WorkBudget:
    """Counts comparison/graph work so hostile inputs cannot run unbounded."""

    def __init__(self, limits: Limits = DEFAULT_LIMITS, limit: str = "compare_steps") -> None:
        self.limits, self.limit, self.used = limits, limit, 0

    def spend(self, n: int = 1) -> None:
        self.used += n
        self.limits.check(self.limit, self.used)
