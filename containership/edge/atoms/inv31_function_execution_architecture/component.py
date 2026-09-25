"""pk_core adapter for INV-31 - Function execution architecture.

The lifecycle implementation itself lives in :mod:`runtime` so its safety
properties remain testable even when the external pk_core framework is absent.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .runtime import (
    CONCURRENCY_LIMIT,
    MAX_AGE,
    MAX_POOL_INSTANCES,
    ConcurrencyExceeded,
    FunctionPool,
    Instance,
    InstanceDestroyed,
    InstanceExpired,
    PoolCapacityExceeded,
)


def _verify(condition: bool, message: str = "behavioural check failed") -> None:
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class FunctionExecutionArchitectureComponent(Component):
    """Master-applied component for INV-31."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)

        instance = Instance("fn-1", "tenant-a", "v1", 0)
        try:
            instance.tenant = "tenant-b"
        except AttributeError:
            findings[1] = self.satisfied(
                items[1],
                "Instance identity (name, tenant, code version and creation tick) is immutable while "
                "invocation state is held separately in bounded per-invocation scratch scopes.",
                *self._evidence("runtime.py::Instance"),
            )
        else:
            raise AssertionError("instance identity mutation unexpectedly succeeded")

        try:
            FunctionPool(concurrency_limit=0)
        except ValueError:
            findings[3] = self.satisfied(
                items[3],
                "Runtime limits are validated before pool activation; invalid security-critical limits "
                "fail closed rather than falling back to an unbounded value.",
                *self._evidence("runtime.py::FunctionPool.__post_init__"),
            )
        else:
            raise AssertionError("invalid pool configuration was unexpectedly accepted")

        configured = FunctionPool(concurrency_limit=2, max_age=30, max_instances=8)
        state = configured.pool_snapshot(0)["configuration"]
        _verify(state == {"concurrency_limit": 2, "max_age": 30, "max_instances": 8})
        findings[4] = self.satisfied(
            items[4],
            "Concurrency, maximum age and pool safety ceiling are runtime configuration values with "
            "validated secure defaults, so environment-specific policy does not require rebuilding code.",
            *self._evidence("runtime.py::FunctionPool"),
        )
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        pool = FunctionPool()
        first = pool.invoke(tenant="t1", version="v1", now=0)
        other_tenant = pool.invoke(tenant="t2", version="v1", now=1)
        other_version = pool.invoke(tenant="t1", version="v2", now=2)
        _verify(other_tenant["cold"] and other_tenant["instance"] != first["instance"])
        _verify(other_version["cold"] and other_version["instance"] != first["instance"])
        findings[5] = self.satisfied(
            items[5],
            "Warm reuse requires an exact tenant and code-version match; both a tenant change and a "
            "version change force a distinct cold instance, preventing cross-boundary memory reuse.",
            *self._evidence("runtime.py::Instance.reusable_for"),
        )
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        instance = Instance("fn-1", "t1", "v1", 0)
        scopes = [instance.enter() for _ in range(CONCURRENCY_LIMIT)]
        try:
            instance.enter()
        except ConcurrencyExceeded:
            findings[3] = self.satisfied(
                items[3],
                f"Admission is bounded at {CONCURRENCY_LIMIT} concurrent invocations per instance; "
                "excess work is rejected rather than allowed to corrupt shared state.",
                *self._evidence("runtime.py::Instance.enter"),
            )
        else:
            raise AssertionError("expected ConcurrencyExceeded was not raised")
        finally:
            for scope_id in scopes:
                instance.leave(scope_id)

        pool = FunctionPool()
        created = pool.invoke(tenant="t1", version="v1", now=0)["instance"]
        destroyed = pool.destroy_idle(tenant="t1")
        _verify(destroyed == [created] and not pool.instances)
        findings[8] = self.satisfied(
            items[8],
            "Operators can quarantine/drain matching idle instances without terminating in-flight work; "
            "destroyed instances are removed from future reuse.",
            *self._evidence("runtime.py::FunctionPool.destroy_idle"),
        )
        return findings


COMPONENT = FunctionExecutionArchitectureComponent

__all__ = [
    "COMPONENT",
    "FunctionExecutionArchitectureComponent",
    "CONCURRENCY_LIMIT",
    "MAX_AGE",
    "MAX_POOL_INSTANCES",
    "ConcurrencyExceeded",
    "PoolCapacityExceeded",
    "InstanceDestroyed",
    "InstanceExpired",
    "Instance",
    "FunctionPool",
]
