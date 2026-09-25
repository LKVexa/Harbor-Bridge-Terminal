"""Standalone policy evaluation primitives for GAP-13.

This module deliberately has no dependency on ``pk_core`` so callers can use the
policy evaluator without installing the conformance/audit framework.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from numbers import Real
from collections.abc import Mapping, Sequence
from typing import Any, Iterable

#: Cached policy older than this is reported stale to the caller.
BUNDLE_STALENESS_BOUND = 300


from .errors import BundleRejected, RequestRejected, ScopeEscalation  # noqa: E402  (re-exported)


def _freeze(value: Any) -> Any:
    """Hashable index key for a match/request value (lists become tagged tuples)."""
    if isinstance(value, list):
        return ("__list__",) + tuple(_freeze(v) for v in value)
    if isinstance(value, dict):
        return ("__dict__",) + tuple(sorted((k, _freeze(v)) for k, v in value.items()))
    try:
        hash(value)
    except TypeError:
        return ("__unhashable__", repr(value))
    # bool/int collide in dict keys (True == 1); tag the type so the index never over-matches silently
    return (type(value).__name__, value)


class CompiledIndex:
    """G13-MC-029 compiled matcher.

    Each rule is filed under exactly one anchor: its least frequent (most selective) pair.  A
    request only visits the buckets for its own (attribute, value) pairs plus the
    residual list of match-everything rules, so evaluation cost scales with the
    request width and bucket occupancy instead of the total rule count.  The
    final equality check is still performed by :meth:`Rule.matches`, so the index
    can only narrow candidates, never widen a match.
    """

    __slots__ = ("buckets", "residual", "size")

    def __init__(self, rules: tuple["Rule", ...]) -> None:
        # pass 1: how common is each (attribute, value) pair across the bundle?
        freq: dict[tuple[str, Any], int] = {}
        for rule in rules:
            for key, value in rule.match:
                fk = (key, _freeze(value))
                freq[fk] = freq.get(fk, 0) + 1
        # pass 2: file each rule under its *most selective* pair (ties -> attribute name) so
        # buckets stay small even when a low-cardinality attribute such as ``action`` is universal
        buckets: dict[tuple[str, Any], list[Rule]] = {}
        residual: list[Rule] = []
        for rule in rules:
            if not rule.match:
                residual.append(rule)
                continue
            anchor = min(((key, _freeze(value)) for key, value in rule.match),
                         key=lambda fk: (freq[fk], fk[0]))
            buckets.setdefault(anchor, []).append(rule)
        self.buckets = {k: tuple(v) for k, v in buckets.items()}
        self.residual = tuple(residual)
        self.size = len(rules)

    def candidates(self, request: Mapping[str, Any]) -> list["Rule"]:
        out = list(self.residual)
        for key, value in request.items():
            bucket = self.buckets.get((key, _freeze(value)))
            if bucket:
                out.extend(bucket)
        return out


def _validate_timestamp(value: Real, *, name: str) -> Real:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a non-negative real number")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _normalise_match(match: Iterable[tuple[str, Any]], *, rule_name: str) -> tuple[tuple[str, Any], ...]:
    if isinstance(match, (str, bytes, bytearray)):
        raise TypeError(f"{rule_name}: match must be an iterable of (attribute, value) pairs")
    try:
        raw = tuple(match)
    except TypeError as exc:
        raise TypeError(f"{rule_name}: match must be iterable") from exc

    pairs: list[tuple[str, Any]] = []
    seen: set[str] = set()
    for index, pair in enumerate(raw):
        if isinstance(pair, (str, bytes, bytearray)):
            raise TypeError(f"{rule_name}: match entry {index} must be a two-item pair")
        try:
            key, value = pair
        except (TypeError, ValueError) as exc:
            raise TypeError(f"{rule_name}: match entry {index} must be a two-item pair") from exc
        if not isinstance(key, str) or not key:
            raise ValueError(f"{rule_name}: match attribute names must be non-empty strings")
        if key in seen:
            raise ValueError(f"{rule_name}: duplicate attribute in match: {key}")
        seen.add(key)
        pairs.append((key, value))

    # Sort only by attribute name. Values may be heterogeneous/non-orderable.
    return tuple(sorted(pairs, key=lambda item: item[0]))


def _match_contains(container: tuple[tuple[str, Any], ...], subset: tuple[tuple[str, Any], ...]) -> bool:
    """Return whether every key/value pair in ``subset`` exists in ``container``.

    This avoids ``set(...)`` so policy values need not be hashable.
    """
    values = dict(container)
    sentinel = object()
    return all(values.get(key, sentinel) == value for key, value in subset)


def check_scope(candidate: tuple["Rule", ...], environment: str) -> None:
    """Tenant rules must bind a tenant and may only narrow estate denies."""
    estate_denies = tuple(rule for rule in candidate if rule.scope == "estate" and rule.effect == "deny")
    for rule in candidate:
        if rule.scope == "tenant" and not any(key == "tenant" for key, _ in rule.match):
            raise BundleRejected(f"{environment}: tenant-scoped rule {rule.name} must bind a tenant attribute")
        if rule.scope == "tenant" and rule.effect == "allow":
            conflicting = next((d for d in estate_denies if _match_contains(rule.match, d.match)), None)
            if conflicting is not None:
                raise ScopeEscalation(f"{rule.name}: tenant rule would widen estate deny {conflicting.name}")


@dataclass(frozen=True, slots=True)
class Rule:
    """One policy rule; more matched attributes means a more specific rule."""

    name: str
    effect: str                 # "allow" | "deny"
    match: tuple                # ((attribute, value), ...) normalized by attribute
    scope: str = "estate"       # "estate" | "tenant"

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("rule name must be a non-empty string")
        if self.effect not in ("allow", "deny"):
            raise ValueError(f"unknown effect: {self.effect!r}")
        if self.scope not in ("estate", "tenant"):
            raise ValueError(f"unknown scope: {self.scope!r}")
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "match", _normalise_match(self.match, rule_name=self.name))

    @property
    def specificity(self) -> int:
        return len(self.match)

    def matches(self, request: Mapping[str, Any]) -> bool:
        sentinel = object()
        for key, value in self.match:
            got = request.get(key, sentinel)
            if got is sentinel or type(got) is not type(value) or got != value:
                return False
        return True


@dataclass(slots=True)
class PolicyEngine:
    """Deny-by-default, most-specific-wins, explainable policy evaluation."""

    environment: str
    version: str = "none"
    rules: tuple[Rule, ...] = field(default_factory=tuple)
    loaded_at: Real = 0
    staleness_bound: Real = BUNDLE_STALENESS_BOUND
    bundle: Any = None                       # PolicyBundle identity of the active rules
    _index: CompiledIndex = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.environment, str) or not self.environment.strip():
            raise ValueError("environment must be a non-empty string")
        self.environment = self.environment.strip()
        _validate_timestamp(self.loaded_at, name="loaded_at")
        if self.rules:
            raise BundleRejected("rules may only enter through load()/activate() with a verified bundle")
        self._index = CompiledIndex(())

    def load(
        self,
        rules: Sequence[Rule],
        version: str,
        verification: Any,
        now: Real = 0,
    ) -> str:
        """Load a bundle -- **only** with a ``VerificationResult`` minted by ``BundleVerifier``.

        G13-MC-001: a caller-supplied mapping such as ``{"verified": True}`` is no
        longer accepted.  ``rules`` and ``version`` must be exactly those of the
        verified bundle, so a verified result cannot be used to smuggle other rules.
        """
        from .verify import is_trusted  # local import: verify -> bundle -> engine
        _validate_timestamp(now, name="now")
        if not is_trusted(verification):
            raise BundleRejected(
                f"{self.environment}: policy bundle {version!r} is not verified "
                "(a BundleVerifier-minted VerificationResult is required)")
        bundle = verification.bundle
        if isinstance(rules, (str, bytes, bytearray)) or not isinstance(rules, Sequence):
            raise BundleRejected(f"{self.environment}: rules must be a sequence")
        if tuple(rules) != bundle.rules or version != bundle.version:
            raise BundleRejected(f"{self.environment}: rules/version differ from the verified bundle")
        return self.activate(verification, now=now)

    def activate(self, verification: Any, now: Real = 0) -> str:
        """Validate the verified bundle's semantics and swap it in atomically."""
        from .verify import is_trusted
        _validate_timestamp(now, name="now")
        if not is_trusted(verification):
            raise BundleRejected(f"{self.environment}: activation requires a verified bundle")
        bundle = verification.bundle
        if bundle.environment != self.environment:
            raise BundleRejected(f"{self.environment}: bundle is for environment {bundle.environment}")
        candidate = tuple(bundle.rules)
        if any(not isinstance(rule, Rule) for rule in candidate):
            raise BundleRejected(f"{self.environment}: bundle contains a non-Rule entry")
        names = [rule.name for rule in candidate]
        if len(set(names)) != len(names):
            raise BundleRejected(f"{self.environment}: bundle {bundle.version} contains duplicate rule names")
        check_scope(candidate, self.environment)
        index = CompiledIndex(candidate)
        # Commit: single tuple assignment of the snapshot (see concurrency note in service.py)
        self._index = index
        self.rules = candidate
        self.version = bundle.version
        self.bundle = bundle
        self.loaded_at = now
        return self.version

    def _ordered_matches(self, request: Mapping[str, Any], index: "CompiledIndex | None" = None) -> list[Rule]:
        if not isinstance(request, Mapping):
            raise TypeError("request must be a mapping")
        idx = index if index is not None else self._index
        matched = [rule for rule in idx.candidates(request) if rule.matches(request)]
        return sorted(matched, key=lambda rule: (-rule.specificity, rule.effect != "deny", rule.name))

    def _stale(self, now: Real | None) -> bool:
        effective_now = self.loaded_at if now is None else _validate_timestamp(now, name="now")
        if effective_now < self.loaded_at:
            raise ValueError("now must not precede the policy bundle load time")
        return effective_now - self.loaded_at > self.staleness_bound

    def evaluate(self, request: Mapping[str, Any], now: Real | None = None) -> dict[str, Any]:
        """Evaluate a request and return a deterministic ``PK_POLICY_VERDICT/1``."""
        stale = self._stale(now)
        ordered = self._ordered_matches(request)
        if not ordered:
            return {
                "schema": "PK_POLICY_VERDICT/1",
                "effect": "deny",
                "rule": None,
                "reason": "no matching rule; policy denies by default",
                "version": self.version,
                "stale": stale,
                "tie_break": False,
                "considered": [],
                "bundle": self._identity(),
            }

        winner = ordered[0]
        tie_break = any(rule.specificity == winner.specificity for rule in ordered[1:])
        return {
            "schema": "PK_POLICY_VERDICT/1",
            "effect": winner.effect,
            "rule": winner.name,
            "reason": f"matched {winner.specificity} attribute(s) via {winner.name}",
            "version": self.version,
            "stale": stale,
            "tie_break": tie_break,
            "considered": [rule.name for rule in ordered],
            "bundle": self._identity(),
        }

    def _identity(self) -> dict[str, Any] | None:
        b = self.bundle
        if b is None:
            return None
        return {"bundle_id": b.bundle_id, "generation": b.generation, "digest": b.digest}

    def explain(self, request: Mapping[str, Any], now: Real | None = None, *,
                max_matches: int = 256) -> dict[str, Any]:
        """Return an operator-readable, machine-stable ``PK_POLICY_EXPLANATION/1``.

        Request *values* are never echoed (G13-MC-025 redaction); only rule
        identities, effects, scopes, specificities and the attribute *names*
        that each rule matched on appear in the output.
        """
        verdict = self.evaluate(request, now=now)
        ordered = self._ordered_matches(request)
        shown = ordered[:max_matches]
        return {
            "schema": "PK_POLICY_EXPLANATION/1",
            "version": self.version,
            "environment": self.environment,
            "bundle": verdict["bundle"],
            "stale": verdict["stale"],
            "effect": verdict["effect"],
            "winner": verdict["rule"],
            "reason": verdict["reason"],
            "tie_break": verdict["tie_break"],
            "precedence": "specificity-desc, deny-before-allow, rule-name-asc",
            "matched": [
                {
                    "rule": rule.name,
                    "effect": rule.effect,
                    "scope": rule.scope,
                    "specificity": rule.specificity,
                    "attributes": [k for k, _ in rule.match],
                }
                for rule in shown
            ],
            "matched_total": len(ordered),
            "truncated": len(ordered) > len(shown),
        }
