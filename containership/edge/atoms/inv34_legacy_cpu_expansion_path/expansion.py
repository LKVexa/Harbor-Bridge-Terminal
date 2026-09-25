"""Pure-stdlib control logic for INV-34 legacy VM CPU expansion.

INV-34 is the conventional-VM CPU scaling path.  The production mechanism is
ACPI CPU hot-plug; this module deliberately owns the control-plane policy and
state machine, not a particular hypervisor driver.  A driver consumes accepted
requests and later reports the observed online-vCPU count back through
``record_observation``.

The separation matters: accepting a request is not the same thing as claiming
that a guest has on-lined the new CPUs.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, replace
from threading import RLock
from typing import Any

REQUEST_SCHEMA = "PK_CPU_EXPANSION_REQUEST/1"
RESULT_SCHEMA = "PK_CPU_EXPANSION_RESULT/1"
STATUS_SCHEMA = "PK_CPU_EXPANSION_STATUS/1"
MAX_IDENTIFIER_LENGTH = 128
MAX_VCPU_SANITY_LIMIT = 65_536


def _require_identifier(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise InvalidRequest(f"{label} must be a string", field=label)
    if not value or len(value) > MAX_IDENTIFIER_LENGTH:
        raise InvalidRequest(
            f"{label} length must be 1..{MAX_IDENTIFIER_LENGTH}", field=label
        )
    if value != value.strip() or any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise InvalidRequest(f"{label} must not contain whitespace or control characters", field=label)
    return value


def _require_int(
    value: object, label: str, *, minimum: int = 0, maximum: int | None = None
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidRequest(f"{label} must be an integer", field=label)
    if value < minimum:
        raise InvalidRequest(f"{label} must be >= {minimum}", field=label)
    if maximum is not None and value > maximum:
        raise InvalidRequest(f"{label} must be <= {maximum}", field=label)
    return value


class ExpansionError(RuntimeError):
    """Base class for machine-readable INV-34 policy failures."""

    code = "EXPANSION_ERROR"
    retryable = False

    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message)
        self.context = dict(context)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": str(self),
            "retryable": self.retryable,
            "context": dict(self.context),
        }


class InvalidRequest(ExpansionError):
    code = "INVALID_REQUEST"


class ExpansionDisabled(ExpansionError):
    code = "EXPANSION_DISABLED"


class HotplugUnsupported(ExpansionError):
    code = "HOTPLUG_UNSUPPORTED"


class ShrinkNotSupported(ExpansionError):
    code = "SHRINK_NOT_SUPPORTED"


class GuestLimitExceeded(ExpansionError):
    code = "GUEST_LIMIT_EXCEEDED"


class HostCapacityExceeded(ExpansionError):
    code = "HOST_CAPACITY_EXCEEDED"
    retryable = True


class StaleGeneration(ExpansionError):
    code = "STALE_GENERATION"
    retryable = True


class IdempotencyConflict(ExpansionError):
    code = "IDEMPOTENCY_CONFLICT"


class ObservationRegression(ExpansionError):
    code = "OBSERVATION_REGRESSION"


class ObservationAheadOfDesired(ExpansionError):
    code = "OBSERVATION_AHEAD_OF_DESIRED"


@dataclass(frozen=True, slots=True)
class VmCpuState:
    """Authoritative control-plane view of one VM's CPU expansion state.

    ``observed_vcpus`` is what the hypervisor/guest path has confirmed online.
    ``desired_vcpus`` is the accepted target.  They are intentionally separate
    so a request is never misreported as completed before the backend confirms it.
    """

    vm_id: str
    observed_vcpus: int
    desired_vcpus: int
    max_vcpus: int
    host_capacity_vcpus: int
    acpi_hotplug_supported: bool = True
    guest_hotplug_supported: bool = True
    expansion_enabled: bool = True
    generation: int = 0

    def __post_init__(self) -> None:
        _require_identifier(self.vm_id, "vm_id")
        observed = _require_int(self.observed_vcpus, "observed_vcpus", minimum=1, maximum=MAX_VCPU_SANITY_LIMIT)
        desired = _require_int(self.desired_vcpus, "desired_vcpus", minimum=1, maximum=MAX_VCPU_SANITY_LIMIT)
        guest_max = _require_int(self.max_vcpus, "max_vcpus", minimum=1, maximum=MAX_VCPU_SANITY_LIMIT)
        host_max = _require_int(self.host_capacity_vcpus, "host_capacity_vcpus", minimum=1, maximum=MAX_VCPU_SANITY_LIMIT)
        _require_int(self.generation, "generation", minimum=0)
        for name in ("acpi_hotplug_supported", "guest_hotplug_supported", "expansion_enabled"):
            if not isinstance(getattr(self, name), bool):
                raise InvalidRequest(f"{name} must be boolean", field=name)
        if observed > desired:
            raise InvalidRequest("observed_vcpus must not exceed desired_vcpus", field="observed_vcpus")
        if desired > guest_max:
            raise InvalidRequest("desired_vcpus must not exceed max_vcpus", field="desired_vcpus")
        if observed > host_max:
            raise InvalidRequest(
                "observed_vcpus must not exceed host_capacity_vcpus",
                field="observed_vcpus",
            )

    @property
    def pending_vcpus(self) -> int:
        return self.desired_vcpus - self.observed_vcpus

    @property
    def converged(self) -> bool:
        return self.pending_vcpus == 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": STATUS_SCHEMA,
            "vm_id": self.vm_id,
            "observed_vcpus": self.observed_vcpus,
            "desired_vcpus": self.desired_vcpus,
            "pending_vcpus": self.pending_vcpus,
            "max_vcpus": self.max_vcpus,
            "host_capacity_vcpus": self.host_capacity_vcpus,
            "acpi_hotplug_supported": self.acpi_hotplug_supported,
            "guest_hotplug_supported": self.guest_hotplug_supported,
            "expansion_enabled": self.expansion_enabled,
            "generation": self.generation,
            "converged": self.converged,
        }


@dataclass(frozen=True, slots=True)
class ExpansionResult:
    request_id: str
    vm_id: str
    previous_desired_vcpus: int
    target_vcpus: int
    added_vcpus: int
    generation: int
    status: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": RESULT_SCHEMA,
            "request_id": self.request_id,
            "vm_id": self.vm_id,
            "previous_desired_vcpus": self.previous_desired_vcpus,
            "target_vcpus": self.target_vcpus,
            "added_vcpus": self.added_vcpus,
            "generation": self.generation,
            "status": self.status,
        }


class CpuExpansionController:
    """Thread-safe, bounded-memory reference controller for one VM.

    The controller is intentionally backend-agnostic. ``request_expansion``
    records a desired target after policy validation. ``record_observation``
    records backend progress after the ACPI/hypervisor/guest path confirms it.
    """

    def __init__(self, state: VmCpuState, *, replay_cache_size: int = 256) -> None:
        if isinstance(replay_cache_size, bool) or not isinstance(replay_cache_size, int) or replay_cache_size < 1:
            raise InvalidRequest("replay_cache_size must be a positive integer", field="replay_cache_size")
        if replay_cache_size > 65_536:
            raise InvalidRequest("replay_cache_size is unreasonably large", field="replay_cache_size")
        self._state = state
        self._replay_cache_size = replay_cache_size
        self._replays: OrderedDict[str, tuple[int, int | None, ExpansionResult]] = OrderedDict()
        self._lock = RLock()

    def snapshot(self) -> VmCpuState:
        with self._lock:
            return self._state

    def request_expansion(
        self,
        request_id: str,
        target_vcpus: int,
        *,
        expected_generation: int | None = None,
    ) -> ExpansionResult:
        request_id = _require_identifier(request_id, "request_id")
        target = _require_int(target_vcpus, "target_vcpus", minimum=1, maximum=MAX_VCPU_SANITY_LIMIT)
        if expected_generation is not None:
            expected_generation = _require_int(expected_generation, "expected_generation", minimum=0)

        with self._lock:
            replay = self._replays.get(request_id)
            if replay is not None:
                old_target, old_expected, old_result = replay
                if old_target != target or old_expected != expected_generation:
                    raise IdempotencyConflict(
                        "request_id was already used for different request parameters",
                        request_id=request_id,
                    )
                self._replays.move_to_end(request_id)
                return old_result

            state = self._state
            if expected_generation is not None and expected_generation != state.generation:
                raise StaleGeneration(
                    f"expected generation {expected_generation}, current generation is {state.generation}",
                    expected_generation=expected_generation,
                    current_generation=state.generation,
                )
            if target < state.desired_vcpus:
                raise ShrinkNotSupported(
                    "legacy expansion path is monotonic and does not hot-unplug CPUs",
                    desired_vcpus=state.desired_vcpus,
                    target_vcpus=target,
                )
            if target > state.max_vcpus:
                raise GuestLimitExceeded(
                    f"target {target} exceeds VM maximum {state.max_vcpus}",
                    target_vcpus=target,
                    max_vcpus=state.max_vcpus,
                )
            if target > state.host_capacity_vcpus:
                raise HostCapacityExceeded(
                    f"target {target} exceeds host capacity {state.host_capacity_vcpus}",
                    target_vcpus=target,
                    host_capacity_vcpus=state.host_capacity_vcpus,
                )

            changed = target > state.desired_vcpus
            if changed:
                if not state.expansion_enabled:
                    raise ExpansionDisabled("CPU expansion is administratively disabled", vm_id=state.vm_id)
                if not state.acpi_hotplug_supported or not state.guest_hotplug_supported:
                    raise HotplugUnsupported(
                        "both hypervisor ACPI hot-plug and guest CPU hot-plug support are required",
                        acpi_hotplug_supported=state.acpi_hotplug_supported,
                        guest_hotplug_supported=state.guest_hotplug_supported,
                    )

            previous = state.desired_vcpus
            new_generation = state.generation + (1 if changed else 0)
            if changed:
                self._state = replace(state, desired_vcpus=target, generation=new_generation)

            result = ExpansionResult(
                request_id=request_id,
                vm_id=state.vm_id,
                previous_desired_vcpus=previous,
                target_vcpus=target,
                added_vcpus=target - previous,
                generation=new_generation,
                status="accepted" if changed else "noop",
            )
            self._remember(request_id, target, expected_generation, result)
            return result

    def record_observation(self, observed_vcpus: int) -> VmCpuState:
        """Record backend/guest progress without pretending partial progress is complete."""
        observed = _require_int(observed_vcpus, "observed_vcpus", minimum=1, maximum=MAX_VCPU_SANITY_LIMIT)
        with self._lock:
            state = self._state
            if observed < state.observed_vcpus:
                raise ObservationRegression(
                    "observed CPU count regressed; CPU hot-unplug is outside INV-34",
                    previous_observed_vcpus=state.observed_vcpus,
                    observed_vcpus=observed,
                )
            if observed > state.desired_vcpus:
                raise ObservationAheadOfDesired(
                    "observed CPU count exceeds the accepted desired target",
                    desired_vcpus=state.desired_vcpus,
                    observed_vcpus=observed,
                )
            if observed == state.observed_vcpus:
                return state
            self._state = replace(state, observed_vcpus=observed, generation=state.generation + 1)
            return self._state

    def update_host_capacity(self, host_capacity_vcpus: int) -> VmCpuState:
        """Update discovered capacity, refusing values that invalidate accepted state."""
        capacity = _require_int(host_capacity_vcpus, "host_capacity_vcpus", minimum=1, maximum=MAX_VCPU_SANITY_LIMIT)
        with self._lock:
            state = self._state
            if capacity < state.observed_vcpus:
                raise InvalidRequest(
                    "host capacity cannot be lower than the already observed online CPU count",
                    field="host_capacity_vcpus",
                    observed_vcpus=state.observed_vcpus,
                )
            if capacity == state.host_capacity_vcpus:
                return state
            self._state = replace(state, host_capacity_vcpus=capacity, generation=state.generation + 1)
            return self._state

    def _remember(
        self,
        request_id: str,
        target_vcpus: int,
        expected_generation: int | None,
        result: ExpansionResult,
    ) -> None:
        self._replays[request_id] = (target_vcpus, expected_generation, result)
        self._replays.move_to_end(request_id)
        while len(self._replays) > self._replay_cache_size:
            self._replays.popitem(last=False)
