# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Constraint-precedence policy (GAP-013).

When requirements conflict, the higher rank wins and the loser is recorded in a
decision record. Rank 0 (zero-budget capability invariants) can never be waived.
"""
from __future__ import annotations

PRECEDENCE = (
    ("capability-invariant", "No OOB success, no amplification, no reuse after invalidation, no false hardware claim"),
    ("security", "Authentication, authorization, tenant isolation, provenance"),
    ("residency", "Data/tenant residency and deployment-context restrictions"),
    ("hardware-requirement", "Workload's declared need for hardware enforcement"),
    ("slo", "Latency/availability objectives"),
    ("cost", "Resource efficiency"),
    ("convenience", "Operator/developer convenience"),
)
RANK = {name: i for i, (name, _) in enumerate(PRECEDENCE)}
UNWAIVABLE = {"capability-invariant"}


def resolve(conflicting: list[str]) -> str:
    unknown = [c for c in conflicting if c not in RANK]
    if unknown:
        raise ValueError(f"unknown constraint class {unknown}")
    return min(conflicting, key=RANK.__getitem__)


def waivable(constraint: str) -> bool:
    return constraint not in UNWAIVABLE
