"""Version semantics and range policy (component 18).

Each namespace declares its scheme; there is no universal comparator
(MC-18-01). Ranges are canonical interval lists ``[(lo, lo_incl, hi,
hi_incl)]``; ``*``/``x`` wildcards are refused (MC-18-02, MC-18-04 — no
implicit widening). Prereleases only match a range that names a prerelease
bound explicitly. Exclusions (known-bad versions / revocations) override
positive ranges (MC-18-05).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

RULESET_REVISION = "GAP15-VERSION-RULES/1.0.0"

_SEMVER = re.compile(
    r"^(0|[1-9]\d{0,8})\.(0|[1-9]\d{0,8})\.(0|[1-9]\d{0,8})"
    r"(?:-((?:0|[1-9]\d{0,8}|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d{0,8}|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)
_SPEC = re.compile(r"^(?:preview|p)?([1-9]\d{0,3})$")  # e.g. WASI preview1/preview2 -> "preview2"
_DATE = re.compile(r"^(20\d\d)-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")


class VersionError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


@dataclass(frozen=True)
class Version:
    scheme: str
    key: tuple
    text: str
    prerelease: bool = False

    def __lt__(self, other: "Version") -> bool:
        if self.scheme != other.scheme:
            raise VersionError("E_VERSION_SCHEME_MIX", f"{self.scheme} vs {other.scheme}")
        return self.key < other.key

    def __le__(self, other: "Version") -> bool:
        return self == other or self < other

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Version) and self.scheme == other.scheme and self.key == other.key

    def __hash__(self) -> int:
        return hash((self.scheme, self.key))


def _pre_key(pre: Optional[str]) -> tuple:
    if pre is None:
        return (1,)  # release sorts after any prerelease
    parts = []
    for ident in pre.split("."):
        parts.append((0, int(ident), "") if ident.isdigit() else (1, 0, ident))
    return (0, tuple(parts))


def parse_version(scheme: str, text: str) -> Version:
    if not isinstance(text, str) or len(text) > 128:
        raise VersionError("E_VERSION_MALFORMED", "version must be a short string")
    if scheme == "semver":
        m = _SEMVER.match(text)
        if not m:
            raise VersionError("E_VERSION_MALFORMED", f"not SemVer 2.0.0: {text!r}")
        major, minor, patch = (int(m.group(i)) for i in (1, 2, 3))
        # build metadata is not significant for precedence (SemVer §10)
        return Version("semver", (major, minor, patch, _pre_key(m.group(4))), text, m.group(4) is not None)
    if scheme == "spec":
        m = _SPEC.match(text)
        if not m:
            raise VersionError("E_VERSION_MALFORMED", f"not a spec revision: {text!r}")
        return Version("spec", (int(m.group(1)),), text)
    if scheme == "date":
        m = _DATE.match(text)
        if not m:
            raise VersionError("E_VERSION_MALFORMED", f"not YYYY-MM-DD: {text!r}")
        return Version("date", tuple(int(g) for g in m.groups()), text)
    if scheme == "build":
        if not re.fullmatch(r"[0-9a-f]{7,64}", text):
            raise VersionError("E_VERSION_MALFORMED", "vendor build ids are lowercase hex")
        return Version("build", (text,), text)  # equality-only
    raise VersionError("E_VERSION_SCHEME_UNKNOWN", scheme)


@dataclass(frozen=True)
class Interval:
    lo: Optional[Version]
    lo_incl: bool
    hi: Optional[Version]
    hi_incl: bool

    def contains(self, v: Version) -> bool:
        if v.scheme == "build":
            return self.lo == v and self.hi == v
        if self.lo is not None and (v < self.lo or (v == self.lo and not self.lo_incl)):
            return False
        if self.hi is not None and (self.hi < v or (v == self.hi and not self.hi_incl)):
            return False
        return True

    def canonical(self) -> str:
        lo = ("[" if self.lo_incl else "(") + (self.lo.text if self.lo else "")
        hi = (self.hi.text if self.hi else "") + ("]" if self.hi_incl else ")")
        return f"{lo},{hi}"


@dataclass(frozen=True)
class Range:
    scheme: str
    intervals: tuple
    exclusions: tuple = ()
    allow_prerelease: bool = False

    def matches(self, v: Version) -> bool:
        if v.scheme != self.scheme:
            return False
        if v in self.exclusions:
            return False
        if v.prerelease and not self.allow_prerelease:
            return False
        return any(iv.contains(v) for iv in self.intervals)

    def canonical(self) -> str:
        ex = ",".join(sorted(e.text for e in self.exclusions))
        body = "|".join(sorted(iv.canonical() for iv in self.intervals))
        return f"{self.scheme}:{body}" + (f"!{ex}" if ex else "") + ("+pre" if self.allow_prerelease else "")


def parse_range(scheme: str, expr: str, exclusions: tuple = ()) -> Range:
    """Grammar: ``=1.2.3`` | ``>=1.2.0 <2.0.0`` | ``>1.0.0 <=1.4.0``; clauses joined by `` || ``.

    Unbounded upper ends are refused (MC-18-04: no implicit major widening).
    """
    if not isinstance(expr, str) or not expr.strip() or len(expr) > 512:
        raise VersionError("E_RANGE_MALFORMED", "empty or oversized range")
    if any(tok in expr for tok in ("*", "x.", ".x", "^", "~", "latest")):
        raise VersionError("E_RANGE_WILDCARD", "wildcard / caret / tilde ranges widen implicitly")
    intervals = []
    allow_pre = False
    for clause in expr.split("||"):
        parts = clause.split()
        lo = hi = None
        lo_incl = hi_incl = False
        for part in parts:
            m = re.fullmatch(r"(>=|<=|>|<|=)(.+)", part)
            if not m:
                raise VersionError("E_RANGE_MALFORMED", f"bad constraint {part!r}")
            op, ver = m.group(1), parse_version(scheme, m.group(2))
            allow_pre = allow_pre or ver.prerelease
            if op == "=":
                if lo or hi:
                    raise VersionError("E_RANGE_MALFORMED", "= cannot combine with bounds")
                lo = hi = ver
                lo_incl = hi_incl = True
            elif op in (">", ">="):
                if lo is not None:
                    raise VersionError("E_RANGE_MALFORMED", "duplicate lower bound")
                lo, lo_incl = ver, op == ">="
            else:
                if hi is not None:
                    raise VersionError("E_RANGE_MALFORMED", "duplicate upper bound")
                hi, hi_incl = ver, op == "<="
        if hi is None:
            raise VersionError("E_RANGE_UNBOUNDED", "an explicit upper bound is required")
        if lo is not None and (hi < lo or (hi == lo and not (lo_incl and hi_incl))):
            raise VersionError("E_RANGE_UNSATISFIABLE", f"{clause.strip()!r} admits no version")
        intervals.append(Interval(lo, lo_incl, hi, hi_incl))
    return Range(scheme, tuple(intervals), tuple(parse_version(scheme, e) for e in exclusions), allow_pre)


def intersect(a: Range, b: Range) -> Optional[Range]:
    """Deterministic interval intersection; ``None`` means unsatisfiable (MC-18-08)."""
    if a.scheme != b.scheme:
        raise VersionError("E_VERSION_SCHEME_MIX", f"{a.scheme} vs {b.scheme}")
    out = []
    for x in a.intervals:
        for y in b.intervals:
            lo, lo_incl = x.lo, x.lo_incl
            if y.lo is not None and (lo is None or lo < y.lo or (lo == y.lo and not y.lo_incl)):
                lo, lo_incl = y.lo, y.lo_incl if (lo is None or lo != y.lo) else (lo_incl and y.lo_incl)
            hi, hi_incl = x.hi, x.hi_incl
            if y.hi is not None and (hi is None or y.hi < hi or (hi == y.hi and not y.hi_incl)):
                hi, hi_incl = y.hi, y.hi_incl if (hi is None or hi != y.hi) else (hi_incl and y.hi_incl)
            if lo is not None and hi is not None and (hi < lo or (hi == lo and not (lo_incl and hi_incl))):
                continue
            out.append(Interval(lo, lo_incl, hi, hi_incl))
    if not out:
        return None
    return Range(a.scheme, tuple(out), tuple(sorted(set(a.exclusions) | set(b.exclusions), key=lambda v: v.key)),
                 a.allow_prerelease and b.allow_prerelease)
