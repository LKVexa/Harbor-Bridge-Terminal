"""Dependency-free runtime logic for INV-58.

This module deliberately has no ``pk_core`` dependency so the security- and
retry-critical logic can be unit-tested in isolation.  ``component.py`` adapts
these primitives to the broader Post-Kubernetes component framework.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Iterable
import re
from urllib.parse import urlsplit

MAX_ROUTE_LENGTH = 512
MAX_IDENTITY_LENGTH = 2048
DEFAULT_MAX_FLAGS = 1024
DEFAULT_MAX_DESTINATIONS = 10_000
DEFAULT_MAX_ROUTES = 10_000
_TRUST_DOMAIN_RE = re.compile(r"^[A-Za-z0-9._~-]+$")
# SPIFFE ID spec: path segments use only letters, digits, '.', '-' and '_'.
_SPIFFE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9._-]+$")


class Unmappable(ValueError):
    """Raised when a mesh certificate identity cannot be mapped safely."""


def _positive_int(value: int, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{what} must be a positive integer, got {value!r}")
    return value


def _token(value: str, what: str, *, max_length: int = MAX_ROUTE_LENGTH) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{what} must be a string, got {type(value).__name__}")
    if not value or value != value.strip():
        raise ValueError(f"{what} must be non-empty and must not have surrounding whitespace")
    if len(value) > max_length:
        raise ValueError(f"{what} exceeds the {max_length}-character limit")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise ValueError(f"{what} must not contain control characters")
    return value


def effective_attempts(app_attempts: int, mesh_attempts: int) -> int:
    """Return the multiplicative attempt count produced by two retry layers."""
    _positive_int(app_attempts, "app_attempts")
    _positive_int(mesh_attempts, "mesh_attempts")
    return app_attempts * mesh_attempts


def reconcile(route: str, app_attempts: int, mesh_attempts: int, budget: int = 3) -> dict:
    """Reconcile retries so no more than one layer retries and budget is bounded.

    The app layer is preferred when both layers request retries because it can
    carry application idempotency context.  If only the mesh requests retries,
    the mesh retains ownership.  ``budget == 1`` disables retries everywhere.

    The original public dictionary keys (``route``, ``owner``, ``app``,
    ``mesh``) are preserved; additive fields expose the effective budget and
    decision reason for observability.
    """
    route = _token(route, "route")
    _positive_int(app_attempts, "app_attempts")
    _positive_int(mesh_attempts, "mesh_attempts")
    _positive_int(budget, "budget")

    if budget == 1:
        owner, app, mesh, reason = "none", 1, 1, "budget_disables_retries"
    elif app_attempts > 1:
        owner = "app"
        app = min(app_attempts, budget)
        mesh = 1
        reason = "app_preferred_for_idempotency" if mesh_attempts > 1 else "app_only_retry_request"
    elif mesh_attempts > 1:
        owner = "mesh"
        app = 1
        mesh = min(mesh_attempts, budget)
        reason = "mesh_only_retry_request"
    else:
        owner, app, mesh, reason = "none", 1, 1, "no_retry_requested"

    total = effective_attempts(app, mesh)
    if total > budget:  # defensive invariant; should be unreachable
        raise RuntimeError(f"reconciled attempts {total} exceed budget {budget}")
    if app > 1 and mesh > 1:  # defensive invariant; should be unreachable
        raise RuntimeError("retry ownership is duplicated across app and mesh")

    return {
        "route": route,
        "owner": owner,
        "app": app,
        "mesh": mesh,
        "budget": budget,
        "effective_attempts": total,
        "reason": reason,
    }


def map_identity(san: str, trust_domain: str) -> str:
    """Map a strict SPIFFE SAN in ``trust_domain`` into a runtime identity.

    Ambiguous URI forms are rejected rather than normalized.  In particular,
    user-info, ports, query/fragment components, dot/empty path segments,
    percent-encoding, whitespace, and control characters fail closed.
    """
    try:
        san = _token(san, "san", max_length=MAX_IDENTITY_LENGTH)
        trust_domain = _token(trust_domain, "trust_domain", max_length=255)
    except ValueError as exc:
        raise Unmappable(str(exc)) from exc

    if not _TRUST_DOMAIN_RE.fullmatch(trust_domain):
        raise Unmappable(f"invalid trust domain {trust_domain!r}")
    if trust_domain.startswith(".") or trust_domain.endswith(".") or ".." in trust_domain:
        raise Unmappable(f"invalid trust domain {trust_domain!r}")

    try:
        parts = urlsplit(san)
    except ValueError as exc:
        raise Unmappable(f"{san!r} is not a valid SPIFFE URI") from exc

    if not san.startswith("spiffe://"):
        # urlsplit lower-cases the scheme; refuse rather than normalise (v4.3.0 fuzz finding)
        raise Unmappable(f"{san!r} is not a SPIFFE identity (scheme must be lowercase 'spiffe')")
    if parts.scheme != "spiffe":
        raise Unmappable(f"{san!r} is not a SPIFFE identity")
    if parts.netloc != trust_domain:
        raise Unmappable(f"{san!r} is not in trust domain {trust_domain!r}")
    if parts.query or parts.fragment or "?" in san or "#" in san:
        # an *empty* query/fragment ("...?", "...#") is silently dropped by urlsplit (v4.3.0 fuzz finding)
        raise Unmappable("SPIFFE identity must not contain query or fragment data")
    if not parts.path or parts.path == "/":
        raise Unmappable("SPIFFE workload path must be non-empty")
    if "%" in parts.path or "\\" in parts.path:
        raise Unmappable("percent-encoded or backslash SPIFFE paths are refused to avoid identity ambiguity")

    segments = parts.path.split("/")[1:]
    if not segments or any(seg in {"", ".", ".."} for seg in segments):
        raise Unmappable("SPIFFE workload path contains an empty or dot segment")
    if any(any(ord(ch) < 0x21 or ord(ch) == 0x7F for ch in seg) for seg in segments):
        raise Unmappable("SPIFFE workload path contains whitespace/control characters")
    if any(not _SPIFFE_SEGMENT_RE.fullmatch(seg) for seg in segments):
        raise Unmappable("SPIFFE workload path segment uses characters outside [A-Za-z0-9._-]")

    return "runtime:" + "/".join(segments)


@dataclass
class BypassDetector:
    """Detect plaintext access to meshed destinations with bounded evidence."""

    meshed: Iterable[str] = field(default_factory=set)
    max_flags: int = DEFAULT_MAX_FLAGS
    max_destinations: int = DEFAULT_MAX_DESTINATIONS
    flagged: list[tuple[str, str]] = field(default_factory=list, init=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _positive_int(self.max_flags, "max_flags")
        _positive_int(self.max_destinations, "max_destinations")
        if isinstance(self.meshed, (str, bytes)):
            raise ValueError("meshed must be an iterable of destination strings, not a string")
        destinations: set[str] = set()
        for dst in self.meshed:
            destinations.add(_token(dst, "meshed destination"))
            if len(destinations) > self.max_destinations:
                raise ValueError(f"meshed destination count exceeds limit {self.max_destinations}")
        self.meshed = frozenset(destinations)

    def observe(self, src: str, dst: str, mtls: bool) -> bool:
        src = _token(src, "src")
        dst = _token(dst, "dst")
        if not isinstance(mtls, bool):
            raise ValueError(f"mtls must be bool, got {type(mtls).__name__}")

        bypass = dst in self.meshed and not mtls
        if bypass:
            with self._lock:
                self.flagged.append((src, dst))
                overflow = len(self.flagged) - self.max_flags
                if overflow > 0:
                    del self.flagged[:overflow]
        return bypass

    def snapshot(self) -> tuple[tuple[str, str], ...]:
        """Return an immutable, race-safe copy of currently retained evidence."""
        with self._lock:
            return tuple(self.flagged)


@dataclass
class RoutePolicyRegistry:
    """Thread-safe copy-on-write registry for route-by-route mesh migration."""

    max_routes: int = DEFAULT_MAX_ROUTES
    _policies: dict[str, dict] = field(default_factory=dict, init=False, repr=False)
    _revision: int = field(default=0, init=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _positive_int(self.max_routes, "max_routes")

    @property
    def revision(self) -> int:
        with self._lock:
            return self._revision

    def migrate_route(
        self,
        route: str,
        app_attempts: int,
        mesh_attempts: int,
        budget: int = 3,
    ) -> dict:
        decision = reconcile(route, app_attempts, mesh_attempts, budget)
        with self._lock:
            if decision["route"] not in self._policies and len(self._policies) >= self.max_routes:
                raise OverflowError(f"route policy capacity {self.max_routes} reached")
            updated = dict(self._policies)
            updated[decision["route"]] = dict(decision)
            self._policies = updated
            self._revision += 1
            result = dict(decision)
            result["revision"] = self._revision
            return result

    def get(self, route: str) -> dict | None:
        route = _token(route, "route")
        with self._lock:
            value = self._policies.get(route)
            return None if value is None else dict(value)

    def snapshot(self) -> tuple[int, dict[str, dict]]:
        with self._lock:
            return self._revision, {route: dict(policy) for route, policy in self._policies.items()}
