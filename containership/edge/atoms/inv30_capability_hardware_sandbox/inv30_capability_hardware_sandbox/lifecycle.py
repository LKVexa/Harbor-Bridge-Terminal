# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Formal lifecycle and result-state model (GAP-012). Illegal transitions raise."""
from __future__ import annotations

# Capability lifecycle (per handle)
MINTED, ACTIVE, INVALIDATED = "minted", "active", "invalidated"
CAPABILITY_TRANSITIONS = {MINTED: {ACTIVE, INVALIDATED}, ACTIVE: {INVALIDATED}, INVALIDATED: set()}

# Service lifecycle
SERVICE_TRANSITIONS = {
    "bootstrapping": {"ready", "failed"},
    "ready": {"degraded", "quarantined", "disabled", "draining"},
    "degraded": {"ready", "quarantined", "disabled", "draining"},
    "quarantined": {"ready", "disabled"},          # release requires operator action
    "disabled": {"bootstrapping"},                  # re-enable = fresh bootstrap
    "draining": {"stopped"},
    "failed": {"bootstrapping"},
    "stopped": set(),
}

# Result states for any operation
SUCCESS, PARTIAL, DEGRADED, RETRYABLE, TERMINAL = "success", "partial", "degraded", "retryable_failure", "terminal_failure"
RESULT_STATES = (SUCCESS, PARTIAL, DEGRADED, RETRYABLE, TERMINAL)


def transition(table: dict, current: str, target: str) -> str:
    if target not in table.get(current, set()):
        raise ValueError(f"illegal transition {current} -> {target}")
    return target


def result_state(outcome: dict) -> str:
    """Classify an operation outcome. Security codes are always terminal."""
    if outcome.get("schema") == "PK_FAILURE/1":
        return RETRYABLE if outcome["retryable"] else TERMINAL
    if outcome.get("degraded"):
        return DEGRADED
    if outcome.get("partial"):
        return PARTIAL
    return SUCCESS
