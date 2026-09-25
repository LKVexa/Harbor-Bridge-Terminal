"""Provider registry, discovery and contract/version negotiation (M12).

Registrations are schema-validated, must present an allowlisted implementation
digest (M20) and a lease epoch (M17).  One (contract, site, environment) slot has
exactly one owner at a time: a second instance is refused unless it presents a
strictly higher epoch (takeover), which fences the old owner.
"""
from __future__ import annotations

import threading

from ..errors.mapping import ProviderFault
from ..schemas import SchemaError, check


def _ver(v: str) -> tuple[int, int]:
    a, b = v.split(".")
    return int(a), int(b)


def negotiate(offered: list[str], supported: list[str]) -> str:
    """Highest common version with the same major; else PK_PROVIDER_INCOMPATIBLE."""
    common = set(offered) & set(supported)
    if not common:
        raise ProviderFault("PK_PROVIDER_INCOMPATIBLE", "no mutually supported contract version")
    return max(common, key=_ver)


class ProviderRegistry:
    def __init__(self, trust=None):
        self._slots: dict[tuple, dict] = {}
        self._lock = threading.Lock()
        self.trust = trust  # supply_chain.ArtifactTrust

    def register(self, reg: dict) -> dict:
        try:
            check(reg, "provider_registration")
        except SchemaError as e:
            raise ProviderFault("PK_PROVIDER_INVALID_LINK", f"bad registration: {e}") from None
        if self.trust is not None:
            self.trust.require(reg["contract_id"], reg["implementation_digest"])
        slot = (reg["contract_id"], reg["site"], reg["environment"])
        with self._lock:
            cur = self._slots.get(slot)
            if cur and cur["instance_id"] != reg["instance_id"] and reg["lease_epoch"] <= cur["lease_epoch"]:
                raise ProviderFault("PK_PROVIDER_FENCED", "slot owned by another instance with equal/higher epoch")
            if cur and cur["instance_id"] == reg["instance_id"] and reg["lease_epoch"] < cur["lease_epoch"]:
                raise ProviderFault("PK_PROVIDER_FENCED", "stale epoch for own registration")
            self._slots[slot] = dict(reg)
            return dict(reg)

    def deregister(self, contract_id: str, site: str, environment: str, instance_id: str, epoch: int) -> bool:
        with self._lock:
            cur = self._slots.get((contract_id, site, environment))
            if not cur or cur["instance_id"] != instance_id or cur["lease_epoch"] != epoch:
                return False
            del self._slots[(contract_id, site, environment)]
            return True

    def discover(self, contract_id: str, *, site: str, environment: str, versions: list[str]) -> tuple[dict, str]:
        with self._lock:
            cur = self._slots.get((contract_id, site, environment))
        if cur is None:
            raise ProviderFault("PK_PROVIDER_NO_LINK", "no provider registered for contract in site/environment")
        return dict(cur), negotiate(versions, cur["versions"])

    def all(self) -> list[dict]:
        with self._lock:
            return [dict(v) for v in self._slots.values()]
