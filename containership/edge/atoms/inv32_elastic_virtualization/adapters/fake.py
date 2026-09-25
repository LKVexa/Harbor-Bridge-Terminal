"""Deterministic fake hypervisor used as the reference adapter and for contract/fault tests (WS 1, 10, 14).

Faults are injected by name and consumed once (or persist when ``sticky``):

* ``refuse``            guest refuses balloon reclaim (memory unchanged)
* ``partial``           memory change applies only half the delta (block aligned);
                        vCPU change applies one step only
* ``timeout``           provider applies the change but never confirms (raises ProviderTimeout)
* ``timeout_noapply``   provider times out without applying
* ``unavailable``       transient RPC failure before anything is applied
* ``restart``           provider restarts: state kept, request lost, raises ProviderUnavailable
* ``lie_floor``         provider reports a value below the requested floor (invariant violation)
* ``capacity_untrusted`` host capacity reported as untrusted
* ``external_change``   another actor changes the guest right before our mutation (stale CAS)
"""
from __future__ import annotations

import threading
import time
from dataclasses import replace
from typing import Any
from uuid import uuid4

from .. import errors as E
from .base import (
    Capabilities,
    GuestLifecycle,
    HostCapacity,
    HypervisorAdapter,
    LiveGuest,
    ProviderResult,
    ProviderStatus,
)


class FakeHypervisor(HypervisorAdapter):
    def __init__(self, total_mib: int = 65536, *, overhead_mib: int = 512, reserved_pool_mib: int = 0,
                 fragmentation_mib: int = 0, block_mib: int = 128, provider_version: str = "fake-hyperflux-1.0",
                 latency_s: float = 0.0, fencing: bool = True) -> None:
        self._lock = threading.RLock()
        self._guests: dict[str, LiveGuest] = {}
        self._caps = Capabilities(provider="fake-hyperflux", provider_version=provider_version,
                                  memory_block_mib=block_mib, free_page_reporting=True,
                                  fencing_tokens=fencing, idempotency_keys=True)
        self._cap = HostCapacity(total_mib, overhead_mib, reserved_pool_mib, fragmentation_mib, True, time.time())
        self._faults: dict[str, int | None] = {}
        self._seen_keys: dict[str, ProviderResult] = {}
        self._max_fence = 0
        self._free: dict[str, int] = {}
        self._latency = latency_s
        self._draining = False
        self.calls: list[tuple[str, str, int]] = []  # (kind, guest, target) actually applied

    # ------------------------------------------------------------- test controls
    def inject(self, fault: str, times: int | None = 1) -> None:
        with self._lock:
            self._faults[fault] = times

    def _take(self, fault: str) -> bool:
        with self._lock:
            if fault not in self._faults:
                return False
            n = self._faults[fault]
            if n is None:
                return True
            if n <= 1:
                del self._faults[fault]
            else:
                self._faults[fault] = n - 1
            return True

    def create_guest(self, guest_id: str, tenant: str, memory_mib: int, vcpus: int = 1, *,
                     lifecycle: GuestLifecycle = GuestLifecycle.RUNNING, non_balloonable_mib: int = 0,
                     min_boot_vcpus: int = 1) -> LiveGuest:
        with self._lock:
            g = LiveGuest(guest_id, tenant, uuid4().hex, lifecycle, memory_mib, vcpus, 1,
                          non_balloonable_mib, min_boot_vcpus)
            self._guests[guest_id] = g
            return g

    def recreate_guest(self, guest_id: str, tenant: str) -> LiveGuest:
        """Destroy and recreate with the same ID (identifier-reuse attack)."""
        with self._lock:
            old = self._guests[guest_id]
            return self.create_guest(guest_id, tenant, old.memory_mib, old.vcpus)

    def set_lifecycle(self, guest_id: str, state: GuestLifecycle) -> None:
        with self._lock:
            g = self._guests[guest_id]
            self._guests[guest_id] = replace(g, lifecycle=state, state_version=g.state_version + 1)

    def external_resize(self, guest_id: str, memory_mib: int) -> None:
        with self._lock:
            g = self._guests[guest_id]
            self._guests[guest_id] = replace(g, memory_mib=memory_mib, state_version=g.state_version + 1)

    def bump_capabilities(self, **changes: Any) -> None:
        with self._lock:
            self._caps = replace(self._caps, generation=self._caps.generation + 1, **changes)

    def set_free_pages(self, guest_id: str, mib: int) -> None:
        self._free[guest_id] = mib

    # ------------------------------------------------------------- adapter API
    def capabilities(self) -> Capabilities:
        return self._caps

    def health(self) -> dict[str, Any]:
        if "unavailable" in self._faults and self._faults["unavailable"] is None:
            return {"ok": False, "reason": "unavailable"}
        return {"ok": not self._draining, "provider_version": self._caps.provider_version}

    def host_capacity(self) -> HostCapacity:
        if self._take("capacity_untrusted"):
            return replace(self._cap, trusted=False)
        return self._cap

    def list_guests(self) -> list[LiveGuest]:
        with self._lock:
            return list(self._guests.values())

    def get_guest(self, guest_id: str) -> LiveGuest:
        with self._lock:
            if self._take("unavailable"):
                raise E.ProviderUnavailable("provider RPC failed", _raw="ECONNRESET /var/run/hyperflux.sock")
            try:
                return self._guests[guest_id]
            except KeyError:
                raise E.IdentityMismatch("guest not present at provider", guest=guest_id) from None

    def free_pages(self, guest_id: str) -> int | None:
        return self._free.get(guest_id)

    def drain(self) -> None:
        self._draining = True

    def _mutate(self, kind: str, guest_id: str, target: int, expected_version: int, incarnation: str,
                idempotency_key: str, fencing_token: int, deadline: float) -> ProviderResult:
        t0 = time.perf_counter()
        if self._latency:
            time.sleep(self._latency)
        with self._lock:
            if self._draining:
                raise E.ProviderUnavailable("provider draining")
            if idempotency_key in self._seen_keys:
                return self._seen_keys[idempotency_key]
            if self._take("unavailable"):
                raise E.ProviderUnavailable("provider RPC failed", _raw="token=abc123 at /var/lib/hf")
            if self._take("restart"):
                raise E.ProviderUnavailable("provider restarted; request lost")
            if self._caps.fencing_tokens:
                if fencing_token < self._max_fence:
                    raise E.FencingRejected("stale fencing token", token=fencing_token, current=self._max_fence)
                self._max_fence = fencing_token
            if self._take("external_change"):
                g0 = self._guests[guest_id]
                self._guests[guest_id] = replace(g0, state_version=g0.state_version + 1)
            g = self._guests.get(guest_id)
            if g is None or g.incarnation != incarnation:
                raise E.IdentityMismatch("guest incarnation changed", guest=guest_id)
            if g.state_version != expected_version:
                raise E.StaleExpectedState("provider state version moved", expected=expected_version,
                                           actual=g.state_version)
            if time.monotonic() > deadline:
                raise E.DeadlineExceeded("deadline passed before provider call")
            current = g.memory_mib if kind == "memory" else g.vcpus
            status = ProviderStatus.APPLIED
            applied = target
            if kind == "memory" and target < current and self._take("refuse"):
                applied, status = current, ProviderStatus.REFUSED
            elif self._take("partial"):
                if kind == "memory":
                    blk = self._caps.memory_block_mib
                    half = (target - current) // 2
                    applied = current + (half // blk) * blk
                else:
                    applied = current + (1 if target > current else -1)
                status = ProviderStatus.PARTIAL if applied != target else ProviderStatus.APPLIED
            if self._take("lie_floor"):
                applied = 1 if kind == "memory" else applied
            no_apply = self._take("timeout_noapply")
            if not no_apply:
                if kind == "memory":
                    self._guests[guest_id] = replace(g, memory_mib=applied, state_version=g.state_version + 1)
                else:
                    self._guests[guest_id] = replace(g, vcpus=applied, state_version=g.state_version + 1)
                self.calls.append((kind, guest_id, applied))
            if no_apply or self._take("timeout"):
                raise E.ProviderTimeout("provider did not confirm before deadline", guest=guest_id)
            result = ProviderResult(uuid4().hex, status, applied, self._guests[guest_id].state_version,
                                    time.perf_counter() - t0, {"provider": "fake"})
            self._seen_keys[idempotency_key] = result
            return result

    def set_memory(self, guest_id, target_mib, *, expected_version, incarnation, idempotency_key,
                   fencing_token, deadline) -> ProviderResult:
        return self._mutate("memory", guest_id, target_mib, expected_version, incarnation,
                            idempotency_key, fencing_token, deadline)

    def set_vcpus(self, guest_id, target, *, expected_version, incarnation, idempotency_key,
                  fencing_token, deadline) -> ProviderResult:
        return self._mutate("vcpu", guest_id, target, expected_version, incarnation,
                            idempotency_key, fencing_token, deadline)
