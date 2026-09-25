"""INV-28 - Unikernel implementations: pk_core conformance component + deprecated v1 API.

Two things live here:

1. ``UnikernelImplementationsComponent`` - the pk_core component.  pk_core's default band handlers
   derive findings from contract declarations; every finding listed in :data:`EXERCISED` is instead
   produced by *running* the v4.3.0 engine (fixtures.world) and asserting behaviour through
   :func:`_verify`, which still fails under ``python -O``.  ``tools/pk_gate.py`` reports the exercised
   and declaration-derived counts separately; the MC-level implementation status lives in
   ``evidence/MC_STATUS.json``, never in the pk_core verdict.

2. ``Toolchain`` / ``ToolchainRegister`` / ``NoSuitableToolchain`` - the v4.2.0 (PK_TOOLCHAIN/1)
   API, kept so existing callers keep working.  It is **deprecated** (docs/MIGRATION.md) and now
   applies the production maturity policy of MC-094: production admits only ``mature``.
"""
from __future__ import annotations

import datetime as dt
import json
import tempfile
import threading
import warnings
from dataclasses import dataclass, field
from pathlib import Path

from . import ensure_pk_core

ensure_pk_core()

from pk_core.checklist import ChecklistItem, Finding  # noqa: E402
from pk_core.component import Component  # noqa: E402

from .contract import ELEMENT_ID, ELEMENT_NAME, build  # noqa: E402
from .errors import BindingError, Inv28Error, Reason, RefusalError, RegistryError, ValidationError  # noqa: E402
from .policy import default_policy  # noqa: E402

PKG = Path(__file__).resolve().parent


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O`` (bare asserts are stripped)."""
    if not condition:
        raise AssertionError(message)


def _refusal_code(fn):
    try:
        fn()
    except RefusalError as exc:
        return exc.refusal.code, exc.refusal
    except Inv28Error as exc:
        return exc.code.value, None
    raise AssertionError("expected a refusal; the call succeeded")


# =====================================================================================================
# Deprecated v1 API (PK_TOOLCHAIN/1)
# =====================================================================================================
MATURITY = ("experimental", "beta", "mature")

#: How long a toolchain's security review stands, in logical ticks (v1 only; v2 uses UTC + per-entry interval).
REVIEW_INTERVAL = 200


class NoSuitableToolchain(RuntimeError):
    """Raised when no registered toolchain meets the workload's requirements (v1 API)."""


@dataclass(frozen=True)
class Toolchain:
    """Deprecated v1 register entry.  Use :class:`model.ToolchainRecord` (PK_TOOLCHAIN/2)."""

    name: str
    languages: frozenset[str]
    architectures: frozenset[str]
    maturity: str
    security_contact: bool
    reviewed_at: int = 0
    limitations: tuple[str, ...] = ()

    def __post_init__(self):
        name = self.name.strip() if isinstance(self.name, str) else ""
        if not name:
            raise ValueError("toolchain name must be a non-empty string")
        maturity = self.maturity.strip().lower() if isinstance(self.maturity, str) else ""
        if maturity not in MATURITY:
            raise ValueError(f"unknown maturity: {self.maturity!r}")
        if type(self.security_contact) is not bool:
            raise TypeError("security_contact must be bool")
        if type(self.reviewed_at) is not int or self.reviewed_at < 0:
            raise ValueError("reviewed_at must be a non-negative integer")
        for attr in ("languages", "architectures"):
            value = getattr(self, attr)
            if not isinstance(value, (set, frozenset)):
                raise TypeError(f"{name}: {attr} must be a set, got {type(value).__name__}")
            normalised = frozenset(_normalise_token(v, attr) for v in value)
            if not normalised:
                raise ValueError(f"{name}: {attr} must not be empty")
            object.__setattr__(self, attr, normalised)
        if not isinstance(self.limitations, (tuple, list)) or any(not isinstance(v, str) or not v.strip() for v in self.limitations):
            raise TypeError("limitations must contain non-empty strings")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "maturity", maturity)
        object.__setattr__(self, "limitations", tuple(v.strip() for v in self.limitations))

    def review_stale(self, now: int) -> bool:
        _validate_now(now)
        return now - self.reviewed_at > REVIEW_INTERVAL


def _normalise_token(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} entries must be non-empty strings")
    return value.strip().lower()


def _validate_now(now: int) -> None:
    if type(now) is not int or now < 0:
        raise ValueError("now must be a non-negative integer")


@dataclass
class ToolchainRegister:
    """Deprecated v1 registry.  Use :class:`registry.Registry` + :class:`selection.Selector`."""

    _toolchains: dict[str, Toolchain] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        warnings.warn("ToolchainRegister (PK_TOOLCHAIN/1) is deprecated; use registry.Registry and "
                      "selection.Selector (PK_TOOLCHAIN/2)", DeprecationWarning, stacklevel=3)

    @property
    def toolchains(self) -> tuple[Toolchain, ...]:
        return tuple(self._toolchains.values())

    def register(self, toolchain: Toolchain) -> Toolchain:
        if not isinstance(toolchain, Toolchain):
            raise TypeError("toolchain must be a Toolchain")
        key = toolchain.name.casefold()
        if key in self._toolchains:
            raise ValueError(f"toolchain {toolchain.name!r} is already registered")
        self._toolchains[key] = toolchain
        return toolchain

    def stale(self, now: int) -> list[str]:
        _validate_now(now)
        return sorted(t.name for t in self.toolchains if t.review_stale(now))

    def select(self, *, language: str, architecture: str, environment: str, now: int = 0) -> dict:
        """v1 selection.  Production applies the MC-094 policy: only ``mature`` is admitted."""
        language = _normalise_token(language, "language")
        architecture = _normalise_token(architecture, "architecture")
        environment = _normalise_token(environment, "environment")
        _validate_now(now)
        min_prod = default_policy().rule("production").min_maturity
        eliminated: list[str] = []
        candidates: list[Toolchain] = []
        for t in self.toolchains:
            if language not in t.languages:
                eliminated.append(f"{t.name}: no {language} support")
                continue
            if architecture not in t.architectures:
                eliminated.append(f"{t.name}: no {architecture} support")
                continue
            if environment == "production" and MATURITY.index(t.maturity) < MATURITY.index(min_prod):
                eliminated.append(f"{t.name}: {t.maturity}, below production policy ({min_prod})")
                continue
            if environment == "production" and not t.security_contact:
                eliminated.append(f"{t.name}: no security contact")
                continue
            if environment == "production" and t.review_stale(now):
                eliminated.append(f"{t.name}: security review is stale")
                continue
            candidates.append(t)
        if not candidates:
            raise NoSuitableToolchain(
                f"no toolchain for language={language} arch={architecture} env={environment} "
                f"({'; '.join(eliminated)})")
        best = sorted(candidates, key=lambda t: (-MATURITY.index(t.maturity), t.name.casefold()))[0]
        return {"schema": "PK_TOOLCHAIN_SELECTION/1", "toolchain": best.name,
                "maturity": best.maturity, "language": language,
                "architecture": architecture, "environment": environment,
                "reason": f"most mature match ({best.maturity})",
                "eliminated": eliminated}


# =====================================================================================================
# Exercised checks (run the v4.3.0 engine; every one fails loudly under python and python -O)
# =====================================================================================================
def _F():
    from . import fixtures
    return fixtures


def chk_source_of_truth():
    F = _F()
    w = F.world()
    snap = w["registry"].snapshot()
    from .registry import verify_snapshot
    verify_snapshot(w["ring"], snap)
    tampered = json.loads(json.dumps(snap))
    tampered["entries"][0]["maturity"] = "mature" if tampered["entries"][0]["maturity"] != "mature" else "beta"
    try:
        verify_snapshot(w["ring"], tampered)
    except RegistryError as exc:
        _verify(exc.code is Reason.REGISTRY_INTEGRITY)
    else:
        raise AssertionError("tampered snapshot verified")
    return (f"The source of truth is the signed register snapshot (r{snap['revision']}, "
            f"{len(snap['entries'])} entries); a one-field edit to it is refused as REG_INTEGRITY_FAILURE.",
            "registry.py::verify_snapshot")


def chk_refuse_no_fit():
    F = _F()
    w = F.world()
    code, ref = _refusal_code(lambda: w["selector"].select(F.request(language="haskell"), now=F.NOW))
    _verify(code == Reason.NO_SUITABLE_TOOLCHAIN.value and ref is not None)
    _verify(set(ref.unmet) >= {Reason.LANGUAGE_UNSUPPORTED.value})
    return ("A workload no registered toolchain can serve gets a structured PK_TOOLCHAIN_REFUSAL/1 listing every "
            f"unmet constraint ({', '.join(sorted(ref.unmet))}), not a downgrade.", "selection.py::Refusal")


def chk_failure_modes():
    F = _F()
    stale = F.record("old", review=True, reviewed_at="2025-01-01T00:00:00Z", interval_days=30)
    w = F.world(records=[stale, F.record("exp", maturity="experimental")])
    _, r1 = _refusal_code(lambda: w["selector"].select(F.request(), now=F.NOW))
    _, r2 = _refusal_code(lambda: w["selector"].select(F.request(architecture="riscv64"), now=F.NOW))
    _verify(Reason.REVIEW_STALE.value in r1.unmet and Reason.MATURITY_BELOW_POLICY.value in r1.unmet)
    _verify(Reason.ARCH_UNSUPPORTED.value in r2.unmet)
    return ("All four contract failure modes (no fit, only-experimental in production, stale review, architecture "
            "unsupported) surface as distinct stable reason codes.", "errors.py::Reason")


def chk_interface_schema():
    from .schema_check import validate_file
    F = _F()
    w = F.world()
    res = w["selector"].select(F.request(), now=F.NOW).to_dict()
    _verify(not validate_file("PK_TOOLCHAIN_SELECTION-2", res), "selection result violates its schema")
    _verify(not validate_file("PK_TOOLCHAIN-2", w["registry"].entries[0].to_dict()))
    _verify(not validate_file("PK_TOOLCHAIN_SELECTION_REQUEST-1", F.request().to_dict()))
    return ("register/select/request payloads validate against the shipped JSON Schemas (schemas/*.schema.json).",
            "schema_check.py::validate_file")


def chk_versioning():
    from .model import ToolchainRecord
    try:
        ToolchainRecord.from_dict({"schema": "PK_TOOLCHAIN/1", "name": "x"})
    except ValidationError as exc:
        _verify(exc.code is Reason.INVALID_REQUEST)
    else:
        raise AssertionError("v1 schema accepted by the v2 loader")
    return ("Schema versions are explicit: a PK_TOOLCHAIN/1 document is refused by the /2 loader rather than "
            "reinterpreted (migration path in docs/MIGRATION.md).", "model.py::ToolchainRecord.from_dict")


def chk_policy_config():
    from .policy import SelectionPolicy
    shipped = SelectionPolicy.load(PKG / "config" / "policy.default.json")
    _verify(shipped.digest == default_policy().digest, "config/policy.default.json drifted from default_policy()")
    bad = json.loads((PKG / "config" / "policy.default.json").read_text())
    bad["environments"]["production"]["require_certification"] = False
    try:
        SelectionPolicy.from_dict(bad)
    except ValidationError as exc:
        _verify(exc.code is Reason.POLICY_INVALID)
    else:
        raise AssertionError("weakened production policy loaded")
    return ("Policy is a validated, versioned document; a production rule that disables certification is refused "
            "at load (SEL_POLICY_INVALID).", "policy.py::EnvironmentRule")


def chk_determinism():
    F = _F()
    a = F.world(records=F.standard_records()[::-1])["selector"].select(F.request(), now=F.NOW)
    b = F.world()["selector"].select(F.request(), now=F.NOW)
    _verify(a.ref == b.ref and a.request_digest == b.request_digest)
    return (f"Registration order does not change the choice ({a.ref}); identical inputs give identical decisions.",
            "selection.py::Selector.select")


def chk_production_maturity():
    F = _F()
    w = F.world()
    chosen = w["selector"].select(F.request(language="c"), now=F.NOW)
    _verify(chosen.toolchain == "rumprun" and chosen.maturity == "mature", chosen)
    _, ref = _refusal_code(lambda: w["selector"].select(F.request(language="rust"), now=F.NOW))
    uk = [e["codes"] for e in ref.eliminated if e["toolchain"] == "unikraft@1.0.0-fixture"]
    _verify(uk == [[Reason.MATURITY_BELOW_POLICY.value]], uk)
    return ("Selection is by requirement and policy: C in production chose the mature rumprun; a Rust workload "
            "whose only match is beta unikraft is refused TC_MATURITY_BELOW_POLICY (MC-094).",
            "selection.py::Selector._codes")


def chk_stdlib_only():
    import ast
    import sys
    std = set(sys.stdlib_module_names)
    bad = []
    for p in PKG.glob("*.py"):
        for node in ast.walk(ast.parse(p.read_text())):
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                mods = [node.module or ""]
            else:
                continue
            bad += [f"{p.name}:{m}" for m in mods if m.split(".")[0] not in std and m.split(".")[0] != "pk_core"]
    _verify(not bad, bad)
    return ("Runtime imports only the standard library (and the vendored pk_core for this component).",
            "tools/deps_check.py")


def chk_authn():
    from .certification import issue
    F = _F()
    w = F.world()
    doc = issue(w["ring"], toolchain="rumprun", version="1.0.0-fixture", artifact_sha256="0" * 64,
                architecture="x86_64", issued_at="2026-09-01T00:00:00Z", expires_at="2026-12-01T00:00:00Z")
    doc["architecture"] = "aarch64"
    try:
        w["certs"].ingest(doc)
    except ValidationError as exc:
        _verify(exc.code is Reason.CERTIFICATION_INVALID)
    else:
        raise AssertionError("tampered certificate accepted")
    return ("GAP-15 certificates are authenticated before trust: an edited certificate is refused "
            "(TC_CERTIFICATION_INVALID).", "certification.py::CertificationStore.ingest")


def chk_substitution():
    F = _F()
    w = F.world()
    res = w["selector"].select(F.request(), now=F.NOW)
    w["inv27"].verify(res.ticket, F.artifact_bytes(res.ref), now=F.NOW)
    try:
        w["inv27"].verify(res.ticket, b"substituted", now=F.NOW)
    except BindingError as exc:
        _verify(exc.code is Reason.BINDING_MISMATCH)
    else:
        raise AssertionError("substituted artifact accepted")
    return ("Selection-to-build substitution is closed: INV-27 accepts the bound artifact and refuses any other "
            "bytes (BIND_ARTIFACT_MISMATCH).", "binding.py::Inv27Adapter.verify")


def chk_log_privacy():
    F = _F()
    w = F.world()
    w["selector"].select(F.request(tenant="acme-secret-tenant"), now=F.NOW)
    joined = "\n".join(w["logger"].lines)
    _verify("acme-secret-tenant" not in joined and "p:" in joined)
    return ("Tenant and workload ids reach logs only as keyed pseudonyms.", "observability.py::StructuredLogger")


def chk_hostile_input():
    from .selection import SelectionRequest
    for bad in ({"workload_id": "w", "tenant": "t", "environment": "production", "language": "c" * 500,
                 "architecture": "x86_64"},
                {"workload_id": "w", "tenant": "t", "environment": "production", "language": "c",
                 "architecture": "x86_64", "toolchain": "nanos"}):
        try:
            SelectionRequest.from_dict(bad)
        except ValidationError:
            continue
        raise AssertionError(f"hostile request accepted: {bad}")
    return ("Oversized tokens and a request that tries to name its toolchain are refused at the boundary.",
            "selection.py::SelectionRequest.from_dict")


def chk_experimental_refused():
    F = _F()
    w = F.world(records=[F.record("nanos", maturity="experimental", contact="")])
    _, ref = _refusal_code(lambda: w["selector"].select(F.request(), now=F.NOW))
    _verify(Reason.MATURITY_BELOW_POLICY.value in ref.unmet and Reason.NO_SECURITY_CONTACT.value in ref.unmet)
    return ("An experimental toolchain with no security contact cannot be selected in production; the answer is a "
            "refusal naming both gates.", "selection.py::Selector._codes")


def chk_env_boundary():
    F = _F()
    w = F.world(records=[F.record("nanos", maturity="experimental", contact="", catalog_status="example")])
    dev = w["selector"].select(F.request(environment="dev"), now=F.NOW)
    _verify(dev.toolchain == "nanos")
    return ("The same toolchain stays selectable in dev, so maturity gating is an environment boundary recorded in "
            "policy, not a blanket ban.", "policy.py::default_policy")


def chk_dependency_loss():
    from .certification import CertificationStore
    from .selection import Selector
    F = _F()
    w = F.world()

    def down():
        raise ConnectionError("gap15 down")
    sel = Selector(w["registry"], default_policy(), certifications=CertificationStore(w["ring"], source=down),
                   advisories=w["advisories"])
    code, _ = _refusal_code(lambda: sel.select(F.request(), now=F.NOW))
    _verify(code == Reason.DEPENDENCY_UNAVAILABLE.value)
    return ("Losing GAP-15 makes production selection refuse (SEL_DEPENDENCY_UNAVAILABLE) instead of proceeding "
            "uncertified.", "certification.py::CertificationStore.refresh")


def chk_reconstruct():
    from .registry import FileStore, Registry
    F = _F()
    w = F.world()
    with tempfile.TemporaryDirectory() as d:
        fs = FileStore(d)
        fs.save(w["registry"].snapshot())
        good_rev = w["registry"].revision
        w["registry"].emergency_disable("rumprun@1.0.0-fixture", actor="operator", reason="drill")
        p = fs.save(w["registry"].snapshot())
        p.write_text(p.read_text().replace('"disabled"', '"active"'))
        snap, problems = fs.reconstruct(w["ring"])
        if snap is None:
            raise AssertionError("reconstruct found no valid snapshot")
        _verify(snap["revision"] == good_rev and problems)
        fresh = Registry(w["ring"])
        fresh.load(snap)
        _verify(fresh.revision == good_rev and len(fresh.entries) == 4
                and all(e.lifecycle == "active" for e in fresh.entries))
    return ("State is reconstructed from the newest snapshot that verifies; a tampered newer file is reported and "
            "skipped.", "registry.py::FileStore.reconstruct")


def chk_capacity():
    from .registry import Authorizer, Registry
    F = _F()
    ring = __import__("inv28_unikernel_implementations.trust", fromlist=["KeyRing"]).KeyRing.ephemeral()
    reg = Registry(ring, Authorizer.permissive("op"), capacity=2)
    for i in range(2):
        reg.register(F.record(f"t{i}"), actor="op", expected_revision=reg.revision)
    try:
        reg.register(F.record("t9"), actor="op", expected_revision=reg.revision)
    except RegistryError as exc:
        _verify(exc.code is Reason.REGISTRY_FULL)
    else:
        raise AssertionError("capacity bound not enforced")
    return ("Registry size is bounded; beyond capacity a register call is refused (REG_CAPACITY_EXCEEDED), "
            "not queued.", "registry.py::Registry.register")


def chk_concurrency():
    F = _F()
    w = F.world()
    reg = w["registry"]
    rev = reg.revision
    ok, conflicts = [], []

    def worker(i):
        try:
            reg.register(F.record(f"c{i}"), actor="operator", expected_revision=rev)
            ok.append(i)
        except RegistryError as exc:
            conflicts.append(exc.code)
    ts = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    _verify(len(ok) == 1 and len(conflicts) == 7 and set(conflicts) == {Reason.REGISTRY_CONFLICT})
    return ("Concurrent writers against the same revision: exactly one wins, the rest get REG_REVISION_CONFLICT.",
            "registry.py::Registry._cas")


def chk_bounded_output():
    from .selection import MAX_ELIMINATIONS
    F = _F()
    recs = [F.record(f"n{i:04d}", languages=("ocaml",)) for i in range(MAX_ELIMINATIONS + 20)]
    w = F.world(records=recs, with_certs=False)
    _, ref = _refusal_code(lambda: w["selector"].select(F.request(), now=F.NOW))
    _verify(len(ref.eliminated) == MAX_ELIMINATIONS and ref.eliminated_truncated == 20)
    return (f"Elimination output is bounded at {MAX_ELIMINATIONS} with an explicit truncation count.",
            "selection.py::MAX_ELIMINATIONS")


def chk_audit_chain():
    F = _F()
    w = F.world()
    w["selector"].select(F.request(), now=F.NOW)
    _verify(not w["audit"].verify())
    w["audit"]._entries[-1]["payload"]["toolchain"] = "nanos@1.0.0-fixture"
    _verify(w["audit"].verify(), "tamper not detected")
    return ("Every decision is written to a hash-chained audit ledger; editing a recorded decision breaks "
            "verification.", "observability.py::AuditLedger.verify")


def chk_explain():
    F = _F()
    w = F.world()
    r = w["selector"].select(F.request(), now=F.NOW)
    text = w["service"].explain(r.decision_id)
    _verify("rumprun" in text and "TC_MATURITY_BELOW_POLICY" in text)
    return ("Operators get an explain view rendered from the recorded decision (inputs, policy digest, "
            "certificate, eliminated candidates with codes).", "explain.py::render")


def chk_readiness():
    F = _F()
    w = F.world(with_feed=False)
    rd = w["service"].readiness()
    _verify(not rd["ready"] and any("advisory" in r for r in rd["reasons"]))
    return ("Dependency health is surfaced: readiness reports a missing advisory feed rather than inferring health.",
            "service.py::Inv28Service.readiness")


def chk_emergency_disable():
    F = _F()
    w = F.world()
    w["registry"].emergency_disable("rumprun@1.0.0-fixture", actor="operator", reason="CVE drill")
    _, ref = _refusal_code(lambda: w["selector"].select(F.request(), now=F.NOW))
    _verify(Reason.DISABLED.value in ref.unmet)
    return ("Emergency disable is a first-class registry operation; the disabled toolchain is refused immediately "
            "(TC_DISABLED) and the change is audited.", "registry.py::Registry.emergency_disable")


def chk_review_freshness():
    F = _F()
    w = F.world()
    later = F.NOW + dt.timedelta(days=200)
    _verify(w["service"].stale_reviews(later) == sorted(r.ref for r in w["registry"].entries))
    return ("Review freshness uses real UTC timestamps with per-toolchain intervals; overdue reviews are listed "
            "and make the toolchain unselectable in production.", "model.py::ReviewRecord.stale")


EXERCISED = {
    "assess_architecture": {3: chk_source_of_truth},
    "assess_requirements": {0: chk_refuse_no_fit, 3: chk_failure_modes, 8: chk_interface_schema},
    "assess_interfaces": {1: chk_interface_schema, 5: chk_versioning, 6: chk_refuse_no_fit},
    "assess_implementation": {1: chk_policy_config, 2: chk_policy_config, 5: chk_production_maturity,
                              8: chk_stdlib_only, 9: chk_determinism},
    "assess_security": {3: chk_authn, 4: chk_substitution, 5: chk_log_privacy, 6: chk_hostile_input,
                        8: chk_experimental_refused, 9: chk_env_boundary},
    "assess_resilience": {2: chk_dependency_loss, 3: chk_reconstruct, 5: chk_capacity, 6: chk_concurrency},
    "assess_performance": {2: chk_bounded_output, 3: chk_capacity},
    "assess_observability": {4: chk_audit_chain, 5: chk_log_privacy, 7: chk_explain, 8: chk_readiness},
    "assess_testing": {7: chk_audit_chain},
    "assess_operations": {1: chk_emergency_disable, 3: chk_review_freshness, 4: chk_reconstruct},
}
EXERCISED_BANDS = [(band, idx) for band, m in EXERCISED.items() for idx in m]


class UnikernelImplementationsComponent(Component):
    """Master-applied component for INV-28."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def _exercise(self, band: str, items: list[ChecklistItem], findings: list[Finding]) -> list[Finding]:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            for idx, fn in EXERCISED.get(band, {}).items():
                statement, evidence = fn()
                findings[idx] = self.satisfied(items[idx], statement, *self._evidence(evidence))
        return findings


for _band in EXERCISED:
    def _make(band):
        def method(self, items):
            return self._exercise(band, items, getattr(Component, band)(self, items))
        method.__name__ = band
        return method
    setattr(UnikernelImplementationsComponent, _band, _make(_band))

COMPONENT = UnikernelImplementationsComponent
