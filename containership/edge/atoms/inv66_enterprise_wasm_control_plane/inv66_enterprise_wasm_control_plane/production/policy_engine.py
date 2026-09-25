"""Organisation policy evaluation with deterministic precedence (MC-011, MC-033; C019, C030, C048).

Local rules (``policy.rules`` in the config generation) have three effects:

* ``deny``    — all ``when`` selectors match  -> deny
* ``require`` — tenant/lattice/environment selectors match -> every component image
                must start with ``require_image_prefix`` (e.g. residency: EU registry)
* ``exempt``  — selectors match -> suppress the rules listed in ``targets``

Precedence (MC-011) is fixed and total: class rank
``security(0) > residency(1) > availability(2) > slo(3) > cost(4)``, then
``priority`` descending, then rule id.  An exemption may only suppress rules of
**equal or lower** precedence class than its own: a cost exemption can never lift
a security or residency rule; such an attempt is recorded as
``exemption_refused`` in the explanation, never silently applied.

External engine (GAP-13): :class:`ExternalPolicy` wraps any client returning
``{"allow": bool, "reasons": [...], "policy_version": str}``, pins the expected
``policy_version``, caches positive answers for ``cache_ttl_s``, uses a circuit
breaker, and on unavailability applies ``on_unavailable``: ``deny`` (default;
fail closed) or ``use_cached`` (only a still-fresh cached answer for the
identical input digest).  :class:`HttpPolicyClient` speaks the OPA data API
(``POST /v1/data/<path>`` with ``{"input": ...}``).
"""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from typing import Any, Callable, Optional, Protocol

from .errors import EcpError, reason
from .resilience import CircuitBreaker
from .util import digest_of, now

CLASS_RANK = {"security": 0, "residency": 1, "availability": 2, "slo": 3, "cost": 4}


def _order(r: dict[str, Any]) -> tuple:
    return (CLASS_RANK[r["class"]], -r["priority"], r["id"])


def _selectors_match(when: dict[str, Any], ctx: dict[str, Any]) -> bool:
    for k in ("tenant", "lattice", "environment"):
        if k in when and when[k] != ctx.get(k):
            return False
    return True


def _component_match(when: dict[str, Any], comp: dict[str, Any]) -> bool:
    if "component_name" in when and comp.get("name") != when["component_name"]:
        return False
    if "image_prefix" in when and not str(comp.get("image", "")).startswith(when["image_prefix"]):
        return False
    return True


def evaluate_local(rules: list[dict[str, Any]], ctx: dict[str, Any], components: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rules, key=_order)
    by_id = {r["id"]: r for r in ordered}
    suppressed: dict[str, str] = {}
    refused: list[dict[str, str]] = []
    for r in ordered:
        if r["effect"] == "exempt" and _selectors_match(r["when"], ctx):
            for tid in r.get("targets", []):
                t = by_id.get(tid)
                if t is None:
                    continue
                if CLASS_RANK[t["class"]] >= CLASS_RANK[r["class"]]:
                    suppressed[tid] = r["id"]
                else:
                    refused.append({"exemption": r["id"], "target": tid, "why": "target has higher precedence class"})
    fired: list[dict[str, Any]] = []
    for r in ordered:
        if r["effect"] == "exempt" or r["id"] in suppressed or not _selectors_match(r["when"], ctx):
            continue
        if r["effect"] == "deny":
            hits = [c.get("name") for c in components if _component_match(r["when"], c)]
            if hits:
                fired.append({"rule": r["id"], "class": r["class"], "components": hits[:32], "message": r["message"]})
        elif r["effect"] == "require":
            prefix = r.get("require_image_prefix", "")
            bad = [c.get("name") for c in components
                   if _component_match({k: v for k, v in r["when"].items() if k == "component_name"}, c)
                   and not str(c.get("image", "")).startswith(prefix)]
            if bad:
                fired.append({"rule": r["id"], "class": r["class"], "components": bad[:32], "message": r["message"]})
    return {"allow": not fired, "fired": fired, "suppressed": suppressed, "exemption_refused": refused,
            "order": [r["id"] for r in ordered]}


class PolicyClient(Protocol):
    def evaluate(self, payload: dict[str, Any], timeout_s: float, headers: dict[str, str]) -> dict[str, Any]: ...


class HttpPolicyClient:
    def __init__(self, endpoint: str):
        from .adapters import require_http_url
        self.endpoint = require_http_url(endpoint, "policy engine")

    def evaluate(self, payload: dict[str, Any], timeout_s: float, headers: dict[str, str]) -> dict[str, Any]:
        req = urllib.request.Request(self.endpoint, data=json.dumps({"input": payload}).encode(), method="POST",  # noqa: S310
                                     headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310 - scheme checked in __init__
                body = json.loads(resp.read(1_000_000))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise EcpError("ECP_DEPENDENCY_UNAVAILABLE", "policy engine unreachable", dependency="policy") from None
        result = body.get("result", body) if isinstance(body, dict) else None
        if not isinstance(result, dict) or not isinstance(result.get("allow"), bool):
            raise EcpError("ECP_DEPENDENCY_UNAVAILABLE", "policy engine returned malformed result", dependency="policy")
        return result


class ExternalPolicy:
    def __init__(self, client: PolicyClient, *, expected_version: Optional[str], cache_ttl_s: float = 30.0,
                 on_unavailable: str = "deny", timeout_s: float = 0.5, clock: Callable[[], float] = now,
                 breaker: Optional[CircuitBreaker] = None):
        self.client = client
        self.expected_version = expected_version
        self.ttl = cache_ttl_s
        self.on_unavailable = on_unavailable
        self.timeout = timeout_s
        self.clock = clock
        self.breaker = breaker or CircuitBreaker("policy", clock=clock)
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def evaluate(self, payload: dict[str, Any], headers: Optional[dict[str, str]] = None) -> dict[str, Any]:
        key = digest_of(payload)
        t = self.clock()
        try:
            result = self.breaker.call(lambda: self.client.evaluate(payload, self.timeout, headers or {}))
        except EcpError as e:
            if e.spec.category != "dependency":
                raise
            with self._lock:
                hit = self._cache.get(key)
            if self.on_unavailable == "use_cached" and hit and t - hit[0] <= self.ttl:
                return {**hit[1], "source": "cache", "degraded": True}
            return {"allow": False, "source": "fail-closed", "degraded": True,
                    "reasons": [reason("ECP_DEPENDENCY_UNAVAILABLE", "policy engine unavailable; denied",
                                       dependency="policy")]}
        version = result.get("policy_version")
        if self.expected_version is not None and version != self.expected_version:
            return {"allow": False, "source": "version-mismatch",
                    "reasons": [reason("ECP_POLICY_DENIED", "policy engine version not pinned version",
                                       expected_version=self.expected_version, observed_version=str(version)[:64])]}
        out = {"allow": result["allow"], "source": "live", "policy_version": version,
               "reasons": [reason("ECP_POLICY_DENIED", str(m)[:256]) for m in result.get("reasons", [])][:32]}
        if out["allow"]:
            with self._lock:
                self._cache[key] = (t, out)
                if len(self._cache) > 10_000:
                    self._cache.pop(next(iter(self._cache)))
        return out
