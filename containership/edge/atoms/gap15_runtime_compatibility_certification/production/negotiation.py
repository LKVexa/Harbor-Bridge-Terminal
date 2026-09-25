"""WASI/WIT/component/runtime negotiation engine (component 16).

Input: an artifact ``Requirements`` manifest and a ``RuntimeProfile``.
Output: a deterministic ``NegotiationResult`` with a full transcript of every
constraint, the capability it was compared against, the rule applied and the
outcome. Negotiation decides *capability fit* only — it never produces a
certification; a fit is still ``untested`` until exact evidence exists
(MC-16-04: a shim that "might" help is never inferred).

Precedence (MC-16-07): revocation > lifecycle > policy prohibition >
spec-version compatibility > vendor extension.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .canonical import digest
from .capability import PROVENANCE_RANK, UNKNOWN, RuntimeProfile, normalize
from .versions import VersionError, parse_range, parse_version

ENGINE_VERSION = "GAP15-NEGOTIATION/1.0.0"
MAX_CONSTRAINTS = 256
MAX_INTERFACES = 512
EXPERIMENTAL = {"preview3"}


class NegotiationError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


@dataclass(frozen=True)
class Constraint:
    field: str
    kind: str  # mandatory | optional | forbidden
    values: tuple = ()  # allowed values (mandatory/optional) or banned values (forbidden)
    version_range: Optional[str] = None  # for runtime.version (semver)
    min_provenance: str = "discovered"


@dataclass(frozen=True)
class Adapter:
    """An explicitly modelled shim: provides ``provides`` when ``requires`` is present."""

    name: str
    version: str
    requires: tuple  # (field, value)
    provides: tuple  # (field, value)
    trusted: bool = False


@dataclass
class Requirements:
    constraints: list = field(default_factory=list)
    wit_imports: list = field(default_factory=list)  # e.g. "wasi:http/outgoing-handler@0.2.0"
    mutually_exclusive: list = field(default_factory=list)  # list of (field, value) pairs sets
    allow_experimental: bool = False


@dataclass
class NegotiationResult:
    fits: bool
    engine_version: str
    input_digest: str
    transcript: list
    accepted: list
    rejected: list
    adapters_used: list

    def as_dict(self) -> dict:
        return dict(fits=self.fits, engine_version=self.engine_version, input_digest=self.input_digest,
                    transcript=self.transcript, accepted=self.accepted, rejected=self.rejected,
                    adapters_used=self.adapters_used)


def _req_digest(req: Requirements, profile: RuntimeProfile, policy_revision: str) -> str:
    return digest({
        "c": [[c.field, c.kind, sorted(c.values), c.version_range or "", c.min_provenance] for c in req.constraints],
        "wit": sorted(req.wit_imports),
        "mx": sorted(sorted(list(map(list, s))) for s in req.mutually_exclusive),
        "exp": req.allow_experimental,
        "p": sorted([c.name, c.value, c.layer, c.provenance] for c in profile.capabilities),
        "policy": policy_revision,
    })


def negotiate(req: Requirements, profile: RuntimeProfile, *, adapters: tuple = (),
              policy_prohibited: frozenset = frozenset(), revoked_runtimes: frozenset = frozenset(),
              eol_runtimes: frozenset = frozenset(), policy_revision: str = "policy:0") -> NegotiationResult:
    if len(req.constraints) > MAX_CONSTRAINTS or len(req.wit_imports) > MAX_INTERFACES:
        raise NegotiationError("E_NEG_CARDINALITY", "requirement manifest exceeds bounded cardinality")
    transcript: list = []
    accepted: list = []
    rejected: list = []
    used: list = []

    def note(step: str, subject: str, candidate: str, rule: str, outcome: str) -> None:
        transcript.append({"step": step, "subject": subject, "candidate": candidate, "rule": rule, "outcome": outcome})

    runtime_id = f"{profile.get('runtime.name')}@{profile.get('runtime.version')}"
    # 1. precedence: revocation, lifecycle, policy
    for label, bag, code in (("revocation", revoked_runtimes, "REVOKED"), ("lifecycle", eol_runtimes, "EOL"),
                             ("policy", policy_prohibited, "PROHIBITED")):
        hit = runtime_id in bag
        note("precedence", label, runtime_id, f"{label} overrides spec compatibility", code if hit else "clear")
        if hit:
            rejected.append({"subject": label, "reason": code})
            return NegotiationResult(False, ENGINE_VERSION, _req_digest(req, profile, policy_revision),
                                     transcript, accepted, rejected, used)

    effective = {c.name: c for c in profile.capabilities}
    # 2. explicit adapters: only trusted ones, and only if their precondition holds
    for ad in sorted(adapters, key=lambda a: (a.name, a.version)):
        f, v = ad.requires
        if not ad.trusted:
            note("adapter", ad.name, ad.version, "untrusted adapters are never applied", "skipped")
            continue
        if profile.get(f) == v:
            pf, pv = ad.provides
            used.append({"name": ad.name, "version": ad.version, "provides": [pf, pv]})
            note("adapter", ad.name, ad.version, f"requires {f}={v}", f"provides {pf}={pv}")

    adapter_provides = {(u["provides"][0], u["provides"][1]) for u in used}

    # 3. constraints
    for c in sorted(req.constraints, key=lambda c: (c.field, c.kind, c.values)):
        cap = effective.get(c.field)
        have = cap.value if cap else UNKNOWN
        strong = cap is not None and PROVENANCE_RANK[cap.provenance] >= PROVENANCE_RANK[c.min_provenance]
        if c.field == "runtime.version" and c.version_range:
            try:
                ok = have != UNKNOWN and strong and parse_range("semver", c.version_range).matches(parse_version("semver", have))
            except VersionError as exc:
                ok = False
                note("constraint", c.field, have, "version parse", exc.code)
        else:
            vals = tuple(normalize(c.field, v) if not c.field.startswith("x-") else v for v in c.values)
            if c.kind == "forbidden":
                ok = have not in vals
                if have == UNKNOWN:
                    ok = False  # unknown cannot prove absence of a forbidden feature
            else:
                ok = (strong and have in vals) or any((c.field, v) in adapter_provides for v in vals)
            if ok and have in EXPERIMENTAL and not req.allow_experimental:
                ok = False
                note("constraint", c.field, have, "experimental requires explicit opt-in", "rejected")
        rule = f"{c.kind} {c.field} in {list(c.values) or c.version_range} (>= {c.min_provenance})"
        note("constraint", c.field, have, rule, "accepted" if ok else "rejected")
        (accepted if ok or c.kind == "optional" else rejected).append(
            {"field": c.field, "kind": c.kind, "have": have, "ok": ok})

    # 4. mutually exclusive sets
    for group in req.mutually_exclusive:
        present = [pair for pair in group if profile.get(pair[0]) == pair[1]]
        if len(present) > 1:
            rejected.append({"subject": "mutually_exclusive", "reason": present})
            note("exclusive", str(group), str(present), "at most one may be present", "rejected")

    # 5. WIT imports need an exact interface@version export
    exported = profile.values("wit.interface")
    for imp in sorted(req.wit_imports):
        ok = imp in exported
        note("wit", imp, "exported" if ok else "absent", "exact interface@version match", "accepted" if ok else "rejected")
        (accepted if ok else rejected).append({"field": "wit.interface", "value": imp, "ok": ok})

    fits = not [r for r in rejected if r.get("kind") != "optional"]
    return NegotiationResult(fits, ENGINE_VERSION, _req_digest(req, profile, policy_revision),
                             transcript, accepted, rejected, used)
