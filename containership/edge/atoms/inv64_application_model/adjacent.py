"""Adjacent-layer contracts and deterministic emulators for INV-10, INV-63, INV-65, INV-66 (MC-10; C030, C083).

**These are emulators, not the real components.** They implement the handoff
contracts INV-64 depends on so the boundary behaviour (version negotiation,
rejection propagation, deadlines, no partial activation, tenant/trace
propagation) is executable in CI. Certification against the real adjacent
implementations is a separate, currently BLOCKED profile (their code is not in
this archive); the release gate reports that explicitly.

Responsibility split (INTERFACES.md §4):

* INV-10 composition — owns what a component reference *is*; INV-64 asks it to
  resolve each ``components[].type`` (``PK_COMPOSE_RESOLVE/1``).
* INV-65 capability providers — owns provider implementations and grants;
  INV-64 asks it to bind each declared provider for the tenant (``PK_PROVIDER_BIND/1``).
* INV-66 enterprise control plane — owns guardrail policy; INV-64 submits the
  canonical manifest for a verdict (``PK_GUARDRAIL/1``).
* INV-63 deployment manager — owns running; INV-64 hands off the *validated
  canonical* manifest (``PK_DEPLOY_HANDOFF/1``) and nothing else.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from .errors import Inv64Error
from .manifest import canonical, canonical_document

CONTRACTS = {
    "INV-10": {"contract": "PK_COMPOSE_RESOLVE", "supported": (1, 2)},
    "INV-65": {"contract": "PK_PROVIDER_BIND", "supported": (1, 1)},
    "INV-66": {"contract": "PK_GUARDRAIL", "supported": (1, 2)},
    "INV-63": {"contract": "PK_DEPLOY_HANDOFF", "supported": (1, 1)},
}


class AdjacentError(Inv64Error):
    pass


@dataclass
class Faults:
    """Fault injection knobs shared by every emulator."""

    unavailable: bool = False
    latency_s: float = 0.0
    malformed: bool = False
    version: int | None = None     # advertised contract version override


@dataclass
class _Emu:
    element: str
    faults: Faults = field(default_factory=Faults)
    sleep: Callable[[float], None] = time.sleep
    calls: list = field(default_factory=list)

    def version(self) -> int:
        return self.faults.version if self.faults.version is not None else CONTRACTS[self.element]["supported"][1]

    def _enter(self, deadline, payload):
        self.calls.append(payload)
        if self.faults.unavailable:
            raise AdjacentError("admission.overloaded", details={"dependency": self.element, "reason": "unavailable"})
        if self.faults.latency_s:
            self.sleep(self.faults.latency_s)
        if deadline is not None:
            deadline.check()


@dataclass
class CompositionEmulator(_Emu):  # INV-10
    element: str = "INV-10"
    catalog: frozenset = frozenset({"web", "worker", "job"})

    def resolve(self, types: list[str], *, deadline=None, ctx=None) -> dict:
        self._enter(deadline, {"types": types, "ctx": ctx})
        if self.faults.malformed:
            return {"garbage": True}
        return {"contract": "PK_COMPOSE_RESOLVE/1", "unresolved": sorted({t for t in types if t not in self.catalog})}


@dataclass
class ProviderEmulator(_Emu):  # INV-65
    element: str = "INV-65"
    grants: dict = field(default_factory=dict)  # tenant -> set(provider names)
    bound: dict = field(default_factory=dict)

    def bind(self, tenant: str, providers: list[str], *, deadline=None, ctx=None) -> dict:
        self._enter(deadline, {"tenant": tenant, "providers": providers, "ctx": ctx})
        if self.faults.malformed:
            return {}
        denied = sorted(p for p in providers if p not in self.grants.get(tenant, set()))
        if denied:
            return {"contract": "PK_PROVIDER_BIND/1", "bound": [], "denied": denied}
        self.bound.setdefault(tenant, set()).update(providers)
        return {"contract": "PK_PROVIDER_BIND/1", "bound": sorted(providers), "denied": []}

    def unbind(self, tenant: str, providers: list[str]) -> None:
        self.bound.get(tenant, set()).difference_update(providers)


@dataclass
class ControlPlaneEmulator(_Emu):  # INV-66
    element: str = "INV-66"
    forbidden_traits: frozenset = frozenset({"privileged"})
    max_components: int = 100

    def guardrail(self, tenant: str, digest: str, manifest: dict, *, deadline=None, ctx=None) -> dict:
        self._enter(deadline, {"tenant": tenant, "digest": digest, "ctx": ctx})
        if self.faults.malformed:
            return {"verdict": 7}
        reasons = []
        if len(manifest.get("components", [])) > self.max_components:
            reasons.append("guardrail.too_many_components")
        if any(t.get("type") in self.forbidden_traits for t in manifest.get("traits", [])):
            reasons.append("guardrail.forbidden_trait")
        return {"contract": "PK_GUARDRAIL/1", "verdict": "deny" if reasons else "allow", "reasons": reasons}


@dataclass
class DeploymentEmulator(_Emu):  # INV-63
    element: str = "INV-63"
    deployed: dict = field(default_factory=dict)

    def handoff(self, envelope: dict, *, deadline=None) -> dict:
        self._enter(deadline, envelope)
        if self.faults.malformed:
            return {"ok": "maybe"}
        # the receiving layer re-derives identity from the canonical bytes (integrity at handoff)
        import hashlib
        if hashlib.sha256(envelope["canonical_document"].encode()).hexdigest() != envelope["digest"]:
            return {"contract": "PK_DEPLOY_HANDOFF/1", "accepted": False, "reason": "digest-mismatch"}
        if not envelope.get("tenant") or not envelope.get("traceparent") or not envelope.get("correlation_id"):
            return {"contract": "PK_DEPLOY_HANDOFF/1", "accepted": False, "reason": "missing-context"}
        dep = f"dep-{envelope['digest'][:12]}"
        self.deployed[(envelope["tenant"], envelope["digest"])] = dep
        return {"contract": "PK_DEPLOY_HANDOFF/1", "accepted": True, "deployment": dep}


def _check_version(emu: _Emu) -> None:
    lo, hi = CONTRACTS[emu.element]["supported"]
    v = emu.version()
    if not lo <= v <= hi:
        raise AdjacentError("version.unsupported", details={"dependency": emu.element, "offered": v,
                                                            "supported": [lo, hi]})


def _shape(emu: _Emu, resp: dict, *keys) -> dict:
    if not isinstance(resp, dict) or not all(k in resp for k in keys):
        raise AdjacentError("internal", details={"dependency": emu.element, "reason": "malformed response"})
    return resp


@dataclass
class Adjacent:
    inv10: CompositionEmulator
    inv65: ProviderEmulator
    inv66: ControlPlaneEmulator
    inv63: DeploymentEmulator

    def handoff(self, manifest: dict, *, tenant: str, correlation_id: str, traceparent: str, deadline=None) -> dict:
        """All-or-nothing: resolve -> guardrail -> bind -> deploy; on any failure, unbind and refuse."""
        for emu in (self.inv10, self.inv66, self.inv65, self.inv63):
            _check_version(emu)   # negotiate before any semantic call
        ctx = {"tenant": tenant, "correlation_id": correlation_id, "traceparent": traceparent}
        digest = canonical(manifest)
        types = [c.get("type", "web") for c in manifest.get("components", [])]
        r = _shape(self.inv10, self.inv10.resolve(types, deadline=deadline, ctx=ctx), "contract", "unresolved")
        if r["unresolved"]:
            raise AdjacentError("manifest.invalid", details={"dependency": "INV-10", "unresolved": r["unresolved"]})
        g = _shape(self.inv66, self.inv66.guardrail(tenant, digest, manifest, deadline=deadline, ctx=ctx),
                   "contract", "verdict", "reasons")
        if g["verdict"] not in ("allow", "deny"):
            raise AdjacentError("internal", details={"dependency": "INV-66", "reason": "malformed verdict"})
        if g["verdict"] != "allow":
            raise AdjacentError("authz.denied", details={"dependency": "INV-66", "reasons": g["reasons"]})
        providers = [p["name"] for p in manifest.get("providers", [])]
        b = _shape(self.inv65, self.inv65.bind(tenant, providers, deadline=deadline, ctx=ctx), "contract", "bound", "denied")
        if b["denied"]:
            raise AdjacentError("authz.denied", details={"dependency": "INV-65", "denied": b["denied"]})
        try:
            env = {"contract": "PK_DEPLOY_HANDOFF/1", "tenant": tenant, "digest": digest,
                   "canonical_document": canonical_document(manifest).decode(), "correlation_id": correlation_id,
                   "traceparent": traceparent}
            d = _shape(self.inv63, self.inv63.handoff(env, deadline=deadline), "contract", "accepted")
            if not d["accepted"]:
                raise AdjacentError("internal", details={"dependency": "INV-63", "reason": d.get("reason")})
        except Exception:
            self.inv65.unbind(tenant, providers)   # no partial activation
            raise
        return {"digest": digest, "deployment": d["deployment"], "bound": b["bound"]}


def default_adjacent(**faults) -> Adjacent:
    return Adjacent(CompositionEmulator(faults=faults.get("inv10", Faults())),
                    ProviderEmulator(faults=faults.get("inv65", Faults()), grants={"acme": {"kv", "queue"}}),
                    ControlPlaneEmulator(faults=faults.get("inv66", Faults())),
                    DeploymentEmulator(faults=faults.get("inv63", Faults())))
