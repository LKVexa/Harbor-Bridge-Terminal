"""The PK_WASM_INSTANCE/1 admission path for INV-44 (components 9, 12, 13, 14, 15, 17).

``TenantGateway`` is the production-shaped entry point that the legacy
``Engine.instantiate(output_valid=...)`` Boolean path is superseded by:

    authenticate -> authorize(instantiate) -> tenant match -> admission control
    -> verify receipt against the bytes -> ambient-import check
    -> Engine.instantiate(output_valid=True) -> audit + metrics + explanation

Every step fails closed, every refusal is audited with its structured code,
and a refusal never leaves a half-created instance behind.

Tenant isolation here is *logical* (one engine per tenant, cross-tenant
requests refused, per-tenant instance quotas, per-tenant metric labels). Host
isolation — separate processes/VMs, cache partitioning, kernel interfaces — is
not provable from Python and stays BLOCKED on the Swivel runtime integration.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping

from .audit_log import AuditLog
from .capability import (Authorizer, CapabilityToken, Principal, check_imports)
from .errors import HardeningError, classify
from .observability import Metrics, explain
from .runtime import Engine, Instance
from .wasm_verify import Keyring, verify_receipt


class TenantMismatch(HardeningError):
    code = "WH-TENANT-MISMATCH"


class Overloaded(HardeningError):
    code = "WH-OVERLOADED"


@dataclass
class Admission:
    max_instances: int
    max_inflight: int


class TenantGateway:
    def __init__(self, *, tenant: str, engine: Engine, authorizer: Authorizer, keyring: Keyring,
                 approved_toolchains: Iterable[str], audit: AuditLog, metrics: Metrics,
                 admission: Admission, receipt_max_age_s: int | None = 86_400,
                 clock: Callable[[], float] = time.time) -> None:
        self.tenant = tenant
        self.engine = engine
        self._authz = authorizer
        self._keyring = keyring
        self._approved = frozenset(approved_toolchains)
        self._audit = audit
        self._metrics = metrics
        self._admission = admission
        self._max_age = receipt_max_age_s
        self._clock = clock
        self._lock = threading.Lock()
        self._live: dict[str, Instance] = {}
        self._inflight = 0
        self._reserved: set[str] = set()

    def instantiate(self, principal: Principal, token: CapabilityToken, module_name: str,
                    module_bytes: bytes, receipt: Mapping, *, fuel: int, pages: int = 1) -> Instance:
        checks: dict[str, bool] = {}
        reserved = False
        started = time.perf_counter()
        actor = getattr(principal, "subject", "<unauthenticated>")
        with self._lock:
            if self._inflight >= self._admission.max_inflight:
                return self._refuse(Overloaded("inflight limit reached"), actor, module_name, checks)
            self._inflight += 1
        try:
            self._authz.authorize(principal, token, "instantiate"); checks["authorized"] = True
            if principal.tenant != self.tenant:
                raise TenantMismatch("principal tenant differs from engine tenant",
                                     engine_tenant=self.tenant, principal_tenant=principal.tenant)
            checks["tenant_match"] = True
            with self._lock:
                if module_name in self._live or module_name in self._reserved:
                    raise HardeningError("instance name already live (duplicate execution refused)",
                                         code="WH-INVALID-ARGUMENT", module=module_name)
                if len(self._live) + len(self._reserved) >= self._admission.max_instances:
                    raise Overloaded("tenant instance quota reached")
                self._reserved.add(module_name)  # closes the check-then-register race
                reserved = True
            checks["admitted"] = True
            summary = verify_receipt(module_bytes, receipt, keyring=self._keyring,
                                     approved_toolchains=self._approved,
                                     max_age_s=self._max_age, now=int(self._clock()))
            checks["receipt_verified"] = True
            check_imports(summary.imports, token); checks["imports_granted"] = True
            if summary.memory_max_pages is None or summary.memory_max_pages > self.engine.memory_page_ceiling:
                # A module without a declared max could request growth the engine
                # refuses later; admit only modules whose own max fits the ceiling.
                from .runtime import MemoryCeiling
                raise MemoryCeiling(f"{module_name}: module memory max "
                                    f"{summary.memory_max_pages} not within ceiling")
            checks["memory_declared_within_ceiling"] = True
            inst = self.engine.instantiate(module_name, output_valid=True, fuel=fuel, pages=pages)
            checks["engine_hardened"] = True
            # Audit BEFORE the instance becomes live: if the audit sink fails the
            # instance is dropped, so nothing runs without its audit record.
            self._audit.append("instantiate", actor=actor, tenant=self.tenant, outcome="success",
                               module=module_name, sha256=summary.sha256,
                               explanation=explain("admit", reason_code=None, checks=checks))
            with self._lock:
                self._live[module_name] = inst
                self._metrics.set("instances", len(self._live), tenant=self.tenant)
            self._metrics.inc("admissions", tenant=self.tenant)
            self._metrics.observe("instantiate_seconds", time.perf_counter() - started, tenant=self.tenant)
            return inst
        except BaseException as exc:  # noqa: BLE001 — every failure is audited then re-raised
            try:
                self._refuse(exc, actor, module_name, checks, reraise=False)
            except Exception:  # audit sink itself failing must not mask the refusal
                pass
            raise
        finally:
            with self._lock:
                self._inflight -= 1
                if reserved:
                    self._reserved.discard(module_name)

    def release(self, module_name: str) -> None:
        with self._lock:
            self._live.pop(module_name, None)
            self._metrics.set("instances", len(self._live), tenant=self.tenant)

    def _refuse(self, exc: BaseException, actor: str, module: str, checks: dict, *, reraise: bool = True):
        doc = classify(exc)
        counter = {
            "WH-HARDENING-INCOMPLETE": "hardening_refusals",
            "WH-OUTPUT-UNVERIFIED": "verification_failures",
            "WH-OUTPUT-MALFORMED": "verification_failures",
            "WH-RECEIPT-INVALID": "verification_failures",
            "WH-TOOLCHAIN-UNAPPROVED": "verification_failures",
            "WH-MEMORY-CEILING": "memory_growth_refusals",
            "WH-AUTHZ-DENIED": "authz_denials",
            "WH-AUTHN-FAILED": "authz_denials",
            "WH-CAPABILITY-EXPIRED": "authz_denials",
            "WH-AMBIENT-IMPORT": "authz_denials",
            "WH-TENANT-MISMATCH": "tenant_violations",
            "WH-OVERLOADED": "load_shed",
        }.get(doc["code"])
        if counter:
            self._metrics.inc(counter, tenant=self.tenant, code=doc["code"])
        self._audit.append("instantiate", actor=actor, tenant=self.tenant, outcome="refused",
                           module=module, code=doc["code"],
                           explanation=explain("refuse", reason_code=doc["code"], checks=checks))
        if reraise:
            raise exc
